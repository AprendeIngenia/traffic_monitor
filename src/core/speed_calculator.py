import cv2
import numpy as np
from collections import defaultdict
from .homography_manager import HomographyManager


class SpeedCalculator:
    def __init__(self, homography_manager: HomographyManager):
        self.hm = homography_manager
        self.kalman_filters = {}
        self.speed_history = defaultdict(lambda: -1)
        
    def _create_kalman_filter(self):
        """Crea un nuevo filtro de Kalman para un objeto."""
        kf = cv2.KalmanFilter(4, 2) # 4 estados (x, y, vx, vy), 2 mediciones (x, y)
        kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
        kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.1
        kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1
        kf.errorCovPost = np.eye(4, dtype=np.float32) * 1
        return kf
        
    def update_speed(self, track_id: int, image_point: tuple, delta_t: float) -> float:
        """
        Update the speed of an object based on its position in the image and its history.
        
        Args:
            track_id (int): The unique identifier for the tracked object.
            image_point (tuple): The current position of the object in the image (x, y).
        
        Returns:
            float: The calculated speed in km/h.
        """
        # iniciar el filtro de Kalman si no existe
        if track_id not in self.kalman_filters:
            self.kalman_filters[track_id] = self._create_kalman_filter()
        
        kf = self.kalman_filters[track_id]
        
        # Actualizar la matriz de transición con el tiempo real transcurrido
        kf.transitionMatrix[0, 2] = delta_t
        kf.transitionMatrix[1, 3] = delta_t
        
        # Predecir el siguiente estado
        kf.predict()
        
        # Transformar la medición de la imagen a coordenadas del mundo real
        real_world_point = self.hm.transform_points([image_point])
        if real_world_point:
            measurement = np.array(real_world_point[0], dtype=np.float32)
            
            # Corregir el estado del filtro con la nueva medición
            kf.correct(measurement)
            
        # El estado corregido contiene [x, y, vx, vy]
        corrected_state = kf.statePost
        vx, vy = corrected_state[2, 0], corrected_state[3, 0]
        
        # Calcular la magnitud de la velocidad en m/s y convertir a km/h
        speed_ms = np.sqrt(vx**2 + vy**2)
        speed_kmh = (speed_ms * 3.6) + 30
        
        last_speed = self.speed_history[track_id]
        if last_speed > 0:
            speed_kmh = (last_speed * 0.9) + (speed_kmh * 0.1)

        self.speed_history[track_id] = speed_kmh
        return speed_kmh
        