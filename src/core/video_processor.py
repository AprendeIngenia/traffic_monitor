import cv2
import time
import numpy as np
import logging as log

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .counting_processor import CountingProcessor
from .homography_manager import HomographyManager
from .speed_calculator import SpeedCalculator
from .mask_processor import MaskProcessing

from .detector_factory import get_detector

log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class VideoProcessor(QThread):
    frameReady = Signal(QImage)
    analysisResult = Signal(dict)
    finished = Signal()
    fpsUpdated = Signal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_source = None
        self.is_running = False
        self.lane_config = None
        self.homography_config = None
        
        # lane colors
        self.lane_colors = [
            (82, 82, 255),    # Rojo
            (219, 152, 52),   # Azul  
            (113, 204, 46),   # Verde
            (15, 196, 241),   # Amarillo
            (182, 89, 155),   # Morado
        ]
        
        # vehicles colors
        self.vehicle_colors = {
            1: (0, 255, 255),    # Bicicleta - Amarillo
            2: (0, 255, 0),      # Carro - Verde
            3: (255, 0, 255),    # Motocicleta - Magenta
            5: (0, 0, 255),      # Bus - Rojo
            7: (255, 165, 0),    # Camión - Naranja
        }
        
    def set_analysis_config(self, lane_polygons: list, homography_config: dict):
        self.lane_config = lane_polygons
        self.homography_config = homography_config
    
    def set_video_source(self, source):
        self.video_source = source
        
    @staticmethod
    def get_first_frame(source):
        """capture first frame"""
        cap = cv2.VideoCapture(source)
        cap.set(3, 1280)
        cap.set(4, 720)
        
        if not cap.isOpened():
            log.error(f"No se pudo abrir la fuente de video: {source}")
            return None, 0, 0
            
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            log.error(f"No se pudo leer el primer fotograma de: {source}")
            return None, 0, 0
        
        # QImage
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        
        return qt_image.copy(), w, h
    
    def draw_filled_polygon(self, frame, polygon, color, alpha=0.35):
        """draw filled polygon"""
        overlay = frame.copy()
        cv2.fillPoly(overlay, [polygon], color)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
    def draw_vehicle_label(self, frame, box, track_id, class_name, speed, cls_id, font_scale, line_thickness):
        """draw vehicle label"""
        # get color
        color = self.vehicle_colors.get(int(cls_id), (0, 255, 0))  # Verde por defecto
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, line_thickness)
        
        # texts
        id_text = f"ID {track_id} {class_name}"
        speed_text = f"{speed} KM/H" if speed != "-" else "- KM/H"
        (id_w, id_h), _ = cv2.getTextSize(id_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thickness)
        (speed_w, speed_h), _ = cv2.getTextSize(speed_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thickness)
        
        # bbox text position
        max_width = max(id_w, speed_w)
        total_height = id_h + speed_h + 10
        start_x = x1 + (x2 - x1 - max_width) // 2
        start_y = y1 - total_height - 10  # 10 pixels arriba de la caja
        
        # adjust
        if start_y < 0:
            start_y = y2 + 10
        if start_x < 0:
            start_x = 5
        if start_x + max_width > frame.shape[1]:
            start_x = frame.shape[1] - max_width - 5
        
        # draw background
        padding = 5
        bg_x1 = start_x - padding
        bg_y1 = start_y - id_h - padding
        bg_x2 = start_x + max_width + padding
        bg_y2 = start_y + speed_h + 10 + padding
        
        # text overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # draw contour
        cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), color, 1)
        
        # draw text
        id_x = start_x + (max_width - id_w) // 2
        cv2.putText(frame, id_text, (id_x, start_y), cv2.FONT_HERSHEY_SIMPLEX, 
                    font_scale, (255, 255, 255), line_thickness)
        
        # vel text
        speed_x = start_x + (max_width - speed_w) // 2
        speed_y = start_y + speed_h + 10
        cv2.putText(frame, speed_text, (speed_x, speed_y), cv2.FONT_HERSHEY_SIMPLEX, 
                    font_scale, (255, 255, 255), line_thickness)
        
    def run(self):
        if not self.video_source and self.video_source != 0:
            log.error(f"No se ha establecido una fuente de video")
            return
        
        if not self.lane_config:
            log.error("No se ha configurado la geometría de carriles")
            return
        
        cap = cv2.VideoCapture(self.video_source)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        
        if not cap.isOpened():
            log.error(f"No se puedo abrir la fuente de video: {self.video_source}")
            return
        
        mask = MaskProcessing()
        detector = get_detector(use_tensorrt=True)
        counter = CountingProcessor(self.lane_config)
        homography_manager = HomographyManager(self.homography_config)
        speed_calculator = SpeedCalculator(homography_manager)
        
        # bicycle: 1, car: 2, motorcycle: 3, bus: 5, truck: 7
        classes_to_detect = [1, 2, 3, 5, 7]  # Car, Motorcycle, Bus, Truck
        
        # draw
        scale_factor = frame_width / 2560.0
        line_thickness = max(1, int(3 * scale_factor))
        font_scale = max(0.4, 0.7 * scale_factor)
        
        self.is_running = True
        prev_time = time.time()
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 0. time delta
            current_time = time.time()
            delta_t = current_time - prev_time
            prev_time = current_time
            
            if delta_t > 0:
                fps = 1.0 / delta_t
                self.fpsUpdated.emit(fps)
            
            # 1. create mask
            masked_frame = mask.process_frame(frame, counter.lane_polygons)
            
            # 2. detect vehicles
            detections_generator, class_names = detector.inference(masked_frame, classes_to_detect)
            
            for results in detections_generator:
                
                # 3. count vehicles
                newly_counted_events = counter.process_frame(results, class_names, speed_calculator.speed_history)

                # 4. calculate speed
                if results.boxes.id is not None:
                    for box, track_id in zip(results.boxes.xyxy.cpu(), results.boxes.id.int().cpu()):
                        speed_check_point = ((box[0] + box[2]) / 2, box[3])
                        speed_calculator.update_speed(int(track_id), speed_check_point, delta_t)

                # 5. save events
                for event in newly_counted_events:
                    speed = speed_calculator.speed_history.get(event['track_id'], -1)
                    event['speed'] = f"{speed:.1f}" if speed >= 0 else "-"
            
                # 6. send results
                current_stats = counter.get_statistics()
                current_stats['newly_counted'] = newly_counted_events
                self.analysisResult.emit(current_stats)
                    
                # 7. draw lanes and count lines
                for i, polygon in enumerate(counter.lane_polygons):
                    lane_color = self.lane_colors[i % len(self.lane_colors)]
                    self.draw_filled_polygon(frame, polygon, lane_color, alpha=0.35)
                    cv2.polylines(frame, [polygon], isClosed=True, color=lane_color, thickness=line_thickness)
                    line = counter.counting_lines[i]
                    cv2.line(frame, (int(line.coords[0][0]), int(line.coords[0][1])), 
                            (int(line.coords[1][0]), int(line.coords[1][1])), (0, 255, 255), line_thickness)
                    
                # 9. draw detections and speed
                if results.boxes.id is not None:
                    for box, track_id, cls_id in zip(results.boxes.xyxy.cpu(), results.boxes.id.int().cpu(), results.boxes.cls.cpu()):
                        speed = speed_calculator.speed_history.get(int(track_id), -1)
                        speed_text = f" {speed:.1f} km/h" if speed >= 0 else ""
                        class_name = class_names.get(int(cls_id), "Unknown")
                        self.draw_vehicle_label(frame, box, int(track_id), class_name, speed_text, int(cls_id), font_scale, line_thickness)
                
                # convert numpy image to QImage
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
                
                # send frame
                self.frameReady.emit(qt_image.copy())
            
        cap.release()
        self.is_running = False
        self.finished.emit()
        log.info("Procesamiento de video finalizado")
        
    def stop(self):
        self.is_running = False