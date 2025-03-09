#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QListWidget, QLabel, QFileDialog, 
                            QSplitter, QSlider, QAbstractItemView, QProgressDialog,
                            QDialog, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from app.components.video_player import VideoPlayer
from app.utils.asr_transcribe import ASRTranscribeThread
from app.components.asr import ASRProcessor

class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.media_path = None
        self.subtitles = None
        self.current_highlighted_index = -1
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
        self.create_playback_controls()
        
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
        
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.transcribe_button)
        right_layout.addLayout(button_layout)
        
        # 字幕列表
        subtitle_label = QLabel("字幕列表")
        right_layout.addWidget(subtitle_label)
        
        self.subtitle_list = QListWidget()
        self.subtitle_list.setMinimumWidth(350)
        right_layout.addWidget(self.subtitle_list, 1)
        
        # 设置字幕列表样式
        self.setup_subtitle_list()
        
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

    def apply_simple_style(self):
        """应用简单样式，避免语法错误"""
        # 主窗口样式
        self.setStyleSheet("QMainWindow { background-color: #121820; color: #e1e1e1; }")
        
        # 按钮样式
        if hasattr(self, 'import_button') and hasattr(self, 'transcribe_button'):
            button_style = "QPushButton { background-color: #1a1f2a; color: #4fc3f7; border: 2px solid #2196f3; border-radius: 5px; padding: 8px; font-weight: bold; }"
            self.import_button.setStyleSheet(button_style)
            self.import_button.setText("📂 导入视频")
            self.transcribe_button.setStyleSheet(button_style)
            self.transcribe_button.setText("🎤 转录字幕")
        
        # 字幕列表样式
        if hasattr(self, 'subtitle_list'):
            subtitle_style = "QListWidget { background-color: #1a1f2a; color: #e1e1e1; border: 2px solid #2196f3; border-radius: 5px; }"
            self.subtitle_list.setStyleSheet(subtitle_style)
        
        # 播放控制样式
        if hasattr(self, 'play_button') and hasattr(self, 'stop_button'):
            control_style = "QPushButton { background-color: #1a1f2a; color: #e1e1e1; border: 2px solid #2196f3; border-radius: 20px; font-weight: bold; }"
            self.play_button.setStyleSheet(control_style)
            self.stop_button.setStyleSheet(control_style)

    def create_playback_controls(self):
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
                
                # 使用 setCurrentRow 并确保视觉反馈
                if matching_index < self.subtitle_list.count():
                    # 将项目设置为当前项
                    self.subtitle_list.setCurrentRow(matching_index)
                    
                    # 获取项目并设置背景色来增强高亮效果
                    item = self.subtitle_list.item(matching_index)
                    if item:
                        # 设置项目背景色以确保高亮明显
                        item.setBackground(self.get_highlight_color())
                        
                        # 清除之前高亮项的背景色
                        if hasattr(self, 'current_highlighted_index') and self.current_highlighted_index >= 0:
                            old_item = self.subtitle_list.item(self.current_highlighted_index)
                            if old_item and self.current_highlighted_index != matching_index:
                                old_item.setBackground(self.get_normal_color())
                        
                        # 滚动到当前项以确保可见
                        self.subtitle_list.scrollToItem(item, hint=self.subtitle_list.ScrollHint.PositionAtCenter)
                        
                        # 更新当前高亮索引
                        self.current_highlighted_index = matching_index
                        
        except Exception as e:
            print(f"更新字幕高亮出错: {str(e)}")
            import traceback
            print(traceback.format_exc())

    def get_highlight_color(self):
        """获取高亮颜色"""
        from PyQt6.QtGui import QColor
        return QColor(41, 128, 185)  # 蓝色

    def get_normal_color(self):
        """获取普通项目颜色"""
        from PyQt6.QtGui import QColor
        return QColor(26, 31, 42)  # 深灰色背景

    def import_video(self):
        """导入视频文件"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv)"
        )
        
        if file_path:
            self.media_path = file_path
            self.video_player.load_media(file_path)
            self.statusBar().showMessage(f"已加载视频: {file_path}")
            
            # 清空字幕
            self.subtitles = None
            self.update_subtitle_list()

    def transcribe_video(self):
        """转录视频字幕"""
        if not self.media_path:
            self.statusBar().showMessage("请先导入视频文件")
            return
        
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
            from PyQt6.QtCore import Qt, QTimer
            
            # 立即创建并显示对话框
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
            
            # 导入必要的模块
            from app.utils.asr_transcribe import ASRTranscribeThread
            from app.components.asr import ASRProcessor
            
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
            from PyQt6.QtWidgets import QMessageBox
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
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "转录完成", f"转录已完成，共生成 {len(subtitles)} 条字幕。", 
                                        QMessageBox.StandardButton.Ok)
                
                self.subtitles = subtitles
                self.update_subtitle_list()
                self.statusBar().showMessage(f"转录完成，共 {len(subtitles)} 条字幕")
            else:
                print("未接收到有效的转录结果")
                self.statusBar().showMessage("转录失败，未生成字幕")
                
                # 显示转录失败的提示
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "转录失败", "转录过程未生成有效字幕，请检查视频文件。", 
                                    QMessageBox.StandardButton.Ok)
        except Exception as e:
            error_msg = f"处理转录结果出错: {str(e)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            self.statusBar().showMessage("转录出错，请检查控制台输出")
            
            # 显示错误提示
            from PyQt6.QtWidgets import QMessageBox
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
                text = subtitle.get('text', '').strip()
                start_time = subtitle.get('start_time', 0)
                end_time = subtitle.get('end_time', 0)
                
                # 格式化时间
                start_str = self.format_time(start_time)
                end_str = self.format_time(end_time)
                
                # 设置显示文本 (保持简洁)
                if len(text) > 50:  # 如果文本太长，截断显示
                    display_text = f"{text[:50]}... ({start_str})"
                else:
                    display_text = f"{text} ({start_str})"
                
                # 添加到列表
                self.subtitle_list.addItem(display_text)
                
            print(f"字幕列表更新完成，显示 {len(self.subtitles)} 条")
            print("字幕列表已更新")
            
            # 重置当前高亮索引
            self.current_highlighted_index = -1
            
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

    def setup_subtitle_list(self):
        """设置字幕列表样式和行为"""
        if hasattr(self, 'subtitle_list'):
            from PyQt6.QtWidgets import QAbstractItemView
            
            # 设置字幕列表样式 - 使用更柔和的颜色
            self.subtitle_list.setAlternatingRowColors(True)
            self.subtitle_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.subtitle_list.setStyleSheet("""
                QListWidget {
                    background-color: #1e2430;  /* 更柔和的深蓝灰色背景 */
                    color: #e0e0e0;  /* 亮一点的文本颜色 */
                    border: 2px solid #1976d2;  /* 蓝色边框 */
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 13px;
                    alternate-background-color: #283447;  /* 稍微浅一点的交替行背景 */
                }
                
                QListWidget::item {
                    border-bottom: 1px solid #394b61;  /* 更柔和的分隔线 */
                    padding: 8px 5px;  /* 增加垂直内边距 */
                    margin: 3px 1px;  /* 增加间距 */
                    border-radius: 4px;  /* 圆角项目 */
                }
                
                QListWidget::item:hover {
                    background-color: #324054;  /* 更柔和的悬停背景 */
                    border: 1px solid #4fc3f7;  /* 悬停时的亮蓝色边框 */
                }
                
                QListWidget::item:selected {
                    background-color: #1769aa;  /* 稍深的蓝色选中背景 */
                    color: #ffffff;  /* 选中项的白色文本 */
                    border: none;
                }
                
                /* 滚动条样式 */
                QScrollBar:vertical {
                    border: none;
                    background: #1e2430;
                    width: 10px;
                    margin: 0px;
                    border-radius: 5px;
                }
                
                QScrollBar::handle:vertical {
                    background: #4f5b69;  /* 更柔和的滚动条颜色 */
                    min-height: 30px;
                    border-radius: 5px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background: #5f6b79;  /* 悬停时稍亮 */
                }
                
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                    height: 0px;
                }
                
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
            
            # 连接项目点击事件
            self.subtitle_list.itemClicked.connect(self.on_subtitle_clicked)
            print("字幕列表样式已更新，使用更柔和的背景颜色")