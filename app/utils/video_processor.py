#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import tempfile
import subprocess
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from app.utils.logger import setup_logger

class VideoProcessor(QObject):
    """视频处理器类，用于处理视频剪辑和合并操作"""
    
    # 定义信号
    progress_updated = pyqtSignal(int, str)
    process_completed = pyqtSignal(str)
    process_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)
        self.temp_dir = None
        self.segment_files = []
    
    def _create_temp_dir(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp(prefix="snipCay_")
        self.logger.info(f"创建临时目录: {self.temp_dir}")
        return self.temp_dir
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            for file in self.segment_files:
                if os.path.exists(file):
                    try:
                        os.remove(file)
                        self.logger.debug(f"删除临时文件: {file}")
                    except Exception as e:
                        self.logger.error(f"删除临时文件失败: {file}, 错误: {str(e)}")
            
            try:
                os.rmdir(self.temp_dir)
                self.logger.info(f"删除临时目录: {self.temp_dir}")
                self.temp_dir = None
                self.segment_files = []
            except Exception as e:
                self.logger.error(f"删除临时目录失败: {self.temp_dir}, 错误: {str(e)}")
    
    def _check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                self.logger.info("FFmpeg可用")
                return True
            else:
                self.logger.error(f"FFmpeg检查失败: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"FFmpeg检查异常: {str(e)}")
            return False
    
    def process_video(self, video_path, segments, output_path):
        """处理视频，根据时间段剪辑并合并
        
        Args:
            video_path: 原始视频路径
            segments: 需要删除的时间段列表，格式为[(start_time, end_time), ...]
            output_path: 输出视频路径
        """
        if not self._check_ffmpeg():
            self.process_error.emit("FFmpeg不可用，请确保已安装FFmpeg并添加到系统路径")
            return
        
        if not os.path.exists(video_path):
            self.process_error.emit(f"视频文件不存在: {video_path}")
            return
        
        # 创建临时目录
        self._create_temp_dir()
        
        try:
            # 获取视频总时长
            duration = self._get_video_duration(video_path)
            if duration <= 0:
                self.process_error.emit("无法获取视频时长")
                return
            
            # 计算需要保留的片段
            keep_segments = self._calculate_keep_segments(segments, duration)
            if not keep_segments:
                self.process_error.emit("没有可保留的视频片段")
                return
            
            # 切割视频片段
            self.segment_files = self._cut_video_segments(video_path, keep_segments)
            if not self.segment_files:
                self.process_error.emit("视频切割失败")
                return
            
            # 合并视频片段
            success = self._merge_video_segments(self.segment_files, output_path)
            if not success:
                self.process_error.emit("视频合并失败")
                return
            
            self.process_completed.emit(output_path)
        except Exception as e:
            self.logger.error(f"视频处理异常: {str(e)}")
            self.process_error.emit(f"视频处理异常: {str(e)}")
        finally:
            # 清理临时文件
            self._cleanup_temp_files()
    
    def _get_video_duration(self, video_path):
        """获取视频时长（毫秒）"""
        try:
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "json", 
                video_path
            ]
            
            result = subprocess.run(cmd, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration_sec = float(data['format']['duration'])
                duration_ms = int(duration_sec * 1000)
                self.logger.info(f"视频时长: {duration_ms}ms")
                return duration_ms
            else:
                self.logger.error(f"获取视频时长失败: {result.stderr}")
                return 0
        except Exception as e:
            self.logger.error(f"获取视频时长异常: {str(e)}")
            return 0
    
    def _calculate_keep_segments(self, delete_segments, duration):
        """计算需要保留的视频片段
        
        Args:
            delete_segments: 需要删除的时间段列表，格式为[(start_time, end_time), ...]
            duration: 视频总时长（毫秒）
            
        Returns:
            保留的时间段列表，格式为[(start_time, end_time), ...]
        """
        # 按开始时间排序删除片段
        sorted_segments = sorted(delete_segments, key=lambda x: x[0])
        
        # 计算保留片段
        keep_segments = []
        last_end = 0
        
        for start, end in sorted_segments:
            # 如果删除片段前有内容，则保留
            if start > last_end:
                keep_segments.append((last_end, start))
            last_end = max(last_end, end)
        
        # 添加最后一个片段
        if last_end < duration:
            keep_segments.append((last_end, duration))
        
        self.logger.info(f"计算得到 {len(keep_segments)} 个保留片段")
        return keep_segments
    
    def _cut_video_segments(self, video_path, segments):
        """切割视频片段
        
        Args:
            video_path: 原始视频路径
            segments: 需要保留的时间段列表，格式为[(start_time, end_time), ...]
            
        Returns:
            切割后的视频片段文件路径列表
        """
        segment_files = []
        total_segments = len(segments)
        
        for i, (start, end) in enumerate(segments):
            # 计算时长（秒）
            start_sec = start / 1000.0
            duration_sec = (end - start) / 1000.0
            
            # 输出文件路径
            output_file = os.path.join(self.temp_dir, f"segment_{i:03d}.mp4")
            segment_files.append(output_file)
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-y",  # 覆盖输出文件
                "-ss", f"{start_sec:.3f}",  # 开始时间
                "-i", video_path,  # 输入文件
                "-t", f"{duration_sec:.3f}",  # 持续时间
                "-c", "copy",  # 复制编解码器（不重新编码）
                output_file  # 输出文件
            ]
            
            # 更新进度
            progress_percent = int((i / total_segments) * 50)  # 切割占总进度的50%
            self.progress_updated.emit(progress_percent, f"正在切割视频片段 {i+1}/{total_segments}")
            
            # 执行命令
            try:
                self.logger.info(f"切割视频片段 {i+1}/{total_segments}: {start_sec:.3f}s - {start_sec+duration_sec:.3f}s")
                result = subprocess.run(cmd, 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE,
                                       text=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    self.logger.error(f"切割视频片段失败: {result.stderr}")
                    return []
            except Exception as e:
                self.logger.error(f"切割视频片段异常: {str(e)}")
                return []
        
        return segment_files
    
    def _merge_video_segments(self, segment_files, output_path):
        """合并视频片段
        
        Args:
            segment_files: 视频片段文件路径列表
            output_path: 输出视频路径
            
        Returns:
            是否成功
        """
        if not segment_files:
            return False
        
        # 创建合并列表文件
        list_file = os.path.join(self.temp_dir, "segments.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for file in segment_files:
                f.write(f"file '{file.replace('\\', '/')}\n")
        
        # 构建FFmpeg命令
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-f", "concat",  # 使用concat协议
            "-safe", "0",  # 允许绝对路径
            "-i", list_file,  # 输入文件列表
            "-c", "copy",  # 复制编解码器（不重新编码）
            output_path  # 输出文件
        ]
        
        # 更新进度
        self.progress_updated.emit(75, "正在合并视频片段")
        
        # 执行命令
        try:
            self.logger.info(f"合并 {len(segment_files)} 个视频片段到: {output_path}")
            result = subprocess.run(cmd, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                self.logger.info("视频合并成功")
                self.progress_updated.emit(100, "视频处理完成")
                return True
            else:
                self.logger.error(f"视频合并失败: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"视频合并异常: {str(e)}")
            return False