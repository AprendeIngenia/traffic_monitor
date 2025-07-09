import os
import sys
import torch
import numpy as np
import logging as log

from ultralytics import YOLO
from ultralytics.engine.results import Results

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
        vehicle_model_path = os.path.join(base_dir, "detection_models/torch", "yolo11n.pt")
        
        try:
            self.vehicle_model: YOLO = YOLO(vehicle_model_path).to(self.device)
            log.info(f"model loaded succesfully using: {self.device}")
        except Exception as e:
            log.error(f"model not loaded: {e}")
            raise

    def inference(self, image: np.ndarray, classes_to_detect: list[int] = None) -> tuple[list[Results], dict[int, str]]:
        return self.vehicle_model.track(image, task='detect', conf=0.10, verbose=False, persist=True, imgsz=640, stream=True, half=True, classes=classes_to_detect), self.vehicle_model.names
    

class VehicleDetectionTensorRT(VehicleDetectionInterface):
    def __init__(self):
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            log.info("CUDA available. inference with TensorRT Engine.")
        else:
            log.error("¡ERROR! TensorRT require a GPU NVIDIA with CUDA.")
            raise RuntimeError("TensorRT not loaded.")
        
        # model
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vehicle_model_path = os.path.join(base_dir, "detection_models/tensorRT", "yolo11n.engine")
        
        try:
            self.vehicle_model: YOLO = YOLO(vehicle_model_path)
            log.info(f"TensorRT model (.engine) loaded succesfully: {vehicle_model_path}")
        except Exception as e:
            log.error(f"TensorRT model not loaded: {e}")
            raise
        
    def inference(self, image: np.ndarray, classes_to_detect: list[int] = None) -> tuple[list[Results], dict[int, str]]:
        return self.vehicle_model.track(image, task='detect', conf=0.10, verbose=False, persist=True, imgsz=640, stream=True, half=True, classes=classes_to_detect), self.vehicle_model.names
