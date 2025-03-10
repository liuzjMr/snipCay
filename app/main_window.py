#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QListWidget, QLabel, QFileDialog, 
                            QSplitter, QSlider, QTabWidget, QTextEdit, QCheckBox,
                            QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from app.components.video_player import VideoPlayer
from app.utils.asr_transcribe import ASRTranscribeThread
from app.components.asr import ASRProcessor
import os

class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.media_path = None
        self.subtitles = None
        self.current_highlighted_index = -1
        self.subtitle_segments = []  # 存储每个字幕段的开始位置和结束位置
        self.cut_segments = []  # 存储要删除的片段
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局和组件"""
        # 创建主布局
        main_layout = QHBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(main_layout)
        self.setCentralWidget(self.central_widget)
        
        # 左侧面板 - 视频播放区域
        left_panel = QWidget()
        self.left_layout = QVBoxLayout(left_panel)
        self.left_layout.setContentsMargins(10, 10, 10, 10)
        self.left_layout.setSpacing(10)
        
        # 视频播放器
        self.video_player = VideoPlayer()
        self.video_player.setMinimumSize(640, 360)  # 确保视频播放器有足够大的尺寸
        self.left_layout.addWidget(self.video_player)
        
        # 添加播放控制面板
        self.setup_playback_controls()
        
        # 右侧面板 - 字幕和控制按钮
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.import_button = QPushButton("导入视频")
        self.import_button.clicked.connect(self.import_video)
        self.import_button.setMinimumHeight(40)
        
        self.transcribe_button = QPushButton("转录字幕")
        self.transcribe_button.clicked.connect(self.transcribe_video)
        self.transcribe_button.setMinimumHeight(40)
        
        # 添加文本剪辑按钮
        self.text_edit_button = QPushButton("按文本剪辑")
        self.text_edit_button.clicked.connect(self.show_text_editor)
        self.text_edit_button.setMinimumHeight(40)
        
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.transcribe_button)
        button_layout.addWidget(self.text_edit_button)
        right_layout.addLayout(button_layout)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #1976d2;
                border-radius: 6px;
                background-color: #1e2430;
            }
            QTabBar::tab {
                background-color: #1a1f2a;
                color: #e0e0e0;
                border: 2px solid #1976d2;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 12px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e2430;
                border-bottom: 2px solid #1e2430;
            }
            QTabBar::tab:hover:!selected {
                background-color: #283447;
            }
        """)
        
        # 字幕列表标签页
        self.subtitle_tab = QWidget()
        subtitle_tab_layout = QVBoxLayout(self.subtitle_tab)
        
        subtitle_label = QLabel("字幕列表")
        subtitle_tab_layout.addWidget(subtitle_label)
        
        self.subtitle_list = QListWidget()
        self.subtitle_list.setMinimumWidth(350)
        self.subtitle_list.setAlternatingRowColors(True)
        self.subtitle_list.itemClicked.connect(self.on_subtitle_clicked)
        subtitle_tab_layout.addWidget(self.subtitle_list, 1)  # 1是伸展因子
        
        # 文本剪辑标签页
        self.text_edit_tab = QWidget()
        self.text_edit_tab_layout = QVBoxLayout(self.text_edit_tab)
        
        text_edit_label = QLabel("文本剪辑 (选中并标记不需要的部分)")
        self.text_edit_tab_layout.addWidget(text_edit_label)
        
        # 这里先不添加内容，在show_text_editor方法中动态创建
        
        # 添加标签页到标签页控件
        self.tab_widget.addTab(self.subtitle_tab, "字幕列表")
        self.tab_widget.addTab(self.text_edit_tab, "文本剪辑")
        
        # 添加标签页控件到右侧面板
        right_layout.addWidget(self.tab_widget, 1)  # 1是伸展因子
        
        # 将左右面板添加到主布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("准备就绪")
        
        # 设置窗口属性
        self.setWindowTitle("视频字幕转录工具")
        self.resize(1200, 700)
        
        # 应用简单样式
        self.apply_simple_style()
        
        # 连接视频播放器信号
        self.connect_video_signals()
        
        # 确保字幕更新定时器启动
        self._ensure_subtitle_update_timer()
        
    def setup_playback_controls(self):
        """创建播放控制面板"""
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        # 播放/暂停按钮
        self.play_button = QPushButton("▶")
        self.play_button.setToolTip("播放/暂停")
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setFixedSize(50, 50)
        
        # 停止按钮
        self.stop_button = QPushButton("■")
        self.stop_button.setToolTip("停止")
        self.stop_button.clicked.connect(self.stop_playback)
        self.stop_button.setFixedSize(50, 50)
        
        # 进度滑块
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.seek_video)
        
        # 添加到布局
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.progress_slider)
        
        self.left_layout.addWidget(control_panel)

    def apply_simple_style(self):
        """应用简单样式，避免语法错误"""
        # 主窗口样式
        self.setStyleSheet("QMainWindow { background-color: #121820; color: #e1e1e1; }")
        
        # 按钮样式
        if hasattr(self, 'import_button') and hasattr(self, 'transcribe_button') and hasattr(self, 'text_edit_button'):
            button_style = "QPushButton { background-color: #1a1f2a; color: #4fc3f7; border: 2px solid #2196f3; border-radius: 5px; padding: 8px; font-weight: bold; }"
            self.import_button.setStyleSheet(button_style)
            self.import_button.setText("📂 导入视频")
            self.transcribe_button.setStyleSheet(button_style)
            self.transcribe_button.setText("🎤 转录字幕")
            self.text_edit_button.setStyleSheet(button_style)
            self.text_edit_button.setText("✂️ 文本剪辑")
        
        # 字幕列表样式
        if hasattr(self, 'subtitle_list'):
            subtitle_style = "QListWidget { background-color: #1a1f2a; color: #e0e0e0; border: 2px solid #2196f3; border-radius: 5px; }"
            self.subtitle_list.setStyleSheet(subtitle_style)
        
        # 播放控制样式
        if hasattr(self, 'play_button') and hasattr(self, 'stop_button'):
            control_style = "QPushButton { background-color: #1a1f2a; color: #e1e1e1; border: 2px solid #2196f3; border-radius: 20px; font-weight: bold; }"
            self.play_button.setStyleSheet(control_style)
            self.stop_button.setStyleSheet(control_style)

    def toggle_playback(self):
        """切换播放/暂停状态"""
        if hasattr(self, 'video_player'):
            if self.video_player.is_playing():
                self.video_player.pause()
                self.play_button.setText("▶")
            else:
                self.video_player.play()
                self.play_button.setText("⏸")

    def stop_playback(self):
        """停止播放"""
        if hasattr(self, 'video_player'):
            self.video_player.stop()
            self.play_button.setText("▶")

    def seek_video(self, position):
        """跳转到视频指定位置"""
        if hasattr(self, 'video_player'):
            duration = self.video_player.get_duration()
            if duration > 0:
                seek_position = int(position * duration / 100)
                self.video_player.seek(seek_position)

    def connect_video_signals(self):
        """连接视频播放器的信号"""
        if hasattr(self, 'video_player'):
            try:
                # 更新定时器
                if not hasattr(self, 'update_timer'):
                    self.update_timer = QTimer()
                    self.update_timer.setInterval(100)  # 100ms更新一次
                    self.update_timer.timeout.connect(self.update_playback_controls)
                    self.update_timer.timeout.connect(self._force_update_subtitle)
                    self.update_timer.start()
                    print("已启动播放控制更新定时器 (100ms)")
                    
            except Exception as e:
                print(f"连接视频播放器信号失败: {str(e)}")

    def update_playback_controls(self):
        """更新播放控制状态"""
        if hasattr(self, 'video_player') and hasattr(self, 'progress_slider'):
            # 更新进度滑块
            duration = self.video_player.get_duration()
            if duration > 0:
                position = self.video_player.get_position()
                progress = int(position * 100 / duration)
                
                # 阻断信号以避免循环
                self.progress_slider.blockSignals(True)
                self.progress_slider.setValue(progress)
                self.progress_slider.blockSignals(False)
            
            # 更新播放/暂停按钮状态
            if hasattr(self, 'play_button'):
                if self.video_player.is_playing():
                    self.play_button.setText("⏸")
                else:
                    self.play_button.setText("▶")

    def _force_update_subtitle(self):
        """强制更新当前字幕高亮显示"""
        try:
            if not hasattr(self, 'video_player') or not self.video_player:
                return
            
            if not hasattr(self, 'subtitle_list') or not self.subtitle_list:
                return
                
            if not hasattr(self, 'subtitles') or not self.subtitles:
                return
                
            # 获取当前播放位置
            current_position = self.video_player.get_position()
            
            # 查找匹配的字幕
            matching_index = -1
            for i, subtitle in enumerate(self.subtitles):
                start_time = subtitle.get('start_time', 0)
                end_time = subtitle.get('end_time', 0)
                
                if start_time <= current_position <= end_time:
                    matching_index = i
                    break
                    
            # 如果找到匹配的字幕，且不是当前高亮的字幕，则更新高亮
            if matching_index >= 0 and matching_index != getattr(self, 'current_highlighted_index', -1):
                print(f"找到匹配字幕索引: {matching_index}, 文本: {self.subtitles[matching_index].get('text', '')}")
                
                # 使用 setCurrentRow 而不是 setItemSelected
                if matching_index < self.subtitle_list.count():
                    self.subtitle_list.setCurrentRow(matching_index)
                    # 滚动到当前项
                    self.subtitle_list.scrollToItem(self.subtitle_list.item(matching_index))
                    
                    # 更新当前高亮索引
                    self.current_highlighted_index = matching_index
                    
        except Exception as e:
            print(f"更新字幕高亮出错: {str(e)}")

    def import_video(self):
        """导入视频文件"""
        try:
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv)"
            )
            
            if file_path:
                print(f"尝试导入视频: {file_path}")
                self.media_path = file_path
                self.video_player.load_media(file_path)
                self.statusBar().showMessage(f"已加载视频: {file_path}")
                print(f"成功导入视频: {file_path}")
                
                # 清空字幕
                self.subtitles = None
                self.update_subtitle_list()
        except Exception as e:
            print(f"导入视频失败: {str(e)}")
            self.statusBar().showMessage(f"导入视频失败: {str(e)}")

    def transcribe_video(self):
        """转录视频字幕"""
        if not self.media_path:
            self.statusBar().showMessage("请先导入视频文件")
            return
            
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
            from PyQt6.QtCore import Qt
            
            # 创建简单的进度对话框
            self.progress_dialog = QDialog(self)
            self.progress_dialog.setWindowTitle("转录中")
            self.progress_dialog.setMinimumWidth(300)
            self.progress_dialog.setMinimumHeight(150)
            self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.progress_dialog.setStyleSheet("QDialog { background-color: #121820; }")
            
            # 设置布局
            layout = QVBoxLayout(self.progress_dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 添加标签
            label = QLabel("正在准备转录...", self.progress_dialog)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 14px; color: #e1e1e1; margin-bottom: 20px;")
            layout.addWidget(label)
            self.progress_label = label
            
            # 添加无限循环的进度条
            progress_bar = QProgressBar(self.progress_dialog)
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(0)  # 无限循环模式
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #2196f3;
                    border-radius: 5px;
                    background-color: #1a1f2a;
                    height: 25px;
                    text-align: center;
                }
                
                QProgressBar::chunk {
                    background-color: #2196f3;
                    width: 10px;
                }
            """)
            layout.addWidget(progress_bar)
            
            # 立即显示对话框
            self.progress_dialog.setAutoFillBackground(True)
            self.progress_dialog.show()
            
            # 使用QTimer延迟初始化ASR处理器和启动转录，让界面先响应
            QTimer.singleShot(100, self.start_transcription_thread)
            
        except Exception as e:
            error_msg = f"创建转录对话框失败: {str(e)}"
            self.statusBar().showMessage(error_msg)
            print(error_msg)
            import traceback
            print(traceback.format_exc())

    def start_transcription_thread(self):
        """启动转录线程（在对话框显示后调用）"""
        try:
            # 更新标签
            if hasattr(self, 'progress_label'):
                self.progress_label.setText("正在转录视频，请稍候...")
            
            # 创建ASR处理器
            asr_processor = ASRProcessor()
            
            # 创建并启动转录线程
            self.asr_thread = ASRTranscribeThread(asr_processor, self.media_path)
            self.asr_thread.progress_signal.connect(self.update_transcribe_progress)
            self.asr_thread.result_signal.connect(self.handle_transcribe_result)
            self.asr_thread.start()
            
        except Exception as e:
            # 关闭进度对话框
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                
            error_msg = f"启动转录线程失败: {str(e)}"
            self.statusBar().showMessage(error_msg)
            print(error_msg)
            
            # 显示错误消息
            QMessageBox.critical(self, "转录错误", f"无法启动转录过程: {str(e)}", 
                                QMessageBox.StandardButton.Ok)
            
            import traceback
            print(traceback.format_exc())

    def update_transcribe_progress(self, progress_text):
        """更新转录进度
        
        Args:
            progress_text: 进度文本或进度值
        """
        try:
            # 只更新状态栏，不更新进度对话框
            message = str(progress_text) if not isinstance(progress_text, int) else f"转录中... {progress_text}%"
            self.statusBar().showMessage(message)
        except Exception as e:
            print(f"更新进度出错: {str(e)}")

    def handle_transcribe_result(self, subtitles):
        """处理转录结果"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
            
            # 确保结果是有效的
            if subtitles:
                print(f"收到转录结果: {len(subtitles)} 条字幕")
                
                # 显示转录成功的提示
                QMessageBox.information(self, "转录完成", f"转录已完成，共生成 {len(subtitles)} 条字幕。", 
                                        QMessageBox.StandardButton.Ok)
                
                self.subtitles = subtitles
                self.update_subtitle_list()
                self.statusBar().showMessage(f"转录完成，共 {len(subtitles)} 条字幕")
            else:
                print("未接收到有效的转录结果")
                self.statusBar().showMessage("转录失败，未生成字幕")
                
                # 显示转录失败的提示
                QMessageBox.warning(self, "转录失败", "转录过程未生成有效字幕，请检查视频文件。", 
                                    QMessageBox.StandardButton.Ok)
        except Exception as e:
            error_msg = f"处理转录结果出错: {str(e)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            self.statusBar().showMessage("转录出错，请检查控制台输出")
            
            # 显示错误提示
            QMessageBox.critical(self, "转录错误", f"处理转录结果时出错: {str(e)}", 
                                QMessageBox.StandardButton.Ok)

    def update_subtitle_list(self):
        """更新字幕列表"""
        try:
            if not hasattr(self, 'subtitle_list'):
                return
                
            # 清空列表
            self.subtitle_list.clear()
            
            # 如果没有字幕，则退出
            if not self.subtitles:
                return
                
            # 添加字幕项
            for subtitle in self.subtitles:
                text = subtitle.get('text', '')
                start_time = subtitle.get('start_time', 0)
                end_time = subtitle.get('end_time', 0)
                
                # 格式化时间
                start_str = self.format_time(start_time)
                end_str = self.format_time(end_time)
                
                # 设置显示文本
                display_text = f"{text} ({start_str}-{end_str})"
                
                # 添加到列表
                self.subtitle_list.addItem(display_text)
                
            print(f"字幕列表更新完成，显示 {len(self.subtitles)} 条")
            print("字幕列表已更新")
            
        except Exception as e:
            print(f"更新字幕列表出错: {str(e)}")

    def on_subtitle_clicked(self, item):
        """处理字幕项点击事件"""
        try:
            index = self.subtitle_list.row(item)
            if index >= 0 and index < len(self.subtitles):
                start_time = self.subtitles[index].get('start_time', 0)
                if hasattr(self, 'video_player'):
                    self.video_player.seek(start_time)
                    self.video_player.play()
                    print(f"跳转到字幕时间点: {start_time}ms")
        except Exception as e:
            print(f"字幕点击处理出错: {str(e)}")

    def format_time(self, milliseconds):
        """格式化时间（毫秒转为时:分:秒）"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        seconds %= 60
        minutes %= 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def _ensure_subtitle_update_timer(self):
        """确保字幕更新定时器启动"""
        try:
            if not hasattr(self, 'subtitle_timer'):
                self.subtitle_timer = QTimer()
                self.subtitle_timer.setInterval(100)  # 100ms更新一次
                self.subtitle_timer.timeout.connect(self._force_update_subtitle)
                self.subtitle_timer.start()
                print("已启动字幕更新定时器 (100ms)")
            
            if not self.subtitle_timer.isActive():
                self.subtitle_timer.start()
                print("字幕更新定时器正常运行中")
                
        except Exception as e:
            print(f"启动字幕更新定时器失败: {str(e)}")

    def update_current_subtitle(self, position=None):
        """根据当前播放位置更新当前字幕"""
        try:
            # 如果未提供位置，则从视频播放器获取
            if position is None and hasattr(self, 'video_player'):
                position = self.video_player.get_position()
                
            if not hasattr(self, 'subtitles') or not self.subtitles:
                return
                
            # 查找匹配的字幕
            for i, subtitle in enumerate(self.subtitles):
                start_time = subtitle.get('start_time', 0)
                end_time = subtitle.get('end_time', 0)
                
                if start_time <= position <= end_time:
                    if hasattr(self, 'subtitle_list'):
                        self.subtitle_list.setCurrentRow(i)
                        self.subtitle_list.scrollToItem(self.subtitle_list.item(i))
                        self.current_highlighted_index = i
                    break
        except Exception as e:
            print(f"更新当前字幕出错: {str(e)}")

    def show_text_editor(self):
        """显示文本剪辑编辑器"""
        if not hasattr(self, 'subtitles') or not self.subtitles:
            QMessageBox.warning(self, "无字幕数据", "请先转录字幕，再使用文本剪辑功能。", 
                               QMessageBox.StandardButton.Ok)
            return
        
        try:
            # 切换到文本剪辑标签页
            self.tab_widget.setCurrentIndex(1)
            
            # 清空现有布局
            while self.text_edit_tab_layout.count():
                item = self.text_edit_tab_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            
            # 创建新的文本编辑器
            text_edit_label = QLabel("文本剪辑 - 选中要删除的文本并点击标记按钮")
            text_edit_label.setStyleSheet("color: #4fc3f7; font-size: 14px; font-weight: bold;")
            self.text_edit_tab_layout.addWidget(text_edit_label)
            
            # 说明文本
            instruction_label = QLabel('使用方法：选中要删除的文本，然后点击"标记删除"按钮。带删除线的部分将在剪辑时被移除。')
            instruction_label.setStyleSheet("color: #e0e0e0; font-size: 12px; font-weight: normal;")
            instruction_label.setWordWrap(True)
            self.text_edit_tab_layout.addWidget(instruction_label)
            
            # 创建文本编辑器
            self.transcript_text_edit = QTextEdit()
            self.transcript_text_edit.setReadOnly(False)
            self.transcript_text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #1e2430;
                    color: #e0e0e0;
                    border: 2px solid #1976d2;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 13px;
                    line-height: 1.5;
                }
            """)
            self.text_edit_tab_layout.addWidget(self.transcript_text_edit)
            
            # 操作按钮区域
            button_layout = QHBoxLayout()
            
            self.mark_delete_button = QPushButton("标记删除选中文本")
            self.mark_delete_button.clicked.connect(self.mark_text_for_deletion)
            self.mark_delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f44336;
                }
            """)
            
            self.preview_button = QPushButton("预览剪辑效果")
            self.preview_button.clicked.connect(self.preview_cuts)
            self.preview_button.setStyleSheet("""
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2196f3;
                }
            """)
            
            self.export_button = QPushButton("导出剪辑计划")
            self.export_button.clicked.connect(self.export_cut_plan)
            self.export_button.setStyleSheet("""
                QPushButton {
                    background-color: #388e3c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4caf50;
                }
            """)
            
            # 配置选项
            self.auto_mark_checkbox = QCheckBox("选中文本后自动标记为删除")
            self.auto_mark_checkbox.setChecked(False)
            self.auto_mark_checkbox.toggled.connect(self.toggle_auto_mark)
            self.auto_mark_checkbox.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            
            # 添加到布局
            button_layout.addWidget(self.mark_delete_button)
            button_layout.addWidget(self.preview_button)
            button_layout.addWidget(self.export_button)
            
            self.text_edit_tab_layout.addLayout(button_layout)
            self.text_edit_tab_layout.addWidget(self.auto_mark_checkbox)
            
            # 填充逐字稿数据
            self.populate_transcript_data()
            
        except Exception as e:
            error_msg = f"加载文本编辑器失败: {str(e)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            
            QMessageBox.critical(self, "错误", f"加载文本编辑器失败: {str(e)}", 
                               QMessageBox.StandardButton.Ok)

    def populate_transcript_data(self):
        """填充逐字稿数据，跟踪每个字幕段的位置"""
        try:
            if not hasattr(self, 'subtitles') or not self.subtitles:
                return
                
            # 构建完整的逐字稿文本
            full_text = ""
            self.subtitle_segments = []
            
            # 添加每个字幕的文本，并记录其位置
            for subtitle in self.subtitles:
                text = subtitle.get('text', '').strip()
                start_time = subtitle.get('start_time', 0)
                end_time = subtitle.get('end_time', 0)
                
                # 记录此字幕在全文中的开始位置
                start_pos = len(full_text)
                
                # 添加文本，确保字幕之间有空格
                if full_text and not full_text.endswith(' '):
                    full_text += ' '
                    
                full_text += text
                
                # 记录结束位置
                end_pos = len(full_text)
                
                # 保存这个字幕段的信息
                self.subtitle_segments.append({
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text
                })
            
            # 设置到文本编辑器
            if hasattr(self, 'transcript_text_edit'):
                self.transcript_text_edit.setText(full_text)
            
            print(f"已导入逐字稿，共 {len(self.subtitles)} 个片段")
            
        except Exception as e:
            print(f"填充逐字稿数据出错: {str(e)}")

    def mark_text_for_deletion(self):
        """标记选中的文本为要删除的部分，使用删除线样式"""
        try:
            if not hasattr(self, 'transcript_text_edit'):
                return
                
            # 获取当前选择
            cursor = self.transcript_text_edit.textCursor()
            if not cursor.hasSelection():
                return
                
            selection_start = cursor.selectionStart()
            selection_end = cursor.selectionEnd()
            selected_text = cursor.selectedText()
            
            if not selected_text.strip():
                return  # 跳过空白选择
                
            # 设置删除线格式
            format = QTextCharFormat()
            format.setFontStrikeOut(True)  # 使用删除线
            format.setForeground(QColor(200, 100, 100))  # 使用红色文本
            
            cursor.setPosition(selection_start)
            cursor.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(format)
            
            # 找出这个选区覆盖了哪些字幕段
            affected_segments = []
            for i, segment in enumerate(self.subtitle_segments):
                # 检查选区和字幕段是否有重叠
                if not (selection_end <= segment['start_pos'] or selection_start >= segment['end_pos']):
                    affected_segments.append(i)
            
            if affected_segments:
                # 创建一个新的剪辑标记
                cut_info = {
                    'start_idx': min(affected_segments),
                    'end_idx': max(affected_segments),
                    'start_time': self.subtitle_segments[min(affected_segments)]['start_time'],
                    'end_time': self.subtitle_segments[max(affected_segments)]['end_time'],
                    'text': selected_text
                }
                
                # 添加到剪辑列表
                self.cut_segments.append(cut_info)
                
                # 更新状态栏
                self.statusBar().showMessage(f"已标记删除: {self.format_time(cut_info['start_time'])} - {self.format_time(cut_info['end_time'])}")
        except Exception as e:
            print(f"标记删除文本出错: {str(e)}")
            import traceback
            print(traceback.format_exc())

    def toggle_auto_mark(self, checked):
        """切换自动标记模式"""
        try:
            if checked:
                # 连接文本选择变化信号
                self.transcript_text_edit.selectionChanged.connect(self.mark_text_for_deletion)
                print("启用自动标记模式")
            else:
                # 断开信号连接
                try:
                    self.transcript_text_edit.selectionChanged.disconnect(self.mark_text_for_deletion)
                except:
                    pass
                print("禁用自动标记模式")
        except Exception as e:
            print(f"切换自动标记模式出错: {str(e)}")

    def preview_cuts(self):
        """预览剪辑效果"""
        if not hasattr(self, 'cut_segments') or not self.cut_segments:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "无剪辑片段", "请先标记要删除的文本片段。", 
                                   QMessageBox.StandardButton.Ok)
            return
        
        try:
            # 切换回字幕标签页
            self.tab_widget.setCurrentIndex(0)
            
            # 构建跳过片段的时间表
            skip_segments = []
            for cut in self.cut_segments:
                skip_segments.append((cut['start_time'], cut['end_time']))
            
            # 按时间排序
            skip_segments.sort(key=lambda x: x[0])
            
            # 合并重叠的片段
            merged_segments = []
            for segment in skip_segments:
                if not merged_segments or segment[0] > merged_segments[-1][1]:
                    merged_segments.append(segment)
                else:
                    merged_segments[-1] = (merged_segments[-1][0], max(merged_segments[-1][1], segment[1]))
            
            # 存储跳过片段以供播放使用
            self.preview_skip_segments = merged_segments
            
            # 开始预览播放
            if hasattr(self, 'video_player'):
                self.video_player.seek(0)  # 从头开始播放
                self.video_player.play()
                self.preview_mode = True
                
                # 使用定时器检查是否需要跳过
                if not hasattr(self, 'preview_timer'):
                    from PyQt6.QtCore import QTimer
                    self.preview_timer = QTimer()
                    self.preview_timer.setInterval(50)  # 50ms检查一次
                    self.preview_timer.timeout.connect(self.check_preview_skip)
                    
                    # 添加视频结束检测定时器
                    self.end_check_timer = QTimer()
                    self.end_check_timer.setInterval(500)  # 500ms检查一次
                    self.end_check_timer.timeout.connect(self.check_preview_ended)
                
                self.preview_timer.start()
                self.end_check_timer.start()
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "预览模式", 
                                      "正在预览剪辑效果，播放器将自动跳过标记为删除的片段。\n\n"
                                      "预览结束后将自动返回编辑界面。", 
                                      QMessageBox.StandardButton.Ok)
                print(f"开始预览，跳过 {len(merged_segments)} 个片段")
            
        except Exception as e:
            print(f"预览剪辑效果出错: {str(e)}")
            import traceback
            print(traceback.format_exc())

    def check_preview_skip(self):
        """检查是否需要跳过当前播放位置"""
        if not hasattr(self, 'preview_skip_segments') or not hasattr(self, 'video_player'):
            return
        
        try:
            # 获取当前位置
            current_pos = self.video_player.get_position()
            
            # 检查是否在需要跳过的片段中
            for start, end in self.preview_skip_segments:
                if start <= current_pos < end:
                    # 跳过这个片段
                    print(f"跳过片段: {self.format_time(start)} - {self.format_time(end)}")
                    self.video_player.seek(end)
                    break
                
        except Exception as e:
            print(f"检查跳过位置出错: {str(e)}")

    def check_preview_ended(self):
        """检查预览是否结束"""
        if not hasattr(self, 'video_player'):
            return
        
        try:
            # 如果视频已停止或播放结束，恢复编辑器
            if not self.video_player.is_playing():
                duration = self.video_player.get_duration()
                position = self.video_player.get_position()
                
                # 如果接近结尾或已停止，认为预览结束
                if position >= duration - 1000 or position == 0:
                    self.restore_editor_after_preview()
                
        except Exception as e:
            print(f"检查预览结束出错: {str(e)}")

    def restore_editor_after_preview(self):
        """预览结束后恢复编辑器"""
        try:
            # 停止预览相关定时器
            if hasattr(self, 'preview_timer') and self.preview_timer.isActive():
                self.preview_timer.stop()
            
            if hasattr(self, 'end_check_timer') and self.end_check_timer.isActive():
                self.end_check_timer.stop()
            
            # 重置预览模式标志
            self.preview_mode = False
            
            # 如果编辑器之前是可见的，恢复它
            if hasattr(self, 'text_editor_dialog_visible') and self.text_editor_dialog_visible:
                if hasattr(self, 'text_editor_dialog'):
                    self.text_editor_dialog.show()
                    print("预览结束，恢复编辑器界面")
                
        except Exception as e:
            print(f"恢复编辑器出错: {str(e)}")

    def export_cut_plan(self):
        """导出剪辑计划"""
        if not hasattr(self, 'cut_segments') or not self.cut_segments:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "无剪辑片段", "请先标记要删除的文本片段。", 
                                   QMessageBox.StandardButton.Ok)
            return
        
        try:
            from PyQt6.QtWidgets import QFileDialog
            import json
            import os
            
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存剪辑计划", "", "剪辑计划文件 (*.json);;所有文件 (*)"
            )
            
            if not file_path:
                return
            
            # 准备导出数据
            export_data = {
                'video_path': self.media_path,
                'cut_segments': []
            }
            
            # 构建跳过片段的时间表
            skip_segments = []
            for cut in self.cut_segments:
                skip_segments.append({
                    'start_time': cut['start_time'],
                    'end_time': cut['end_time'],
                    'text': cut['text']
                })
            
            # 按时间排序
            skip_segments.sort(key=lambda x: x['start_time'])
            
            # 合并重叠的片段
            merged_segments = []
            for segment in skip_segments:
                if not merged_segments or segment['start_time'] > merged_segments[-1]['end_time']:
                    merged_segments.append(segment)
                else:
                    merged_segments[-1]['end_time'] = max(merged_segments[-1]['end_time'], segment['end_time'])
                    merged_segments[-1]['text'] += " " + segment['text']
            
            # 计算保留片段 (不是删除片段的部分)
            if hasattr(self, 'video_player'):
                total_duration = self.video_player.get_duration()
            else:
                # 如果没有视频长度，使用最后一个字幕的结束时间
                total_duration = max([s['end_time'] for s in self.subtitle_segments]) if self.subtitle_segments else 0
            
            keep_segments = []
            last_end = 0
            
            for segment in merged_segments:
                if segment['start_time'] > last_end:
                    keep_segments.append({
                        'start_time': last_end,
                        'end_time': segment['start_time'],
                        'keep': True
                    })
                
                # 记录要删除的片段
                keep_segments.append({
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'keep': False,
                    'text': segment['text']
                })
                
                last_end = segment['end_time']
            
            # 添加最后一个保留片段
            if last_end < total_duration:
                keep_segments.append({
                    'start_time': last_end,
                    'end_time': total_duration,
                    'keep': True
                })
            
            # 保存到导出数据
            export_data['segments'] = keep_segments
            
            # 计算剪辑后的总时长
            total_keep_duration = sum([s['end_time'] - s['start_time'] for s in keep_segments if s.get('keep', False)])
            export_data['original_duration'] = total_duration
            export_data['edited_duration'] = total_keep_duration
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            # 显示成功消息
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "导出成功", 
                f"剪辑计划已保存到: {os.path.basename(file_path)}\n\n"
                f"原始时长: {self.format_time(total_duration)}\n"
                f"剪辑后时长: {self.format_time(total_keep_duration)}\n"
                f"减少了: {self.format_time(total_duration - total_keep_duration)} ({(total_duration - total_keep_duration) / total_duration * 100:.1f}%)",
                QMessageBox.StandardButton.Ok
            )
            
            print(f"剪辑计划已导出: {file_path}")
            
        except Exception as e:
            print(f"导出剪辑计划出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "导出错误", f"导出剪辑计划失败: {str(e)}", 
                               QMessageBox.StandardButton.Ok)