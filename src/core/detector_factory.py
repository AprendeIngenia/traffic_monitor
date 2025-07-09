import logging as log
from .vehicle_detector import VehicleDetection
from .vehicle_detector import VehicleDetectionTensorRT
from models.detection import VehicleDetectionInterface


def get_detector(use_tensorrt: bool = True) -> VehicleDetectionInterface:
    """
    Factory that return vehicle detector instance.
    
    Args:
        use_tensorrt (bool): if is True, inference with TensorRT.
                            if failed or is False, inference with PyTorch.
    Returns:
        An instance that complies with the VehicleDetectionInterface.
    """
    if use_tensorrt:
        try:
            log.info("Initializing with TensorRT...")
            return VehicleDetectionTensorRT()
        except Exception as e:
            log.warning(f"Cannot initializing with TensorRT: {e}. Return PyTorch.")
            return VehicleDetection()
    else:
        log.info("Initializing with PyTorch...")
        return VehicleDetection()
    