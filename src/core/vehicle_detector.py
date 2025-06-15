import os
import sys
import torch
import numpy as np
import logging as log

from ultralytics import YOLO
from ultralytics.engine.results import Results

#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.detection import VehicleDetectionInterface


class VehicleDetection(VehicleDetectionInterface):
    def __init__(self):
        # device
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            log.info("Using Apple Silicon MPS backend for PyTorch")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            log.info("Using CUDA for PyTorch")
        else:
            self.device = torch.device("cpu")
            log.info("Using CPU for PyTorch")

        # model
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vehicle_model_path = os.path.join(base_dir, "detection_models", "yolo11s.pt")
        
        try:
            self.vehicle_model: YOLO = YOLO(vehicle_model_path).to(self.device)
            log.info(f"model loaded succesfully using: {self.device}")
        except Exception as e:
            log.error(f"model not loaded: {e}")
            raise
        

    def inference(self, image: np.ndarray, classes_to_detect: list[int] = None) -> tuple[list[Results], dict[int, str]]:
        return self.vehicle_model.track(image, conf=0.3, verbose=False, persist=True, imgsz=640, stream=True, half=True, classes=classes_to_detect), self.vehicle_model.names
