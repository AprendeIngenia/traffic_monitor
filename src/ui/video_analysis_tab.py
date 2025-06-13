from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QLabel, QFrame, QGridLayout, QFileDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage

from core.video_processor import VideoProcessor


class VideoAnalysisTab(QWidget):
    videoSourceChanged = Signal(bool)
    firstFrameReady = Signal(QImage, int, int)
    
    def __init__(self):
        super().__init__()
        
        self.video_source_path = None
        self.video_processor = VideoProcessor()
        
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
            
            detection_layout.addWidget(QLabel(f"<b>Vehículo:</b> -"), 0, 0)
            detection_layout.addWidget(QLabel(f"<b>Confianza:</b> -%"), 1, 0)
            detection_layout.addWidget(QLabel(f"<b>Velocidad:</b> - km/h"), 2, 0)
            detection_layout.addWidget(QLabel(f"<b>Carril:</b> -"), 3, 0)
            
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
        
    @property
    def status_bar(self):
        return self.window().statusBar()
        
        