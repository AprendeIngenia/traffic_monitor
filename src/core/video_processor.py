import cv2
import time
import numpy as np
import logging as log

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .vehicle_detector import VehicleDetection
from .counting_processor import CountingProcessor
from .homography_manager import HomographyManager
from .speed_calculator import SpeedCalculator
from .mask_processor import MaskProcessing

log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class VideoProcessor(QThread):
    frameReady = Signal(QImage)
    analysisResult = Signal(dict)
    finished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_source = None
        self.is_running = False
        self.lane_config = None
        self.homography_config = None
        
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
        
        # Convertir el fotograma a QImage y obtener dimensiones
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        
        return qt_image.copy(), w, h
        
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
        detector = VehicleDetection()
        counter = CountingProcessor(self.lane_config)
        homography_manager = HomographyManager(self.homography_config)
        speed_calculator = SpeedCalculator(homography_manager)
        
        # bicycle: 1, car: 2, motorcycle: 3, bus: 5, truck: 7
        classes_to_detect = [1, 2, 3, 5, 7]  # Car, Motorcycle, Bus, Truck
        
        # draw
        scale_factor = frame_width / 2560.0  # Normalizar basado en Full HD
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
            
            # 1. create mask
            masked_frame = mask.process_frame(frame, counter.lane_polygons)
            
            # 2. detect vehicles
            detections_generator, class_names = detector.inference(masked_frame, classes_to_detect)
            
            for results in detections_generator:
                
                # 3. count vehicles
                new_events = counter.process_frame(results, class_names, speed_calculator.speed_history)
                
                # 4. calculate speed
                if results.boxes.id is not None:
                    for box, track_id in zip(results.boxes.xyxy.cpu(), results.boxes.id.int().cpu()):
                        speed_check_point = ((box[0] + box[2]) / 2, box[3])
                        speed_calculator.update_speed(int(track_id), speed_check_point, delta_t)
                        
                # 5. save events
                for event in new_events:
                    speed = speed_calculator.speed_history.get(event['track_id'], -1)
                    event['speed'] = f"{speed:.1f}" if speed >= 0 else "-"
            
                # 6. send results
                #if new_events:
                #    current_stats = counter.get_statistics()
                #    self.analysisResult.emit(current_stats)
                current_stats = counter.get_statistics()
                current_stats['newly_counted'] = new_events
                self.analysisResult.emit(current_stats)
                    
                # 7. draw lanes and count lines
                for i, polygon in enumerate(counter.lane_polygons):
                    cv2.polylines(frame, [polygon], isClosed=True, color=(255, 255, 0), thickness=line_thickness)
                    line = counter.counting_lines[i]
                    cv2.line(frame, (int(line.coords[0][0]), int(line.coords[0][1])), 
                            (int(line.coords[1][0]), int(line.coords[1][1])), (0, 255, 255), line_thickness)
                    
                # 9. draw detections and speed
                if results.boxes.id is not None:
                    for box, track_id, cls_id in zip(results.boxes.xyxy.cpu(), results.boxes.id.int().cpu(), results.boxes.cls.cpu()):
                        speed = speed_calculator.speed_history.get(int(track_id), -1)
                        speed_text = f" {speed:.1f} km/h" if speed >= 0 else ""
                        label = f"ID:{track_id} {class_names.get(int(cls_id))}{speed_text}"
                        
                        cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), line_thickness)
                        cv2.putText(frame, label, (int(box[0]), int(box[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), line_thickness)
                
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