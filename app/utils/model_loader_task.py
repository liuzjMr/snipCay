from pdb import run
from PyQt6.QtCore import QThread, pyqtSignal
from app.services.asr_service import ASRService

class ModelLoadThread(QThread):
    model_loaded_signal = pyqtSignal(ASRService)
    
    def __init__(self):
        super().__init__()
        self._is_running = True
        
    def run(self):
        self._is_running = True
        while self._is_running:
            asr = ASRService()
            self.model_loaded_signal.emit(asr)
            break  # 只执行一次
        self._is_running = False
            
    def stop(self):
        self._is_running = False
        self.quit()
        self.wait(5000)  # 增加5秒超时等待