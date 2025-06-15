import numpy as np

from ultralytics import YOLO
from abc import ABC, abstractmethod
from ultralytics.engine.results import Results


class VehicleDetectionInterface(ABC):
    """Abstract base class for detection vehicles in a frame."""
    @abstractmethod
    def inference(self, image: np.ndarray, classes_to_detect: list[int] = None) -> tuple[list[Results], dict[int, str]]:
        raise NotImplementedError