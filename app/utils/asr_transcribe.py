from PyQt6.QtCore import QThread, pyqtSignal

class ASRTranscribeThread(QThread):
    """ASR转录线程"""
    
    # 定义信号
    progress_signal = pyqtSignal(int, str)  # 进度信号
    result_signal = pyqtSignal(list)  # 结果信号
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self, asr_processor, media_path):
        """初始化转录线程"""
        super().__init__()
        self.asr_processor = asr_processor
        self.media_path = media_path
    
    def run(self):
        """执行转录任务"""
        try:
            # 发送进度信号
            self.progress_signal.emit(10, "准备转录...")
            
            # 执行转录 - 获取格式化的字幕列表
            print("开始转录...")
            
            # 执行转录任务 - ASRProcessor 现在直接返回字幕列表
            subtitles = self.asr_processor.transcribe(self.media_path)
            
            # 发送进度信号
            self.progress_signal.emit(90, "转录完成，准备渲染...")
            
            # 调试信息
            print(f"转录完成，得到 {len(subtitles)} 条字幕")
            if subtitles and len(subtitles) > 0:
                print(f"第一条字幕: {subtitles[0]}")
            
            # 发送字幕结果信号
            self.result_signal.emit(subtitles)
            
            # 最终进度
            self.progress_signal.emit(100, "转录完成")
            
        except Exception as e:
            # 发送错误信号
            import traceback
            error_details = traceback.format_exc()
            self.error_signal.emit(f"转录失败: {str(e)}\n\n{error_details}") 