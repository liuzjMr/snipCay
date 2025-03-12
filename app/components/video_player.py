#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QSlider, QLabel, QStyle, QSizePolicy, QFrame)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTime, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class VideoPlayer(QWidget):
    # 自定义信号
    position_changed = pyqtSignal(int)  # 播放位置变化信号
    
    def __init__(self):
        """初始化视频播放器"""
        super().__init__()
        
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        self.media_path = None
        self.duration = 0
        
        # 创建定时器以定期更新位置
        self.position_timer = QTimer()
        self.position_timer.setInterval(100)  # 每100毫秒检查一次
        self.position_timer.timeout.connect(self.emit_position)
        
        # 当视频播放时启动定时器
        self.media_player.playingChanged.connect(self.handle_playing_changed)
        
        # 设置界面
        self.setup_ui()
        
        # 设置信号连接
        self.setup_connections()
        
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 视频控件
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 设置视频控件背景
        self.video_widget.setStyleSheet("background-color: #222;")
        
        # 连接媒体播放器和视频控件
        self.media_player.setVideoOutput(self.video_widget)
        
        # 添加视频控件到布局
        layout.addWidget(self.video_widget)
        
        # 创建控制面板
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 5, 10, 5)
        
        # 播放/暂停按钮
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setFixedSize(32, 32)
        controls_layout.addWidget(self.play_button)
        
        # 停止按钮
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setFixedSize(32, 32)
        controls_layout.addWidget(self.stop_button)
        
        # 当前时间标签
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("color: white;")
        self.time_label.setFixedWidth(70)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        controls_layout.addWidget(self.time_label)
        
        # 进度条
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        controls_layout.addWidget(self.position_slider)
        
        # 总时长标签
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setStyleSheet("color: white;")
        self.duration_label.setFixedWidth(70)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        controls_layout.addWidget(self.duration_label)
        
        # 音量按钮
        self.volume_button = QPushButton()
        self.volume_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.volume_button.setFixedSize(32, 32)
        controls_layout.addWidget(self.volume_button)
        
        # 音量滑块
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        controls_layout.addWidget(self.volume_slider)
        
        # 创建控制面板容器
        controls_frame = QFrame()
        controls_frame.setStyleSheet("background-color: #333;")
        controls_frame.setLayout(controls_layout)
        
        # 添加控制面板到主布局
        layout.addWidget(controls_frame)
        
    def setup_connections(self):
        """设置视频播放器信号连接"""
        # 连接播放器状态变化信号
        self.media_player.playbackStateChanged.connect(self.update_play_button)
        
        # 连接播放器位置变化信号
        self.media_player.positionChanged.connect(self.update_position)
        
        # 连接播放器持续时间变化信号
        self.media_player.durationChanged.connect(self.update_duration)
        
        # 连接视频输出相关信号
        if hasattr(self, 'video_output'):
            # 尝试连接视频输出的信号
            pass
        
        # 连接按钮动作
        self.play_button.clicked.connect(self.toggle_play)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.volume_slider.sliderMoved.connect(self.set_volume)
        self.volume_button.clicked.connect(self.toggle_mute)
        
    def load_media(self, file_path):
        """加载媒体文件"""
        self.media_path = file_path
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.stop()
        
    def get_media_path(self):
        """获取当前媒体路径"""
        return self.media_path
    
    def has_media(self):
        """检查是否有加载媒体"""
        return self.media_path is not None
        
    def toggle_play(self):
        """切换播放/暂停状态"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
            
    def play(self):
        """播放视频"""
        if hasattr(self, 'media_player'):
            self.media_player.play()
        
    def pause(self):
        """暂停播放"""
        if hasattr(self, 'media_player'):
            self.media_player.pause()
        
    def stop(self):
        """停止播放"""
        if hasattr(self, 'media_player'):
            self.media_player.stop()
        
    def set_position(self, position):
        """设置播放位置"""
        self.media_player.setPosition(position)
        
    def seek(self, position_ms):
        """
        跳转到指定时间点
        
        Args:
            position_ms (int): 目标时间点（毫秒）
        """
        if hasattr(self, 'media_player'):
            # 转换毫秒到视频播放器使用的格式
            position = position_ms
            self.media_player.setPosition(position)
        
    def get_position(self):
        """获取当前播放位置（毫秒）"""
        if hasattr(self, 'media_player'):
            position = self.media_player.position()
            self.position_changed.emit(position)
            return position
        return 0
        
    def set_volume(self, volume):
        """设置音量"""
        self.audio_output.setVolume(volume / 100.0)
        
    def toggle_mute(self):
        """切换静音状态"""
        self.audio_output.setMuted(not self.audio_output.isMuted())
        
        # 更新图标
        if self.audio_output.isMuted():
            self.volume_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
        else:
            self.volume_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        
    def update_duration(self, duration):
        """更新媒体总时长"""
        self.duration = duration
        self.position_slider.setRange(0, duration)
        
        # 格式化时间
        time = QTime(0, 0, 0).addMSecs(duration)
        format_string = "hh:mm:ss" if duration > 3600000 else "mm:ss"
        self.duration_label.setText(time.toString(format_string))
        
    def update_position(self, position):
        """更新播放位置"""
        # 更新滑块位置（不触发sliderMoved信号）
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(position)
        self.position_slider.blockSignals(False)
        
        # 更新时间标签
        current_info = self.format_time(position)
        duration_info = self.format_time(self.media_player.duration())
        self.time_label.setText(f"{current_info} / {duration_info}")
        
        # 发出位置变化信号
        self.position_changed.emit(position)
        
    def update_play_button(self, state):
        """根据播放状态更新播放按钮图标"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        
    def is_playing(self):
        """检查是否正在播放"""
        if hasattr(self, 'media_player'):
            return self.media_player.isPlaying()
        return False

    def format_time(self, milliseconds):
        """格式化时间（毫秒转为时:分:秒.毫秒）"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        hours = minutes // 60
        milliseconds %= 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def handle_playing_changed(self, playing):
        """处理播放状态变化"""
        if playing:
            self.position_timer.start()
        else:
            self.position_timer.stop()
    
    def emit_position(self):
        """发送当前位置信号"""
        if self.media_player.isPlaying():
            position = self.get_position()
            self.position_changed.emit(position)

    def get_duration(self):
        """获取视频总时长（毫秒）"""
        if hasattr(self, 'media_player'):
            return self.media_player.duration()
        return 0