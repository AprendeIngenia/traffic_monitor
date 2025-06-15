import cv2
import numpy as np


class MaskProcessing:
    def _init__(self):
        pass
    
    def process_frame(self, frame: np.ndarray, lane_polygons: list[list[tuple[int, int]]]) -> np.ndarray:
        """
        Process the frame to create a mask for the specified lane polygons.
        
        Args:
            frame (np.ndarray): The input video frame.
            lane_polygons (list[list[tuple[int, int]]]): List of lane polygons.
        
        Returns:
            np.ndarray: The processed frame with the mask applied.
        """
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        
        for polygon in lane_polygons:
            cv2.fillPoly(mask, [polygon], 255)
        
        masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
        
        return masked_frame