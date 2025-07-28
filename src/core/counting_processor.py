import os
import sys
import cv2
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
        
        # history
        self.track_history = defaultdict(list)
        
        # save data
        self.full_event_log = []
        self.speeds_per_lane = defaultdict(list)
        self.vehicle_counts_per_lane = defaultdict(lambda: defaultdict(int))
        
        self.globally_counted_ids = set()
        
    def _calculate_counting_line(self, polygon: np.ndarray) -> LineString:
        """
        Calculate the counting line for a given lane polygon.
        
        Args:
            polygon: A numpy array representing the lane polygon.
        
        Returns:
            A LineString object representing the counting line.
        """
        if len(polygon) < 2:
            return None

        y_coords = polygon[:, 1]
        line_y = np.min(y_coords) + (np.max(y_coords) - np.min(y_coords)) / 3
        x_coords = polygon[:, 0]
        return LineString([(np.min(x_coords), line_y), (np.max(x_coords), line_y)])
    
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
            current_point = ((box[0] + box[2]) / 2, box[3])

            self.track_history[track_id].append(current_point)
            if len(self.track_history[track_id]) > 2:
                self.track_history[track_id].pop(0)

            if len(self.track_history[track_id]) < 2 or track_id in self.globally_counted_ids:
                continue

            # 1. Determinar en qué carril está el vehículo
            for i, polygon in enumerate(self.lane_polygons):
                # Usamos pointPolygonTest para ver si el punto está dentro del polígono del carril
                if cv2.pointPolygonTest(polygon, current_point, False) >= 0:

                    # 2. check LANE
                    trajectory = LineString(self.track_history[track_id])
                    counting_line = self.counting_lines[i]

                    if trajectory.intersects(counting_line):
                        self.globally_counted_ids.add(track_id)

                        speed = speed_history.get(track_id, 0)
                        if speed <= 0: continue

                        if speed > 60:
                            status = "Exceso de Velocidad"
                        elif speed < 40:
                            status = "Lento"
                        else:
                            status = "Normal"

                        event = {
                            "track_id": track_id,
                            "timestamp": datetime.now().strftime('%H:%M:%S'),
                            "lane": i + 1,  # El carril correcto
                            "type": class_names.get(cls_id, "Desconocido"),
                            "speed": f"{speed:.1f}",
                            "confidence": f"{conf * 100:.0f}%",
                            "status": status
                        }
                        self.full_event_log.append(event)
                        newly_counted_events.append(event)

                        self.speeds_per_lane[i].append(speed)
                        self.vehicle_counts_per_lane[i][event["type"]] += 1
                        break

        return newly_counted_events
    
    def get_statistics(self) -> dict:
        """Calcula y devuelve todas las estadísticas acumuladas."""
        stats = { "lanes": {}, "global": {}, "log_preview": [] }
        
        # stats per lane
        for lane_idx, speeds in self.speeds_per_lane.items():
            if not speeds:
                continue
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
        
        # global stats
        all_speeds = [s for speeds in self.speeds_per_lane.values() for s in speeds]
        stats["global"]["avg_speed"] = np.mean(all_speeds) if all_speeds else 0
        
        global_counts = defaultdict(int)
        for counts in self.vehicle_counts_per_lane.values():
            for v_type, count in counts.items():
                global_counts[v_type] += count
        stats["global"]["vehicle_counts"] = global_counts
        stats["log_preview"] = self.full_event_log[-5:]
        return stats
    