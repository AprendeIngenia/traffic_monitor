import numpy as np

from typing import Tuple
from collections import defaultdict
from abc import ABC, abstractmethod
from ultralytics.engine.results import Results


class CountingVehiclesInterface(ABC):
    """
    Abstract base class for counting vehicles in a video stream.
    """
    def __init__(self):
        self.vehicle_types_per_lane = defaultdict(dict)

    @abstractmethod
    def count(self, image: np.ndarray, sack_track: Results, sack_classes: list) -> Tuple[int, np.ndarray]:
        raise NotImplementedError