import os
import sys
import numpy as np
from datetime import datetime
from collections import defaultdict
from shapely.geometry import LineString, Point

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.count import CountingVehiclesInterface


class CountingProcessor:
    def __init__(self, lane_polygons: list[list[tuple[int, int]]]):
        """
        Initialize the counting processor class.

        Args:
            lane_polygons list[list[tuple[int, int]]]: List of lanes.
        """
        self.lane_polygons = [np.array(p, dtype=np.int32) for p in lane_polygons]
        self.counting_lines = [self._calculate_counting_line(p) for p in self.lane_polygons]
        
        # Historial para la lógica de cruce de línea
        self.track_history = defaultdict(list)
        
        # Almacenamiento persistente de datos de la sesión
        self.full_event_log = []
        self.speeds_per_lane = defaultdict(list)
        self.vehicle_counts_per_lane = defaultdict(lambda: defaultdict(int))
        
        self.counted_ids_per_lane = defaultdict(list)
        
    def _calculate_counting_line(self, polygon: np.ndarray) -> LineString:
        """
        Calculate the counting line for a given lane polygon.
        
        Args:
            polygon: A numpy array representing the lane polygon.
        
        Returns:
            A LineString object representing the counting line.
        """
        if len(polygon) < 2:
            raise ValueError("Polygon must have at least two points to form a line.")
        
        # ordenate points to find the start and end points
        sorted_by_y = sorted(polygon, key=lambda p: p[1])
        top_points = sorted(sorted_by_y[:2], key=lambda p: p[0])
        bottom_points = sorted(sorted_by_y[2:], key=lambda p: p[0])
        
        # mid point
        mid_top = ((top_points[0][0] + top_points[1][0]) / 2, (top_points[0][1] + top_points[1][1]) / 2)
        mid_bottom = ((bottom_points[0][0] + bottom_points[1][0]) / 2, (bottom_points[0][1] + bottom_points[1][1]) / 2)
        
        # mid line un Y axis
        line_y = (mid_top[1] + mid_bottom[1]) / 3
        
        # counting line
        x_coords = [p[0] for p in polygon]
        
        return LineString([(min(x_coords), line_y), (max(x_coords), line_y)])
    
    def process_frame(self, detections, class_names: dict, speed_history: dict):
        """
        process detections and count vehicles per lane.
        """
        newly_counted_events = []
        
        if detections.boxes.id is None:
            return newly_counted_events
        
        boxes = detections.boxes.xyxy.cpu().numpy()
        track_ids = detections.boxes.id.int().cpu().tolist()
        clss = detections.boxes.cls.cpu().tolist()
        confs = detections.boxes.conf.cpu().tolist()
        
        for box, track_id, cls_id, conf in zip(boxes, track_ids, clss, confs):
            self.track_history[track_id].append(((box[0] + box[2]) / 2, box[3]))
            if len(self.track_history[track_id]) > 2:
                self.track_history[track_id].pop(0)
                
            if len(self.track_history[track_id]) == 2:
                trajectory = LineString(self.track_history[track_id])
                for i, line in enumerate(self.counting_lines):
                    if trajectory.intersects(line) and track_id not in self.counted_ids_per_lane[i]:
                        self.counted_ids_per_lane[i].append(track_id)
                        
                        speed = speed_history.get(track_id, 0)
                        if speed <= 0: continue

                        if speed > 60: status = "Exceso de Velocidad"
                        elif speed < 40: status = "Lento"
                        else: status = "Normal"
                        
                        event = {
                            "track_id": track_id,
                            "timestamp": datetime.now().strftime('%H:%M:%S'),
                            "lane": i + 1,
                            "type": class_names.get(cls_id, "Desconocido"),
                            "speed": f"{speed:.1f}",
                            "confidence": f"{conf*100:.0f}%",
                            "status": status
                        }
                        self.full_event_log.append(event)
                        newly_counted_events.append(event)
                        
                        self.speeds_per_lane[i].append(speed)
                        self.vehicle_counts_per_lane[i][event["type"]] += 1
                        
        return newly_counted_events
    
    def get_statistics(self) -> dict:
        """Calcula y devuelve todas las estadísticas acumuladas."""
        stats = { "lanes": {}, "global": {}, "log_preview": [] }
        
        # Estadísticas por carril
        for lane_idx, speeds in self.speeds_per_lane.items():
            if not speeds: continue
            stats["lanes"][lane_idx] = {
                "avg_speed": np.mean(speeds),
                "min_speed": min(speeds),
                "max_speed": max(speeds),
                "vehicle_counts": self.vehicle_counts_per_lane[lane_idx],
                "speed_dist": {
                    "slow": len([s for s in speeds if s < 40]),
                    "normal": len([s for s in speeds if 40 <= s < 60]),
                    "fast": len([s for s in speeds if s >= 60]),
                }
            }
        
        # Estadísticas globales
        all_speeds = [s for speeds in self.speeds_per_lane.values() for s in speeds]
        stats["global"]["avg_speed"] = np.mean(all_speeds) if all_speeds else 0
        
        global_counts = defaultdict(int)
        for counts in self.vehicle_counts_per_lane.values():
            for v_type, count in counts.items():
                global_counts[v_type] += count
        stats["global"]["vehicle_counts"] = global_counts
        
        # Vista previa del log para el CSV
        stats["log_preview"] = self.full_event_log[-5:] # Últimos 5 eventos
        
        return stats
    