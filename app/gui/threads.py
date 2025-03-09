from PyQt6.QtCore import QThread, pyqtSignal
import traceback
import time
import threading

class TranscribeThread(QThread):
    """处理视频转录的线程"""
    
    # 定义信号
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, media_path):
        """初始化转录线程"""
        super().__init__()
        self.media_path = media_path
        # 重要：延迟创建Transcriber实例到run方法中，避免在主线程中初始化
        self.transcriber = None
        self.stop_progress_update = False
        
    def run(self):
        """执行转录任务"""
        try:
            # 设置线程优先级 - 确保不会占用太多UI线程资源
            self.setPriority(QThread.Priority.LowPriority)
            
            # 在线程中导入模块和创建Transcriber实例
            # 这是关键，避免在主线程中加载模型
            from app.utils.transcriber import Transcriber
            self.transcriber = Transcriber()
            
            # 发送进度信号
            self.progress_signal.emit(10)
            
            # 启动进度更新线程
            progress_thread = threading.Thread(target=self.update_progress)
            progress_thread.daemon = True
            progress_thread.start()
            
            print(f"开始转录文件: {self.media_path}")
            
            # 执行转录 - 这是耗时操作，但现在它在单独的线程中运行
            subtitles = self.transcriber.transcribe(self.media_path)
            
            # 停止进度更新
            self.stop_progress_update = True
            
            # 发送结果信号
            self.progress_signal.emit(95)
            self.result_signal.emit(subtitles)
            self.progress_signal.emit(100)
            
        except Exception as e:
            # 停止进度更新
            self.stop_progress_update = True
            
            # 捕获并发送错误信号
            error_details = traceback.format_exc()
            self.error_signal.emit(f"转录失败: {str(e)}\n\n详细错误信息:\n{error_details}")
    
    def update_progress(self):
        """后台更新进度"""
        progress = 10
        while not self.stop_progress_update and progress < 90:
            time.sleep(1)  # 每1秒更新一次
            progress += 1
            if progress > 85:
                progress = 85  # 最高到85%
            self.progress_signal.emit(progress) 