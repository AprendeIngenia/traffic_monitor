import csv
import logging as log
from collections import deque
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QScrollArea, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView)


class MetricsTab(QWidget):
    def __init__(self):
        super().__init__()

        self.full_event_log = []
        self.last_event_time_by_lane = {}
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
        
        # UI metrics
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
        self.full_event_log.clear()
        self.last_event_time_by_lane.clear()
        self.export_button.setEnabled(False)
                    
        # lane metrics
        for i in range(num_lanes):
            lane_box = QGroupBox(f"Métricas del Carril {i + 1}")
            form = QFormLayout(lane_box)

            widgets = {
                "avg_speed": QLabel("- km/h"), "min_speed": QLabel("- km/h"),
                "counts": {v_type: QLabel("0") for v_type in self.vehicle_types},
                "dist": {"slow": QLabel("0"), "normal": QLabel("0"), "fast": QLabel("0")}
            }

            form.addRow("Velocidad Promedio:", widgets["avg_speed"])
            form.addRow("Velocidad Mín/Máx:", widgets["min_speed"])
            form.addRow(QLabel("<b>Conteo de Vehículos:</b>"))

            for v_type in self.vehicle_types:
                form.addRow(f"  - {v_type.capitalize()}:", widgets["counts"][v_type])

            form.addRow(QLabel("<b>Distribución de Velocidad:</b>"))
            form.addRow("  - Lentos (<40 km/h):", widgets["dist"]["slow"])
            form.addRow("  - Normales (40-60 km/h):", widgets["dist"]["normal"])
            form.addRow("  - Rápidos (>60 km/h):", widgets["dist"]["fast"])

            self.metrics_layout.addWidget(lane_box)
            self.lane_widgets[i] = widgets

        # global metrics
        global_box = QGroupBox("Métricas Globales")
        global_form = QFormLayout(global_box)
        self.global_widgets = {
            "avg_speed": QLabel("- km/h"),
            "counts": {v_type: QLabel("0") for v_type in self.vehicle_types},
            "preview_table": QTableWidget()
        }

        self.global_widgets["preview_table"].setRowCount(3)
        self.global_widgets["preview_table"].setColumnCount(7)
        self.global_widgets["preview_table"].setHorizontalHeaderLabels(["Hora", "Carril", "Tipo", "Velocidad", "Headway (s)", "Confianza", "ID"])
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
        """update UI."""
        new_events = stats.get("newly_counted", [])
        if new_events:
            processed_events = self._process_events_for_headway(new_events)
            self.full_event_log.extend(processed_events)
            self.export_button.setEnabled(True)

        # update metrics
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
        
        # update global metrics
        glob_stats = stats.get("global", {})
        if glob_stats:
            self.global_widgets["avg_speed"].setText(f"{glob_stats['avg_speed']:.1f} km/h")
            for v_type, count in glob_stats["vehicle_counts"].items():
                if v_type in self.global_widgets["counts"]:
                    self.global_widgets["counts"][v_type].setText(str(count))

        # update table
        table = self.global_widgets["preview_table"]
        log_preview = self.full_event_log[-3:]

        for row in range(3):
            if row < len(log_preview):
                event = log_preview[-(row + 1)]
                table.setItem(row, 0, QTableWidgetItem(str(event.get("timestamp", ''))))
                table.setItem(row, 1, QTableWidgetItem(str(event.get("lane", ''))))
                table.setItem(row, 2, QTableWidgetItem(str(event.get("type", ''))))
                table.setItem(row, 3, QTableWidgetItem(str(event.get("speed", ''))))
                table.setItem(row, 4, QTableWidgetItem(str(event.get("time_headway", '--'))))
                table.setItem(row, 5, QTableWidgetItem(str(event.get("confidence", ''))))
                table.setItem(row, 6, QTableWidgetItem(str(event.get("track_id", ''))))
            else:
                for col in range(table.columnCount()):
                    table.setItem(row, col, QTableWidgetItem(""))

    def _process_events_for_headway(self, events: list) -> list:
        """add time headway"""
        processed = []
        for event in events:
            lane = event.get("lane")
            timestamp_str = event.get("timestamp")

            try:
                # convert to string
                current_time = datetime.strptime(timestamp_str, "%H:%M:%S")
            except (ValueError, TypeError):
                log.warning(f"Formato de timestamp inválido: {timestamp_str}. Saltando cálculo de headway.")
                event['time_headway'] = '--'
                processed.append(event)
                continue

            # calculate headway
            if lane in self.last_event_time_by_lane:
                last_time = self.last_event_time_by_lane[lane]
                time_diff = (current_time - last_time).total_seconds()
                event['time_headway'] = f"{time_diff:.1f}"
            else:
                # first vehicle
                event['time_headway'] = "--"

            # update
            self.last_event_time_by_lane[lane] = current_time
            processed.append(event)

        return processed
                
    def export_to_csv(self):
        """save CSV."""
        if not self.full_event_log:
            log.warning("No hay datos para exportar.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = f"reporte_trafico_{timestamp}.csv"
        filePath, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", default_path, "CSV Files (*.csv)")
        
        if filePath:
            try:
                with open(filePath, 'w', newline='', encoding='utf-8') as csvfile:
                    if self.full_event_log:
                        headers = self.full_event_log[0].keys()
                        writer = csv.DictWriter(csvfile, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(self.full_event_log)
                log.info(f"Reporte guardado exitosamente en: {filePath}")
            except IOError as e:
                print(f"Error al guardar el archivo: {e}")



