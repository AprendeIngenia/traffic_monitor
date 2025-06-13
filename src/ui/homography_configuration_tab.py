from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QFormLayout, QLineEdit, QFrame, QSpinBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap

class HomographyConfigurationTab(QWidget):
    configChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self.homography_inputs = [] # save: SpinBoxes & QLineEdits
        self.coord_spinboxes = []   # only coordenates
        self.frame_width = 0
        self.frame_height = 0
        
        main_layout = QHBoxLayout(self)
        
        # left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(450)
        
        # vertical points (reds)
        vertical_box = QGroupBox("Puntos Verticales (Corrección de Escala)")
        vertical_form = QFormLayout(vertical_box)
        self._create_homography_fields(vertical_form, "V", 2)
        
        # horizontal points (blues)
        horizontal_box = QGroupBox("Puntos Horizontales (Corrección de Perspectiva)")
        horizontal_form = QFormLayout(horizontal_box)
        self._create_homography_fields(horizontal_form, "H", 2)
        
        left_layout.addWidget(vertical_box)
        left_layout.addWidget(horizontal_box)
        left_layout.addStretch()
        
        # right panel
        right_panel = QGroupBox("Vista Previa de Puntos")
        right_layout = QVBoxLayout(right_panel)
        preview_label = QLabel("Aquí se mostrarán los puntos:<br><span style='color:red;'>● Puntos Verticales</span><br><span style='color:blue;'>● Puntos Horizontales</span>")
        preview_label.setAlignment(Qt.AlignTop)
        
        self.preview_area = QLabel()
        self.preview_area.setFrameShape(QFrame.Box)
        self.preview_area.setMinimumSize(1280, 720)
        self.preview_area.setStyleSheet("background-color: black; color: white;")
        right_layout.addWidget(preview_label)
        right_layout.addWidget(self.preview_area, 1)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        self.validate_config()
        
    def _create_homography_fields(self, form_layout, prefix, num_pairs):
        """Homography fields."""
        for i in range(num_pairs):
            # Campos de coordenadas con QSpinBox
            form_layout.addRow(f"Punto {prefix}{2*i+1}:", self._create_coord_spinboxes())
            form_layout.addRow(f"Punto {prefix}{2*i+2}:", self._create_coord_spinboxes())
            
            # Campo de distancia con QLineEdit
            dist_input = QLineEdit()
            dist_input.textChanged.connect(self.validate_config)
            self.homography_inputs.append(dist_input)
            form_layout.addRow(f"Distancia Real {i+1} (m):", dist_input)
            
    def _create_coord_spinboxes(self):
        """Crea y devuelve un layout con dos QSpinBox para X e Y."""
        x_spin = QSpinBox()
        y_spin = QSpinBox()
        
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel("X:"))
        coord_layout.addWidget(x_spin)
        coord_layout.addWidget(QLabel("Y:"))
        coord_layout.addWidget(y_spin)
        
        self.coord_spinboxes.extend([x_spin, y_spin])
        self.homography_inputs.extend([x_spin, y_spin])
        
        x_spin.valueChanged.connect(self.validate_config)
        y_spin.valueChanged.connect(self.validate_config)
        
        return coord_layout
    
    def update_spinbox_limits(self):
        for i, spinbox in enumerate(self.coord_spinboxes):
            is_x = i % 2 == 0
            spinbox.setMaximum(self.frame_width if is_x else self.frame_height)
    
    def validate_config(self):
        """check inputs."""
        all_filled = all(
            (isinstance(w, QSpinBox) and w.value() >= 0) or \
            (isinstance(w, QLineEdit) and w.text().strip() != "")
            for w in self.homography_inputs
        )
        is_valid = all_filled and self.frame_width > 0
        self.configChanged.emit(is_valid)
        
    def update_preview_image(self, image: QImage, width: int, height: int):
        self.frame_width = width
        self.frame_height = height
        
        pixmap = QPixmap.fromImage(image)
        self.preview_area.setPixmap(pixmap.scaled(self.preview_area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self.update_spinbox_limits()
        self.validate_config()

