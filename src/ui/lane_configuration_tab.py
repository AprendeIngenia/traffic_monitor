from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QSpinBox, QFormLayout, QScrollArea, QFrame
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPolygonF, QPen
from PySide6.QtCore import Qt, Signal, QPointF, QPoint


class ClickableLabel(QLabel):
    pointModified = Signal(int, int, QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points_data = []
        self.pixmap_size = QPoint(0,0)
        
    def set_points_data(self, points):
        """Set points data and update the label."""
        self.points_data = points
        
    def set_pixmap_size(self, size):
        """Set the size of the pixmap to scale points correctly."""
        self.pixmap_size = size
        
    def mousePressEvent(self, event):
        if not self.pixmap():
            return
        
        # escale
        widget_pos = event.pos()
        pixmap_w = self.pixmap_size.x()
        pixmap_h = self.pixmap_size.y()
        
        if pixmap_w == 0 or pixmap_h == 0:
            return
        
        # aspect ratio
        scaled_pixmap = self.pixmap().scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - scaled_pixmap.width()) / 2
        offset_y = (self.height() - scaled_pixmap.height()) / 2
        
        img_x = (widget_pos.x() - offset_x) * pixmap_w / scaled_pixmap.width()
        img_y = (widget_pos.y() - offset_y) * pixmap_h / scaled_pixmap.height()
        
        click_pos = QPoint(int(img_x), int(img_y))
        
        # find nearest point
        min_dist = float('inf')
        closest_lane = -1
        closest_point_idx = -1
        
        for lane_idx, lane_points in enumerate(self.points_data):
            for point_idx, point in enumerate(lane_points):
                dist = (click_pos - point).manhattanLength()
                if dist < min_dist and dist < 1000:
                    min_dist = dist
                    closest_lane = lane_idx
                    closest_point_idx = point_idx
                    
        if closest_lane != -1:
            # emit signal with lane index, point index and position
            self.pointModified.emit(closest_lane, closest_point_idx, click_pos)


class LaneConfigurationTab(QWidget):
    lanesChanged = Signal(int)
    configChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        
        self.lane_spinboxes = []
        self.frame_width = 0
        self.frame_height = 0
        self.base_pixmap = None
        
        self.lane_colors = [
            QColor(255, 82, 82, 90),   # Rojo
            QColor(52, 152, 219, 90),  # Azul
            QColor(46, 204, 113, 90),  # Verde
            QColor(241, 196, 15, 90),  # Amarillo
            QColor(155, 89, 182, 90),  # Morado
        ]
        
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
        
        self.preview_area = ClickableLabel("Aquí se mostrará la vista previa de los carriles.")
        self.preview_area.pointModified.connect(self.update_point_from_click)
        self.preview_area.setFrameShape(QFrame.Box)
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setStyleSheet("background-color: black; color: white;")
        self.preview_area.setMinimumSize(1280, 720)
        right_layout.addWidget(self.preview_area)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        self.update_lane_inputs(1)
        
    def get_all_lane_points(self):
        """Get all lane points as a list of lists."""
        all_points = []
        num_lanes = self.spin_num_lanes.value()
        points_per_lane = 4
        
        for i in range(num_lanes):
            lane_points = []
            for j in range(points_per_lane):
                base_idx = i * (points_per_lane * 2) + j * 2
                if base_idx + 1 < len(self.lane_spinboxes):
                    x = self.lane_spinboxes[base_idx].value()
                    y = self.lane_spinboxes[base_idx + 1].value()
                    lane_points.append(QPoint(x, y))
            all_points.append(lane_points)
        return all_points
    
    def redraw_lanes(self):
        """Redraw lanes on the preview area based on current points."""
        if not self.base_pixmap:
            return
        
        pixmap_to_draw = self.base_pixmap.copy()
        painter = QPainter(pixmap_to_draw)
        
        all_lane_points = self.get_all_lane_points()
        self.preview_area.set_points_data(all_lane_points)

        for i, lane_points in enumerate(all_lane_points):
            if len(lane_points) == 4:
                polygon = QPolygonF([QPointF(p) for p in lane_points])
                color = self.lane_colors[i % len(self.lane_colors)]
                
                # Dibujar el polígono relleno
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawPolygon(polygon)
                
                # Dibujar los puntos de los vértices
                pen = QPen(color.darker(150), 2)
                painter.setPen(pen)
                painter.setBrush(Qt.white)
                for point in lane_points:
                    painter.drawEllipse(point, 5, 5)

        painter.end()
        self.preview_area.setPixmap(pixmap_to_draw.scaled(self.preview_area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.validate_config()
        
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
                x_spin.valueChanged.connect(self.redraw_lanes)
                y_spin.valueChanged.connect(self.redraw_lanes)
                lane_form.addRow(f"Punto {j+1}:", coord_layout)
                
            self.lanes_layout.addWidget(lane_box)
            
        self.lanes_layout.addStretch()
        self.update_spinbox_limits()
        # signal
        self.lanesChanged.emit(num_lanes)
        self.redraw_lanes()
        
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
        
        self.base_pixmap = QPixmap.fromImage(image)
        self.preview_area.set_pixmap_size(QPoint(width, height))
        
        self.update_spinbox_limits()
        self.redraw_lanes()
        
    def update_point_from_click(self, lane_idx, point_idx, new_pos):
        """Update point from click."""
        base_idx = lane_idx * 8 + point_idx * 2
        
        # block signals to avoid recursion
        self.lane_spinboxes[base_idx].blockSignals(True)
        self.lane_spinboxes[base_idx + 1].blockSignals(True)
        
        self.lane_spinboxes[base_idx].setValue(new_pos.x())
        self.lane_spinboxes[base_idx + 1].setValue(new_pos.y())
        
        self.lane_spinboxes[base_idx].blockSignals(False)
        self.lane_spinboxes[base_idx + 1].blockSignals(False)
        
        # redraw lanes
        self.redraw_lanes()
        
        
        
        