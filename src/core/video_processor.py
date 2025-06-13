import cv2
import logging as log

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage

log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class VideoProcessor(QThread):
    frameReady = Signal(QImage)
    finished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_source = None
        self.is_running = False
    
    def set_video_source(self, source):
        self.video_source = source
        
    @staticmethod
    def get_first_frame(source):
        """capture first frame"""
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            log.error(f"No se pudo abrir la fuente de video: {source}")
            return None, 0, 0
            
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            log.error(f"No se pudo leer el primer fotograma de: {source}")
            return None, 0, 0
        
        # Convertir el fotograma a QImage y obtener dimensiones
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        
        return qt_image.copy(), w, h
        
    def run(self):
        if self.video_source is None:
            log.error(f"No se ha establecido una fuente de video")
            return
            
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            log.error(f"No se puedo abrir la fuente d evideo: {self.video_source}")
            return
        
        self.is_running = True
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            #TODO: logica de deteccion tracking
            
            # comnvert numpy image to QImage
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
            
            # send frame
            self.frameReady.emit(qt_image.copy())
            
        cap.release()
        self.is_running = False
        self.finished.emit()
        log.info("Procesamiento de video finalizado")
        
    def stop(self):
        self.is_running = False