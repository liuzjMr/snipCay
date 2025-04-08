#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtCore import QObject, pyqtSignal
from ..utils.logger import setup_logger

class BatchTranscribeQueue(QObject):
    """批量转录队列管理器"""
    
    # 定义信号
    queue_progress_signal = pyqtSignal(int, int)  # 当前处理的索引, 总数量
    queue_completed_signal = pyqtSignal()  # 队列处理完成信号
    video_start_signal = pyqtSignal(str)  # 开始处理某个视频
    video_completed_signal = pyqtSignal(str)  # 某个视频处理完成
    
    def __init__(self):
        """初始化批量转录队列"""
        super().__init__()
        self.logger = setup_logger(__name__)
        self.video_queue = []  # 视频文件路径队列
        self.current_index = -1  # 当前处理的视频索引
        self.is_processing = False  # 是否正在处理队列
        self.results = {}  # 存储每个视频的转录结果 {file_path: {subtitles, words_timestamps}}
        
    def add_videos(self, video_paths):
        """添加多个视频到队列"""
        if not video_paths:
            return
            
        self.video_queue.extend(video_paths)
        self.logger.info(f"已添加 {len(video_paths)} 个视频到转录队列，当前队列长度: {len(self.video_queue)}")
        
    def clear_queue(self):
        """清空队列"""
        self.video_queue = []
        self.current_index = -1
        self.is_processing = False
        self.results = {}
        self.logger.info("转录队列已清空")
        
    def start_processing(self, asr_processor):
        """开始处理队列"""
        if not self.video_queue or self.is_processing:
            return False
            
        self.is_processing = True
        self.current_index = 0
        self.asr_processor = asr_processor
        self.logger.info(f"开始批量转录，队列中有 {len(self.video_queue)} 个视频")
        
        # 发送队列进度信号
        self.queue_progress_signal.emit(self.current_index, len(self.video_queue))
        
        # 开始处理第一个视频
        self._process_current_video()
        return True
        
    def _process_current_video(self):
        """处理当前视频"""
        if self.current_index >= len(self.video_queue):
            self._complete_queue()
            return
            
        current_video = self.video_queue[self.current_index]
        self.logger.info(f"开始处理队列中的第 {self.current_index + 1}/{len(self.video_queue)} 个视频: {current_video}")
        
        # 发送开始处理视频信号
        self.video_start_signal.emit(current_video)
        
        # 这里不直接处理，而是通知主窗口开始处理
        # 主窗口会调用 on_video_transcribed 方法来通知队列管理器继续处理下一个
        
    def on_video_transcribed(self, video_path, subtitles, words_timestamps):
        """视频转录完成回调"""
        if not self.is_processing:
            return
            
        # 存储结果
        self.results[video_path] = {
            'subtitles': subtitles,
            'words_timestamps': words_timestamps
        }
        
        # 发送视频处理完成信号
        self.video_completed_signal.emit(video_path)
        
        # 处理下一个视频
        self.current_index += 1
        self.queue_progress_signal.emit(self.current_index, len(self.video_queue))
        
        if self.current_index < len(self.video_queue):
            self._process_current_video()
        else:
            self._complete_queue()
    
    def _complete_queue(self):
        """完成队列处理"""
        self.is_processing = False
        self.logger.info(f"批量转录队列处理完成，共处理 {len(self.results)} 个视频")
        self.queue_completed_signal.emit()
        
    def get_current_video(self):
        """获取当前正在处理的视频路径"""
        if 0 <= self.current_index < len(self.video_queue):
            return self.video_queue[self.current_index]
        return None
        
    def get_results(self):
        """获取所有转录结果"""
        return self.results
        
    def get_result(self, video_path):
        """获取指定视频的转录结果"""
        return self.results.get(video_path, None)

    def get_video_paths(self):
        """获取队列中的所有视频路径"""
        return self.video_queue.copy()  # 返回副本以防止外部修改
    
    def remove_video(self, index):
        """从队列中移除指定索引的视频"""
        if 0 <= index < len(self.video_queue):
            video_path = self.video_queue[index]
            self.video_queue.pop(index)
            if video_path in self.results:
                del self.results[video_path]
            self.logger.info(f"已从队列中移除视频: {video_path}")
            return True
        return False