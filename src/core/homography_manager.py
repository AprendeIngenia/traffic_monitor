import cv2
import numpy as np
import logging as log


class HomographyManager:
    def __init__(self, homography_config: dict):
        """
        Initialize the HomographyManager with a configuration dictionary.
        Args:
            homography_config (dict): A dictionary with coordinate points and real distances.
        """
        self.matrix =None
        self._calculate_homography_matrix(homography_config)
        
    def _calculate_homography_matrix(self, config: dict):
        """
        Calculate the homography matrix from the configuration dictionary.
        Args:
            config (dict): A dictionary with coordinate points and real distances.
        """
        
        img_pts = config.get("image_points")
        width_m = config.get("real_width_m")
        length_m = config.get("real_length_m")
        
        if not all([img_pts, width_m, length_m]) or len(img_pts) != 4:
            log.error("Configuración de homografía inválida. Se necesitan 4 puntos, ancho y largo.")
            return
        
        # Convertir puntos de imagen a formato adecuado
        src_points = np.float32(img_pts)
        
        # Puntos de destino en el mundo real (un rectángulo perfecto)
        # El orden debe coincidir con cómo se seleccionaron en la UI
        # Por ejemplo: Arriba-Izquierda, Arriba-Derecha, Abajo-Derecha, Abajo-Izquierda
        dst_points = np.float32([
            [0, length_m],         # P1: Arriba-Izquierda
            [width_m, length_m],   # P2: Arriba-Derecha
            [width_m, 0],          # P3: Abajo-Derecha
            [0, 0]                 # P4: Abajo-Izquierda
        ])
        
        try:
            self.matrix, _ = cv2.findHomography(src_points, dst_points)
            if self.matrix is not None:
                log.info("Matriz de homografía de 4 puntos calculada exitosamente.")
            else:
                log.error("Fallo al calcular la matriz de homografía.")
        except Exception as e:
            log.error(f"Error en cv2.findHomography: {e}")
            self.matrix = None
            
    def transform_points(self, points: list[tuple]) -> list[tuple]:
        """
        Transforma una lista de puntos de la imagen a coordenadas del mundo real.
        """
        if self.matrix is None or not points:
            return None
            
        points_np = np.float32(points).reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(points_np, self.matrix)
        
        return [tuple(p[0]) for p in transformed] if transformed is not None else None
        
