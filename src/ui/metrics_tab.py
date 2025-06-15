import csv
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QScrollArea, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView)


class MetricsTab(QWidget):
    def __init__(self):
        super().__init__()
        
        self.stats_data = {}
        self.vehicle_types = ["car", "motorcycle", "bus", "truck", "bicycle"]
        
        main_layout = QVBoxLayout(self)
        self.export_button = QPushButton("📄 Exportar a .csv")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_to_csv)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        content_widget = QWidget()
        self.metrics_layout = QVBoxLayout(content_widget)
        scroll_area.setWidget(content_widget)
        
        main_layout.addWidget(self.export_button)
        main_layout.addWidget(scroll_area)
        
        # Contenedores para las UI de las métricas
        self.lane_widgets = {}
        self.global_widgets = {}
        
        self.update_metrics_display(1)
        
    def update_metrics_display(self, num_lanes):
        # clean lanes
        while self.metrics_layout.count():
            child = self.metrics_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.lane_widgets.clear()
                    
        # Métricas por Carril
        for i in range(num_lanes):
            lane_box = QGroupBox(f"Métricas del Carril {i+1}")
            form = QFormLayout(lane_box)
            widgets = {
                "avg_speed": QLabel("- km/h"), "min_speed": QLabel("- km/h"), "max_speed": QLabel("- km/h"),
                "counts": {v_type: QLabel("0") for v_type in self.vehicle_types},
                "dist": {
                    "slow": QLabel("0"), "normal": QLabel("0"), "fast": QLabel("0")
                }
            }
            form.addRow("Velocidad Promedio:", widgets["avg_speed"])
            form.addRow("Velocidad Mín/Máx:", widgets["min_speed"])
            # form.addRow("Velocidad Máxima:", widgets["max_speed"]) # Combinado para ahorrar espacio
            
            form.addRow(QLabel("<b>Conteo de Vehículos:</b>"))
            for v_type in self.vehicle_types:
                form.addRow(f"  - {v_type.capitalize()}:", widgets["counts"][v_type])
                
            form.addRow(QLabel("<b>Distribución de Velocidad:</b>"))
            form.addRow("  - Lentos (<40 km/h):", widgets["dist"]["slow"])
            form.addRow("  - Normales (40-60 km/h):", widgets["dist"]["normal"])
            form.addRow("  - Rápidos (>60 km/h):", widgets["dist"]["fast"])
            
            self.metrics_layout.addWidget(lane_box)
            self.lane_widgets[i] = widgets

        # Métricas Globales
        global_box = QGroupBox("Métricas Globales")
        global_form = QFormLayout(global_box)
        self.global_widgets = {
            "avg_speed": QLabel("- km/h"),
            "counts": {v_type: QLabel("0") for v_type in self.vehicle_types},
            "preview_table": QTableWidget()
        }
        self.global_widgets["preview_table"].setRowCount(5)
        self.global_widgets["preview_table"].setColumnCount(6)
        self.global_widgets["preview_table"].setHorizontalHeaderLabels(["Hora", "Carril", "Tipo", "Velocidad", "Confianza", "Estado"])
        self.global_widgets["preview_table"].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        global_form.addRow("Velocidad Promedio Total:", self.global_widgets["avg_speed"])
        global_form.addRow(QLabel("<b>Conteo Total de Vehículos:</b>"))
        for v_type in self.vehicle_types:
            global_form.addRow(f"  - {v_type.capitalize()}:", self.global_widgets["counts"][v_type])
        global_form.addRow(QLabel("<b>Vista Previa de Datos a Exportar:</b>"))
        global_form.addRow(self.global_widgets["preview_table"])
        
        self.metrics_layout.addWidget(global_box)
        self.metrics_layout.addStretch()
                            
    def update_statistics(self, stats: dict):
        """Recibe el paquete completo de estadísticas y actualiza toda la UI."""
        self.stats_data = stats
        self.export_button.setEnabled(bool(stats.get("log_preview")))

        # Actualizar métricas por carril
        for lane_idx, lane_stats in stats.get("lanes", {}).items():
            if lane_idx in self.lane_widgets:
                widgets = self.lane_widgets[lane_idx]
                widgets["avg_speed"].setText(f"{lane_stats['avg_speed']:.1f} km/h")
                widgets["min_speed"].setText(f"{lane_stats['min_speed']:.1f} / {lane_stats['max_speed']:.1f} km/h")
                for v_type, count in lane_stats["vehicle_counts"].items():
                    if v_type in widgets["counts"]: widgets["counts"][v_type].setText(str(count))
                widgets["dist"]["slow"].setText(str(lane_stats["speed_dist"]["slow"]))
                widgets["dist"]["normal"].setText(str(lane_stats["speed_dist"]["normal"]))
                widgets["dist"]["fast"].setText(str(lane_stats["speed_dist"]["fast"]))
        
        # Actualizar métricas globales
        glob_stats = stats.get("global", {})
        if glob_stats:
            self.global_widgets["avg_speed"].setText(f"{glob_stats['avg_speed']:.1f} km/h")
            for v_type, count in glob_stats["vehicle_counts"].items():
                if v_type in self.global_widgets["counts"]: self.global_widgets["counts"][v_type].setText(str(count))

        # Actualizar tabla de vista previa
        table = self.global_widgets["preview_table"]
        log_preview = stats.get("log_preview", [])
        table.setRowCount(len(log_preview))
        for row, event in enumerate(log_preview):
            for col, key in enumerate(["timestamp", "lane", "type", "speed", "confidence", "status"]):
                table.setItem(row, col, QTableWidgetItem(str(event.get(key, ''))))
                
    def export_to_csv(self):
        """Guarda el registro completo de eventos en un archivo CSV."""
        if not self.stats_data.get("full_log"): # Comprobar que hay datos para exportar
            # O usar `counter.full_event_log` si se pasa el objeto entero
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = f"reporte_trafico_{timestamp}.csv"
        
        filePath, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", default_path, "CSV Files (*.csv)")
        
        if filePath:
            try:
                with open(filePath, 'w', newline='', encoding='utf-8') as csvfile:
                    # Usar los encabezados del primer evento si existen
                    if self.stats_data["full_log"]:
                        headers = self.stats_data["full_log"][0].keys()
                        writer = csv.DictWriter(csvfile, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(self.stats_data["full_log"])
            except IOError as e:
                print(f"Error al guardar el archivo: {e}")



