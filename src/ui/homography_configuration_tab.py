from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QFormLayout, QLineEdit, QFrame, QSpinBox
from PySide6.QtCore import Qt, Signal, QPoint, QPointF
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont


class ClickableLabel(QLabel):
    pointModified = Signal(int, QPoint) # point_global_idx, new_pos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.points_data = []
        self.pixmap_size = QPoint(0,0)

    def set_points_data(self, points):
        self.points_data = points

    def set_pixmap_size(self, size):
        self.pixmap_size = size

    def mousePressEvent(self, event):
        if not self.pixmap(): return
        
        widget_pos = event.pos()
        pixmap_w, pixmap_h = self.pixmap_size.x(), self.pixmap_size.y()
        if pixmap_w == 0 or pixmap_h == 0: return

        scaled_pixmap = self.pixmap().scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - scaled_pixmap.width()) / 2
        offset_y = (self.height() - scaled_pixmap.height()) / 2
        img_x = (widget_pos.x() - offset_x) * pixmap_w / scaled_pixmap.width()
        img_y = (widget_pos.y() - offset_y) * pixmap_h / scaled_pixmap.height()
        click_pos = QPoint(int(img_x), int(img_y))

        min_dist = float('inf')
        closest_point_idx = -1
        for i, point in enumerate(self.points_data):
            dist = (click_pos - point).manhattanLength()
            if dist < min_dist and dist < 1000:
                min_dist = dist
                closest_point_idx = i
        
        if closest_point_idx != -1:
            self.pointModified.emit(closest_point_idx, click_pos)


class HomographyConfigurationTab(QWidget):
    configChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self.all_inputs = []
        self.coord_spinboxes = []
        self.distance_lineedits = []
        self.frame_width = 0
        self.frame_height = 0
        self.base_pixmap = None
        
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
        
        self.preview_area = ClickableLabel()
        self.preview_area.pointModified.connect(self.update_point_from_click)
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
            dist_input.setPlaceholderText("e.g., 5.5")
            dist_input.textChanged.connect(self.redraw_lines)
            self.all_inputs.append(dist_input)
            self.distance_lineedits.append(dist_input)
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
        self.all_inputs.extend([x_spin, y_spin])
        
        x_spin.valueChanged.connect(self.validate_config)
        y_spin.valueChanged.connect(self.validate_config)
        
        return coord_layout
    
    def get_all_points(self):
        """Get all lane points as a list of lists."""
        points = []
        for i in range(0, len(self.coord_spinboxes), 2):
            x = self.coord_spinboxes[i].value()
            y = self.coord_spinboxes[i+1].value()
            points.append(QPoint(x,y))
        return points
    
    def redraw_lines(self):
        if not self.base_pixmap: return

        pixmap_to_draw = self.base_pixmap.copy()
        painter = QPainter(pixmap_to_draw)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        
        all_points = self.get_all_points()
        self.preview_area.set_points_data(all_points)

        # 4 pares de puntos en total (8 puntos)
        for i in range(4):
            p1_idx = i * 2
            p2_idx = i * 2 + 1
            
            p1 = all_points[p1_idx]
            p2 = all_points[p2_idx]
            
            is_vertical_group = i < 2 # Los primeros 2 pares son verticales
            color = Qt.red if is_vertical_group else Qt.blue
            
            pen = QPen(color, 3)
            painter.setPen(pen)
            painter.setBrush(Qt.white)
            
            # Dibujar línea y puntos
            painter.drawLine(p1, p2)
            painter.drawEllipse(p1, 6, 6)
            painter.drawEllipse(p2, 6, 6)
            
            # Dibujar texto de distancia
            dist_text = self.distance_lineedits[i].text() + " m"
            mid_point = (p1 + p2) / 2
            painter.setPen(Qt.white)
            painter.drawText(mid_point.x() + 10, mid_point.y(), dist_text)

        painter.end()
        self.preview_area.setPixmap(pixmap_to_draw.scaled(self.preview_area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.validate_config()
    
    def update_spinbox_limits(self):
        for i, spinbox in enumerate(self.coord_spinboxes):
            is_x = i % 2 == 0
            spinbox.setMaximum(self.frame_width if is_x else self.frame_height)
    
    def validate_config(self):
        """check inputs."""
        all_filled = all(
            (isinstance(w, QSpinBox)) or 
            (isinstance(w, QLineEdit) and w.text().strip() != "")
            for w in self.all_inputs
        )
        is_valid = all_filled and self.frame_width > 0
        self.configChanged.emit(is_valid)
        
    def update_preview_image(self, image: QImage, width: int, height: int):
        self.frame_width = width
        self.frame_height = height
        
        self.base_pixmap = QPixmap.fromImage(image)
        self.preview_area.set_pixmap_size(QPoint(width, height))
        
        self.update_spinbox_limits()
        self.redraw_lines()
        
    def update_point_from_click(self, point_idx, new_pos):
        base_spinbox_idx = point_idx * 2
        
        self.coord_spinboxes[base_spinbox_idx].blockSignals(True)
        self.coord_spinboxes[base_spinbox_idx+1].blockSignals(True)
        
        self.coord_spinboxes[base_spinbox_idx].setValue(new_pos.x())
        self.coord_spinboxes[base_spinbox_idx+1].setValue(new_pos.y())
        
        self.coord_spinboxes[base_spinbox_idx].blockSignals(False)
        self.coord_spinboxes[base_spinbox_idx+1].blockSignals(False)
        
        self.redraw_lines()

