from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QSpinBox, QFormLayout, QScrollArea, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap


class LaneConfigurationTab(QWidget):
    lanesChanged = Signal(int)
    configChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        
        self.lane_spinboxes = []
        self.frame_width = 0
        self.frame_height = 0
        
        # Layout principal
        main_layout = QHBoxLayout(self)
        
        # left panel
        left_panel = QGroupBox("Configuración de Carriles")
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(400)
        
        # number of lanes
        form_layout = QFormLayout()
        self.spin_num_lanes = QSpinBox()
        self.spin_num_lanes.setMinimum(1)
        self.spin_num_lanes.setValue(1)
        form_layout.addRow("Número de carriles:", self.spin_num_lanes)
        
        left_layout.addLayout(form_layout)
        
        # lane inputs
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.lanes_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area)
        
        # connect spinbox to update inputs
        self.spin_num_lanes.valueChanged.connect(self.update_lane_inputs)
        
        # right panel
        right_panel = QGroupBox("Vista Previa de Carriles")
        right_layout = QVBoxLayout(right_panel)
        
        self.preview_area = QLabel("Aquí se mostrará la vista previa de los carriles.")
        self.preview_area.setFrameShape(QFrame.Box)
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setStyleSheet("background-color: black; color: white;")
        self.preview_area.setMinimumSize(1280, 720)
        right_layout.addWidget(self.preview_area)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        self.update_lane_inputs(1)
        
    def update_lane_inputs(self, num_lanes):
        # clean layout
        while self.lanes_layout.count():
            child = self.lanes_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.lane_spinboxes.clear()
        
        # new group box
        for i in range(num_lanes):
            lane_box = QGroupBox(f"Carril {i+1}")
            lane_form = QFormLayout(lane_box)
            for j in range(4):
                x_spin = QSpinBox()
                y_spin = QSpinBox()
                
                coord_layout = QHBoxLayout()
                coord_layout.addWidget(QLabel("X:"))
                coord_layout.addWidget(x_spin)
                coord_layout.addWidget(QLabel("Y:"))
                coord_layout.addWidget(y_spin)
                
                # save spinboxes
                self.lane_spinboxes.extend([x_spin, y_spin])
                
                # connect validation
                x_spin.valueChanged.connect(self.validate_config)
                y_spin.valueChanged.connect(self.validate_config)
                
                lane_form.addRow(f"Punto {j+1}:", coord_layout)
            self.lanes_layout.addWidget(lane_box)
            
        self.lanes_layout.addStretch()
        self.update_spinbox_limits()
        # signal
        self.lanesChanged.emit(num_lanes)
        self.validate_config()
        
    def update_spinbox_limits(self):
        """Actualiza los límites de todos los spinboxes de coordenadas."""
        for i, spinbox in enumerate(self.lane_spinboxes):
            # Los pares son X, los impares son Y
            is_x = i % 2 == 0
            spinbox.setMaximum(self.frame_width if is_x else self.frame_height)
        
    def validate_config(self):
        """check inputs"""
        is_valid = self.frame_width > 0 and self.frame_height > 0
        self.configChanged.emit(is_valid)
        
    def update_preview_image(self, image: QImage, width: int, height: int):
        """Slot to receibed fisrt frame."""
        self.frame_width = width
        self.frame_height = height
        
        pixmap = QPixmap.fromImage(image)
        self.preview_area.setPixmap(pixmap.scaled(self.preview_area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # update spinboxes limits
        self.update_spinbox_limits()
        self.validate_config()
        
        
        
        