import logging as log
from collections import deque
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QLabel, QFrame, QGridLayout, QFileDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage

from core.video_processor import VideoProcessor


class VideoAnalysisTab(QWidget):
    videoSourceChanged = Signal(bool)
    firstFrameReady = Signal(QImage, int, int)
    newDataAvailable = Signal(dict, list)
    
    def __init__(self):
        super().__init__()
        
        self.video_source_path = None
        self.video_processor = VideoProcessor()
        self.recent_detections = deque(maxlen=3)
        self.detection_labels = []
        
        # main layout
        main_layout = QHBoxLayout(self)
        
        # left panel
        left_panel = QGroupBox("Detecciones Actuales")
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(300)
        
        # text boxes
        for i in range(3):
            detection_box = QFrame()
            detection_box.setFrameShape(QFrame.StyledPanel)
            detection_layout = QGridLayout(detection_box)
            
            labels = {
                "type": QLabel("<b>Vehículo:</b> -"),
                "confidence": QLabel("<b>Confianza:</b> -%"),
                "speed": QLabel("<b>Velocidad:</b> - km/h"),
                "lane": QLabel("<b>Carril:</b> -")
            }
            
            detection_layout.addWidget(labels["type"], 0, 0)
            detection_layout.addWidget(labels["confidence"], 1, 0)
            detection_layout.addWidget(labels["speed"], 2, 0)
            detection_layout.addWidget(labels["lane"], 3, 0)
            
            self.detection_labels.append(labels)
            left_layout.addWidget(detection_box)
        left_layout.addStretch()
            
        # right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # control buttons
        controls_box = QGroupBox("Controles")
        controls_layout = QHBoxLayout(controls_box)
        
        # buttons
        self.btn_load_video = QPushButton("📂 Cargar Video")
        self.btn_use_camera = QPushButton("📷 Usar Cámara")
        self.btn_start_analysis = QPushButton("▶️ Iniciar Análisis")
        self.btn_stop_analysis = QPushButton("⏹️ Detener Análisis")
        
        # add buttons to layout
        controls_layout.addWidget(self.btn_load_video)
        controls_layout.addWidget(self.btn_use_camera)
        controls_layout.addWidget(self.btn_start_analysis)
        controls_layout.addWidget(self.btn_stop_analysis)
        
        # video area
        self.video_area = QLabel("Área de Video")
        self.video_area.setFrameShape(QFrame.Box)
        self.video_area.setAlignment(Qt.AlignCenter)
        self.video_area.setStyleSheet("background-color: black; color: white;")
        self.video_area.setMinimumSize(1280, 720)
        
        right_layout.addWidget(controls_box)
        right_layout.addWidget(self.video_area, 1)
        
        # Añadir paneles al layout principal
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # connections
        self.btn_start_analysis.setEnabled(False)
        self.btn_stop_analysis.setEnabled(False)

        self.btn_load_video.clicked.connect(self.load_video)
        self.btn_use_camera.clicked.connect(self.use_camera)
        self.btn_start_analysis.clicked.connect(self.start_analysis)
        self.btn_stop_analysis.clicked.connect(self.stop_analysis)
        
        self.video_processor.frameReady.connect(self.update_video_frame)
        self.video_processor.finished.connect(self.on_analysis_finished)
        
    def load_video(self):
        """select file video"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Video", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            self.process_new_source(file_path)
            
    def use_camera(self):
        """select cam (índex 0)."""
        self.process_new_source(0)
        
    def process_new_source(self, source):
        """Centraliza la lógica para una nueva fuente de video."""
        self.video_source_path = source
        self.status_bar.showMessage(f"Cargando fuente: {source}...")
        
        # Obtenemos el primer frame de forma síncrona
        first_frame, width, height = VideoProcessor.get_first_frame(source)
        
        if first_frame:
            self.videoSourceChanged.emit(True)
            self.status_bar.showMessage(f"Fuente cargada ({width}x{height}): {source}")
            # Emitimos la señal con el frame para las otras pestañas
            self.firstFrameReady.emit(first_frame, width, height)
        else:
            self.videoSourceChanged.emit(False)
            self.status_bar.showMessage(f"Error al cargar la fuente: {source}")
        
    def start_analysis(self):
        """start processing video"""
        if self.video_source_path is not None:
            # 1. get points from lane configuration tab
            lane_qpoints = self.window().lane_tab.get_all_lane_points()
            homography_config = self.window().homography_tab.get_homography_data()
            
            # 2. convert points
            lane_tuples = []
            for lane in lane_qpoints:
                lane_tuples.append([(p.x(), p.y()) for p in lane])

            log.info(f"Lane points (converted to tuples): {lane_tuples}")
            log.info(f"Homography config: {homography_config}")
            
            self.video_processor.set_analysis_config(lane_tuples, homography_config)
            
            self.video_processor.set_video_source(self.video_source_path)
            self.video_processor.start()
            self.set_controls_for_analysis(is_running=True)
            
    def stop_analysis(self):
        """stop processing"""
        self.video_processor.stop()
        self.set_controls_for_analysis(is_running=False)
        
    def on_analysis_finished(self):
        """exect when the video finished"""
        self.set_controls_for_analysis(is_running=False)
        self.videoSourceChanged.emit(False)
        self.video_source_path = None
        
    def on_config_status_changed(self, is_ready):
        """Slot enable/disable start button."""
        self.btn_start_analysis.setEnabled(is_ready)
        
    def update_video_frame(self, image):
        """show QImage received from QLabel."""
        pixmap = QPixmap.fromImage(image)
        self.video_area.setPixmap(pixmap.scaled(self.video_area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
    def set_controls_for_analysis(self, is_running: bool):
        """Habilita o deshabilita los botones según el estado del análisis."""
        self.btn_start_analysis.setEnabled(not is_running)
        self.btn_stop_analysis.setEnabled(is_running)
        self.btn_load_video.setEnabled(not is_running)
        self.btn_use_camera.setEnabled(not is_running)
        
    def on_new_analysis_data(self, stats: dict):
        """Recibe datos del procesador, actualiza la UI local y emite una señal."""
        new_events = stats.get("newly_counted", []) # Suponiendo que el paquete de stats contiene esta clave
        for event in new_events:
            self.recent_detections.appendleft(event)
        
        # Actualizar las cajas de "Detecciones Actuales"
        for i in range(3):
            if i < len(self.recent_detections):
                event = self.recent_detections[i]
                # Las claves ahora coinciden con lo que espera la UI
                self.detection_labels[i]["type"].setText(f"<b>Vehículo:</b> {event['type']}")
                self.detection_labels[i]["confidence"].setText(f"<b>Confianza:</b> {event['confidence']}")
                self.detection_labels[i]["speed"].setText(f"<b>Velocidad:</b> {event['speed']} km/h")
                self.detection_labels[i]["lane"].setText(f"<b>Carril:</b> {event['lane']}")
            else:
                # Limpiar cajas no usadas
                self.detection_labels[i]["type"].setText("<b>Vehículo:</b> -")
                self.detection_labels[i]["confidence"].setText("<b>Confianza:</b> -%")
                self.detection_labels[i]["speed"].setText("<b>Velocidad:</b> - km/h")
                self.detection_labels[i]["lane"].setText("<b>Carril:</b> -")

        # Emitir señal para que otros widgets (como MetricsTab) puedan usar los datos
        #self.newDataAvailable.emit(new_events)
        
    @property
    def status_bar(self):
        return self.window().statusBar()
        
        