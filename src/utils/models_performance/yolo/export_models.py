import logging as log
from ultralytics import YOLO

log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

try:
    # Load a model
    log.info("Loading YOLO model...")
    model = YOLO("models/yolo11m.pt")

    # Export the model
    model.export(format="engine", imgsz=640, batch=1, half=True, workspace=4, verbose=True, device=0)
    
    log.info("Model exported successfully. ✅")
    
except Exception as e:
    log.error(f"❌ Ocurrió un error crítico durante la exportación: {e}", exc_info=True)