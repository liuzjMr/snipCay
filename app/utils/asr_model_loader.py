from PyQt6.QtCore import QThread, pyqtSignal
from app.components.asr import ASRProcessor

class ASRModelLoaderThread(QThread):
    """ASR模型加载线程"""
    
    # 定义信号
    progress_signal = pyqtSignal(int, str)  # 进度信号
    model_ready_signal = pyqtSignal(object)  # 模型就绪信号
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self):
        """初始化模型加载线程"""
        super().__init__()
    
    def run(self):
        """执行模型加载"""
        try:
            # 发送进度信号
            self.progress_signal.emit(10, "初始化ASR处理器...")
            
            # 创建ASR处理器
            asr_processor = ASRProcessor()
            
            # 发送进度信号
            self.progress_signal.emit(100, "ASR模型加载完成")
            
            # 发送模型就绪信号
            self.model_ready_signal.emit(asr_processor)
            
        except Exception as e:
            # 发送错误信号
            import traceback
            error_details = traceback.format_exc()
            self.error_signal.emit(f"加载ASR模型失败: {str(e)}\n\n{error_details}") 