#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTextEdit, QScrollArea, QFrame, QSizePolicy,
                            QToolBar, QSpacerItem)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QAction, QIcon


class SubtitleItem(QFrame):
    """单个字幕项组件"""
    clicked = pyqtSignal(int)  # 点击时发射时间点信号
    edited = pyqtSignal(int, str)  # 编辑时发射ID和内容信号
    deleted = pyqtSignal(int)  # 删除时发射ID信号
    
    def __init__(self, subtitle_id, start_time, end_time, text, parent=None):
        super().__init__(parent)
        
        self.subtitle_id = subtitle_id
        self.start_time = start_time
        self.end_time = end_time
        self.text = text
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            SubtitleItem {
                background-color: #2a2a2a;
                border-radius: 4px;
                margin: 2px;
            }
            SubtitleItem:hover {
                background-color: #353535;
            }
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        
        # 时间信息行
        time_layout = QHBoxLayout()
        
        # 时间标签
        time_text = f"{self.format_time(self.start_time)} → {self.format_time(self.end_time)}"
        self.time_label = QLabel(time_text)
        self.time_label.setStyleSheet("color: #aaa; font-size: 10px;")
        time_layout.addWidget(self.time_label)
        
        # 弹性空间
        time_layout.addStretch()
        
        # 删除按钮
        self.delete_button = QPushButton("×")
        self.delete_button.setFixedSize(16, 16)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.delete_button.clicked.connect(self.on_delete)
        time_layout.addWidget(self.delete_button)
        
        layout.addLayout(time_layout)
        
        # 文本编辑框
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.text)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #333;
                color: white;
                border: none;
                border-radius: 2px;
            }
        """)
        self.text_edit.setMaximumHeight(80)
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)
        
    def format_time(self, ms):
        """将毫秒格式化为时:分:秒.毫秒"""
        s, ms = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}.{ms//10:02d}"
        else:
            return f"{m:02d}:{s:02d}.{ms//10:02d}"
        
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.clicked.emit(self.start_time)
        super().mousePressEvent(event)
        
    def on_text_changed(self):
        """文本编辑事件"""
        new_text = self.text_edit.toPlainText()
        self.text = new_text
        self.edited.emit(self.subtitle_id, new_text)
        
    def on_delete(self):
        """删除事件"""
        self.deleted.emit(self.subtitle_id)
        
    def get_data(self):
        """获取字幕数据"""
        return {
            "id": self.subtitle_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text
        }


class SubtitleEditor(QWidget):
    # 自定义信号
    subtitle_clicked = pyqtSignal(int)  # 字幕点击信号
    text_edited = pyqtSignal(list)  # 文本编辑信号
    
    def __init__(self):
        super().__init__()
        
        self.subtitles = []
        self.subtitle_widgets = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 工具栏
        toolbar = QToolBar()
        toolbar.setStyleSheet("background-color: #333;")
        toolbar.setIconSize(QSize(20, 20))
        
        # 导出字幕按钮
        export_action = QAction("导出字幕", self)
        export_action.triggered.connect(self.export_subtitles)
        toolbar.addAction(export_action)
        
        # 导入字幕按钮
        import_action = QAction("导入字幕", self)
        import_action.triggered.connect(self.import_subtitles)
        toolbar.addAction(import_action)
        
        # 添加工具栏到布局
        main_layout.addWidget(toolbar)
        
        # 标题标签
        title_label = QLabel("字幕编辑")
        title_label.setStyleSheet("background-color: #333; color: white; padding: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2d2d2d;
                border: none;
            }
            QScrollBar:vertical {
                background: #2a2a2a;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #666;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 创建容器部件
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #2d2d2d;")
        
        # 容器布局
        self.subtitles_layout = QVBoxLayout(self.container)
        self.subtitles_layout.setContentsMargins(10, 10, 10, 10)
        self.subtitles_layout.setSpacing(10)
        self.subtitles_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 设置滚动区域内容
        scroll_area.setWidget(self.container)
        
        # 添加滚动区域到主布局
        main_layout.addWidget(scroll_area)
        
    def load_subtitles(self, subtitles):
        """加载字幕数据"""
        self.subtitles = subtitles
        self.update_subtitle_widgets()
        
    def update_subtitle_widgets(self):
        """更新字幕小部件"""
        # 清除现有小部件
        self.clear_subtitles()
        
        # 创建新的字幕小部件
        for subtitle in self.subtitles:
            self.add_subtitle_widget(subtitle)
            
        # 添加弹性空间
        self.subtitles_layout.addStretch()
        
    def add_subtitle_widget(self, subtitle):
        """添加单个字幕小部件"""
        widget = SubtitleItem(
            subtitle["id"],
            subtitle["start_time"],
            subtitle["end_time"],
            subtitle["text"]
        )
        
        # 连接信号
        widget.clicked.connect(self.subtitle_clicked)
        widget.edited.connect(self.on_subtitle_edited)
        widget.deleted.connect(self.on_subtitle_deleted)
        
        # 存储并添加到布局
        self.subtitle_widgets[subtitle["id"]] = widget
        self.subtitles_layout.addWidget(widget)
        
    def clear_subtitles(self):
        """清除所有字幕小部件"""
        # 移除所有小部件
        for i in reversed(range(self.subtitles_layout.count())):
            item = self.subtitles_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self.subtitles_layout.removeItem(item)
                
        self.subtitle_widgets = {}
        
    def on_subtitle_edited(self, subtitle_id, text):
        """处理字幕编辑事件"""
        # 更新字幕文本
        for subtitle in self.subtitles:
            if subtitle["id"] == subtitle_id:
                subtitle["text"] = text
                break
                
        # 发射编辑信号
        self.text_edited.emit(self.subtitles)
        
    def on_subtitle_deleted(self, subtitle_id):
        """处理字幕删除事件"""
        # 从UI中移除
        if subtitle_id in self.subtitle_widgets:
            self.subtitle_widgets[subtitle_id].deleteLater()
            del self.subtitle_widgets[subtitle_id]
            
        # 从数据中移除
        self.subtitles = [s for s in self.subtitles if s["id"] != subtitle_id]
        
        # 发射编辑信号
        self.text_edited.emit(self.subtitles)
        
    def get_subtitles(self):
        """获取字幕数据"""
        return self.subtitles
        
    def export_subtitles(self):
        """导出字幕"""
        # 在实际应用中实现字幕导出功能
        print("Export subtitles")
        
    def import_subtitles(self):
        """导入字幕"""
        # 在实际应用中实现字幕导入功能
        print("Import subtitles") 