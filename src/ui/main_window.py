from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QStatusBar
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

from .video_analysis_tab import VideoAnalysisTab
from .lane_configuration_tab import LaneConfigurationTab
from .homography_configuration_tab import HomographyConfigurationTab
from .metrics_tab import MetricsTab

class MainWindow(QMainWindow):
    configStatusChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Sistema de Monitoreo de Tráfico")
        self.setGeometry(100, 100, 1400, 900)
        
        # config state
        self.is_lane_config_valid = False
        self.is_homography_config_valid = False
        self.has_video_source = False
        
        # central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # create tab widget
        self.tab_widget = QTabWidget()
        
        # add tabs
        self.video_tab = VideoAnalysisTab()
        self.lane_tab = LaneConfigurationTab()
        self.homography_tab = HomographyConfigurationTab()
        self.metrics_tab = MetricsTab()
        
        self.tab_widget.addTab(self.video_tab, "Análisis de Video")
        self.tab_widget.addTab(self.lane_tab, "Configuración de Carriles")
        self.tab_widget.addTab(self.homography_tab, "Corrección Homográfica")
        self.tab_widget.addTab(self.metrics_tab, "Métricas")
        
        layout.addWidget(self.tab_widget)
        
        self.setup_menu()
        self.setup_status_bar()
        self.setup_connections()

    def setup_menu(self):
        # create menu bar
        menu_bar = self.menuBar()
        
        # file menu
        file_menu = menu_bar.addMenu("Archivo")
        
        load_project = QAction("Cargar Proyecto", self)
        save_project = QAction("Guardar Proyecto", self)
        export_data = QAction("Exportar Datos", self)
        
        file_menu.addAction(load_project)
        file_menu.addAction(save_project)
        file_menu.addSeparator()
        file_menu.addAction(export_data)
        
        # config menu
        config_menu = menu_bar.addMenu("Configuración")
        
        video_settings = QAction("Configuración de Video", self)
        detection_settings = QAction("Configuración de Detección", self)
        
        config_menu.addAction(video_settings)
        config_menu.addAction(detection_settings)
        
    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
        
    def setup_connections(self):
        """connect al signals with slots"""
        # lanes_config_tab -> metrics_tab
        self.lane_tab.lanesChanged.connect(self.metrics_tab.update_metrics_display)
        
        # first frame
        self.video_tab.firstFrameReady.connect(self.lane_tab.update_preview_image)
        self.video_tab.firstFrameReady.connect(self.homography_tab.update_preview_image)
        self.video_tab.firstFrameReady.connect(lambda img, w, h: self.video_tab.update_video_frame(img))
        
        # config validation
        self.lane_tab.configChanged.connect(self.on_lane_config_changed)
        self.homography_tab.configChanged.connect(self.on_homography_config_changed)
        self.video_tab.videoSourceChanged.connect(self.on_video_source_changed)
        
        # mainwindow -> video button
        self.configStatusChanged.connect(self.video_tab.on_config_status_changed)
        
        # mainwindow -> metrics tab
        self.video_tab.video_processor.analysisResult.connect(self.video_tab.on_new_analysis_data)
        self.video_tab.video_processor.analysisResult.connect(self.metrics_tab.update_statistics)
        
    def on_lane_config_changed(self, is_valid):
        self.is_lane_config_valid = is_valid
        self._check_overall_config()
    
    def on_homography_config_changed(self, is_valid):
        self.is_homography_config_valid = is_valid
        self._check_overall_config()
        
    def on_video_source_changed(self, has_source):
        self.has_video_source = has_source
        self._check_overall_config()
        
    def _check_overall_config(self):
        """check all validations."""
        is_ready = self.is_lane_config_valid and self.is_homography_config_valid and self.has_video_source
        self.configStatusChanged.emit(is_ready)
        