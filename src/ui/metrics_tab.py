from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QScrollArea, QPushButton


class MetricsTab(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QVBoxLayout(self)
        
        # export button
        export_button = QPushButton("Exportar a .csv")
        main_layout.addWidget(export_button)
        
        # scroll metrics
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        
        content_widget = QWidget()
        self.metrics_layout = QVBoxLayout(content_widget)
        scroll_area.setWidget(content_widget)
            
        # Métricas Generales
        self.general_box = QGroupBox("Métricas Generales (Todos los carriles)")
        general_form = QFormLayout(self.general_box)
        general_form.addRow("Velocidad Promedio Total:", QLabel("- km/h"))
        general_form.addRow("Total de Vehículos Contados:", QLabel("0"))
        
        self.update_metrics_display(1)
        
    def update_metrics_display(self, num_lanes):
        # clean lanes
        while self.metrics_layout.count():
            child = self.metrics_layout.takeAt(0)
            if child.widget():
                if child.widget() != self.general_box:
                    child.widget().deleteLater()
                    
        for i in range(num_lanes):
            lane_box = QGroupBox(f"Métricas del Carril {i+1}")
            lane_form = QFormLayout(lane_box)
            
            lane_form.addRow("Velocidad Promedio:", QLabel("- km/h"))
            lane_form.addRow("Velocidad Máxima:", QLabel("- km/h"))
            lane_form.addRow("Velocidad Mínima:", QLabel("- km/h"))
            
            lane_form.addRow(QLabel("<b>Conteo de Vehículos:</b>"))
            lane_form.addRow("  - Carros:", QLabel("0"))
            lane_form.addRow("  - Motos:", QLabel("0"))
            lane_form.addRow("  - Buses:", QLabel("0"))
            
            lane_form.addRow(QLabel("<b>Distribución de Velocidad:</b>"))
            lane_form.addRow("  - Lentos:", QLabel("0"))
            lane_form.addRow("  - Normales:", QLabel("0"))
            lane_form.addRow("  - Rápidos:", QLabel("0"))
            
            self.metrics_layout.addWidget(lane_box)
            
        # Añadir las métricas generales al final y el stretch
        self.metrics_layout.addWidget(self.general_box)
        self.metrics_layout.addStretch()



