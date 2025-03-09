#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QScrollArea, QFrame, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient


class TimelineRuler(QWidget):
    """时间轴刻度尺组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.duration = 0
        self.tick_interval = 5000  # 刻度间隔，单位为毫秒
        self.minor_ticks = 5  # 每个主刻度之间的次刻度数量
        
        self.setFixedHeight(30)
        self.setMinimumWidth(1000)
        
    def set_duration(self, duration):
        """设置时间轴总时长"""
        self.duration = duration
        self.update_size()
        self.update()
        
    def update_size(self):
        """根据时长更新部件尺寸"""
        width = max(self.parentWidget().width(), self.ms_to_pixels(self.duration))
        self.setMinimumWidth(width)
        
    def ms_to_pixels(self, ms):
        """将毫秒转换为像素位置"""
        # 假设1秒 = 100像素
        return int(ms / 1000 * 100)
        
    def paintEvent(self, event):
        """绘制事件"""
        if self.duration == 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(event.rect(), QColor("#2d2d2d"))
        
        # 设置刻度画笔
        painter.setPen(QPen(QColor("#aaa")))
        
        # 绘制刻度和标签
        for t in range(0, self.duration + 1, self.tick_interval):
            x = self.ms_to_pixels(t)
            
            # 绘制主刻度线
            painter.drawLine(x, 15, x, 30)
            
            # 绘制时间标签
            time_str = self.format_time(t)
            painter.drawText(x - 20, 0, 40, 15, Qt.AlignmentFlag.AlignCenter, time_str)
            
            # 绘制次刻度线
            if t < self.duration:
                minor_interval = self.tick_interval / self.minor_ticks
                for i in range(1, self.minor_ticks):
                    minor_t = t + i * minor_interval
                    if minor_t > self.duration:
                        break
                    minor_x = self.ms_to_pixels(minor_t)
                    painter.drawLine(minor_x, 25, minor_x, 30)
        
    def format_time(self, ms):
        """格式化时间"""
        s = ms // 1000
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"


class TimelineWaveform(QWidget):
    """时间轴波形组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.duration = 0
        self.waveform_data = []  # 存储波形数据
        self.current_position = 0
        self.subtitles = []
        
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def set_duration(self, duration):
        """设置时间轴总时长"""
        self.duration = duration
        self.update_size()
        self.update()
        
    def update_size(self):
        """根据时长更新部件尺寸"""
        width = max(self.parentWidget().width(), self.ms_to_pixels(self.duration))
        self.setMinimumWidth(width)
        
    def ms_to_pixels(self, ms):
        """将毫秒转换为像素位置"""
        # 假设1秒 = 100像素
        return int(ms / 1000 * 100)
        
    def set_waveform_data(self, data):
        """设置波形数据"""
        self.waveform_data = data
        self.update()
        
    def set_subtitles(self, subtitles):
        """设置字幕数据"""
        self.subtitles = subtitles
        self.update()
        
    def set_position(self, position):
        """设置当前播放位置"""
        self.current_position = position
        self.update()
        
    def paintEvent(self, event):
        """绘制事件"""
        if self.duration == 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(event.rect(), QColor("#1a1a1a"))
        
        # 绘制字幕区域
        self.draw_subtitle_regions(painter)
        
        # 绘制波形
        self.draw_waveform(painter, event.rect())
        
        # 绘制当前位置线
        self.draw_position_line(painter)
        
    def draw_subtitle_regions(self, painter):
        """绘制字幕区域"""
        for subtitle in self.subtitles:
            start_x = self.ms_to_pixels(subtitle["start_time"])
            end_x = self.ms_to_pixels(subtitle["end_time"])
            width = max(end_x - start_x, 1)  # 确保宽度至少为1像素
            
            # 创建字幕区域渐变
            gradient = QLinearGradient(start_x, 0, end_x, 0)
            gradient.setColorAt(0, QColor(0, 120, 210, 150))
            gradient.setColorAt(1, QColor(0, 120, 210, 100))
            
            # 绘制字幕区域矩形
            painter.fillRect(start_x, 0, width, self.height(), gradient)
            
            # 绘制字幕区域边框
            painter.setPen(QPen(QColor(0, 150, 255, 200)))
            painter.drawRect(start_x, 0, width, self.height() - 1)
        
    def draw_waveform(self, painter, rect):
        """绘制波形"""
        if not self.waveform_data:
            # 绘制模拟波形
            self.draw_dummy_waveform(painter, rect)
            return
            
        # 实际波形的绘制代码将根据波形数据格式来实现
        
    def draw_dummy_waveform(self, painter, rect):
        """绘制模拟波形（当没有实际波形数据时）"""
        painter.setPen(QPen(QColor("#4CAF50"), 1))
        
        center_y = rect.height() / 2
        step = 5
        
        for i in range(0, rect.width(), step):
            # 计算振幅，创建一个简单的正弦波形
            t = i / 100.0
            amp = 20 * (1 + 0.5 * (1 + int(t * 2) % 2))
            y1 = int(center_y - amp)  # 转换为整数
            y2 = int(center_y + amp)  # 转换为整数
            
            painter.drawLine(i, y1, i, y2)
        
    def draw_position_line(self, painter):
        """绘制当前位置线"""
        if self.current_position > 0:
            x = self.ms_to_pixels(self.current_position)
            painter.setPen(QPen(QColor("#FF5722"), 2))
            painter.drawLine(x, 0, x, self.height())


class Timeline(QWidget):
    """时间轴组件"""
    
    def __init__(self):
        super().__init__()
        
        self.duration = 0
        self.media_path = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题标签
        title_label = QLabel("时间轴")
        title_label.setStyleSheet("background-color: #333; color: white; padding: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
                border: none;
            }
            QScrollBar:horizontal {
                background: #2a2a2a;
                height: 10px;
            }
            QScrollBar::handle:horizontal {
                background: #666;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # 创建容器部件
        timeline_container = QWidget()
        
        # 容器布局
        container_layout = QVBoxLayout(timeline_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 创建时间刻度尺
        self.ruler = TimelineRuler()
        container_layout.addWidget(self.ruler)
        
        # 创建波形视图
        self.waveform = TimelineWaveform()
        container_layout.addWidget(self.waveform)
        
        # 设置滚动区域内容
        self.scroll_area.setWidget(timeline_container)
        
        # 添加滚动区域到主布局
        main_layout.addWidget(self.scroll_area)
        
    def load_media(self, media_path):
        """加载媒体文件"""
        self.media_path = media_path
        
        # 在实际应用中，会从媒体文件中获取时长
        # 暂时使用模拟时长
        self.set_duration(2 * 60 * 1000)  # 2分钟，单位为毫秒
        
    def set_duration(self, duration):
        """设置时间轴总时长"""
        self.duration = duration
        self.ruler.set_duration(duration)
        self.waveform.set_duration(duration)
        
    def load_subtitles(self, subtitles):
        """加载字幕数据"""
        self.waveform.set_subtitles(subtitles)
        
    def update_subtitles(self, subtitles):
        """更新字幕数据"""
        self.waveform.set_subtitles(subtitles)
        
    def update_position(self, position):
        """更新当前播放位置"""
        self.waveform.set_position(position)
        
        # 自动滚动到当前位置
        if position > 0:
            pixel_pos = self.waveform.ms_to_pixels(position)
            viewport_width = self.scroll_area.viewport().width()
            scroll_value = max(0, pixel_pos - viewport_width // 2)
            self.scroll_area.horizontalScrollBar().setValue(scroll_value) 