#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QListWidget, QLabel, QFileDialog, 
                            QSplitter,  QTabWidget, QTextEdit, QApplication,
                            QMessageBox, QDialog, QLineEdit,
                            QFontComboBox, QSpinBox, QColorDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from app.components.video_player import VideoPlayer
from app.utils.asr_transcribe import ASRTranscribeThread
from app.utils.model_loader_task import ModelLoadThread
from app.components.progress_dialog import ProgressDialog
from app.utils.logger import setup_logger
from app.components.video_player_controls import VideoPlayerControls
from app.utils.event_bus import event_bus
from app.utils.video_processor import VideoProcessor
import json
class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)
        self.media_path = None
        self.subtitles = None
        self.current_highlighted_index = -1
        self.marked_indices = {}  # 存储被标记的字的下标
        self.words_timestamps = None
        self.asr = None
        self.asr_loaded = False  # 新增标志位
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
        
        # 添加字幕样式设置面板
        self.setup_subtitle_style_controls()
        
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
        
        # 添加导出视频按钮
        self.export_video_button = QPushButton("导出视频")
        self.export_video_button.clicked.connect(self.export_video)
        self.export_video_button.setMinimumHeight(40)
        
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.transcribe_button)
        button_layout.addWidget(self.text_edit_button)
        button_layout.addWidget(self.export_video_button)
        right_layout.addLayout(button_layout)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #ffffff;
                color: #666666;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 12px;
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
        
        # 添加搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词过滤字幕...")
        self.search_edit.textChanged.connect(self.update_subtitle_list)
        subtitle_tab_layout.addWidget(self.search_edit)
        
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
        splitter.setSizes([int(self.width() * 0.7), int(self.width() * 0.3)])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.splitterMoved.connect(self.handle_splitter_move)
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("准备就绪")
        
        # 添加模型加载状态标签
        self.status_label = QLabel("AI引擎未加载")
        self.statusBar().addPermanentWidget(self.status_label)

        # 设置窗口属性
        self.setWindowTitle("视频字幕剪辑工具")
        self.resize(1200, 700)
        
        # 应用简单样式
        self.apply_simple_style()
        
        # 初始化模型加载
        self.init_model_loader()
        
        # 订阅事件
        self.subscribe_events()

    def init_model_loader(self):
        """初始化模型加载器"""
        self.status_label.setText("AI引擎加载中...")
        asr_thread = ModelLoadThread()
        self.asr_thread = asr_thread
        asr_thread.start()
        
    def subscribe_events(self):
        """订阅事件"""
        event_bus.subscribe('asr_model_loaded', self.on_model_loaded)
        event_bus.subscribe('asr_progress', self.on_asr_progress)
        event_bus.subscribe('asr_result', self.on_asr_result)
        event_bus.subscribe('asr_error', self.on_asr_error)
        event_bus.subscribe('asr_complete', self.on_asr_complete)

    def on_asr_complete(self, data):
        """ASR转录完成事件处理"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        self.statusBar().showMessage("转录已完成", 5000)

    def on_model_loaded(self, data):
        """模型加载完成事件处理"""
        self.asr = data
        self.asr_loaded = True
        if hasattr(self, 'status_label'):
            self.status_label.setText("AI引擎就绪")
        self.transcribe_button.setEnabled(True)
        self.statusBar().showMessage("模型加载完成", 5000)

    def on_asr_progress(self, data):
        """ASR进度事件处理"""
        progress = data.get('progress', 0)
        message = data.get('message', '')
        self.statusBar().showMessage(f"{message} {progress}%")

    def on_asr_result(self, data):
        """ASR结果事件处理"""
        subtitles = data.get('subtitles')
        words_timestamps = data.get('words_timestamps')
        
        if subtitles:
            self.logger.info(f"收到转录结果: {len(subtitles)} 条字幕")
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
            QMessageBox.information(self, "转录完成", f"转录已完成，共生成 {len(subtitles)} 条字幕。", 
                                    QMessageBox.StandardButton.Ok)
            
            self.subtitles = subtitles
            self.words_timestamps = words_timestamps
            self.update_subtitle_list()
            self.statusBar().showMessage(f"转录完成，共 {len(subtitles)} 条字幕")
        else:
            self.logger.error("未接收到有效的转录结果")
            self.statusBar().showMessage("转录失败，未生成字幕")
            QMessageBox.warning(self, "转录失败", "转录过程未生成有效字幕，请检查视频文件。", 
                                QMessageBox.StandardButton.Ok)

    def on_asr_error(self, data):
        """ASR错误事件处理"""
        error = data.get('error', '未知错误')
        details = data.get('details', '')
        self.logger.error(f"转录错误: {error}\n{details}")
        QMessageBox.critical(self, "转录错误", f"转录过程发生错误：{error}", 
                            QMessageBox.StandardButton.Ok)
        self.statusBar().showMessage("转录失败")
        
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()

    def handle_splitter_move(self, pos, index):
        """处理分割器移动事件"""
        self.logger.debug(f"分割器位置已调整: {pos}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        self.logger.info('正在关闭主窗口...')
        
        # 检查并等待模型加载线程
        if hasattr(self, 'asr_thread'):
            self.logger.debug(f'模型加载线程状态: 运行中={self.asr_thread.isRunning()}')
            if self.asr_thread.isRunning():
                self.asr_thread.quit()
                self.asr_thread.wait()
        
        # 检查并等待转录线程
        if hasattr(self, 'transcribe_thread'):
            self.logger.debug(f'转录线程状态: 运行中={self.transcribe_thread.isRunning()}')
            if self.transcribe_thread.isRunning():
                self.transcribe_thread.quit()
                self.transcribe_thread.wait()
        
        self.logger.info('窗口关闭完成')
        event.accept()

    def import_video(self):
        """导入视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov);;所有文件 (*.*)"
        )
        
        if file_path:
            self.logger.info(f"尝试导入视频: {file_path}")
            self.media_path = file_path
            self.video_player.set_media(file_path)
            self.logger.info(f"成功导入视频: {file_path}")
            self.statusBar().showMessage(f"已导入视频: {file_path}")

    def transcribe_video(self):
        """转录视频"""
        if not self.media_path:
            QMessageBox.warning(self, "提示", "请先导入视频文件", 
                                QMessageBox.StandardButton.Ok)
            return
        
        if not self.asr_loaded or not self.asr:
            QMessageBox.warning(self, "提示", "AI引擎尚未加载完成，请稍候", 
                                QMessageBox.StandardButton.Ok)
            return
        
        self.logger.info('正在执行视频转录...')
        self.show_progress_dialog("正在转录", "视频正在转录中，请稍候...")
        
        # 创建并启动转录线程
        self.transcribe_thread = ASRTranscribeThread(self.asr, self.media_path)
        self.transcribe_thread.start()

    def update_subtitle_list(self, filter_text=""):
        """更新字幕列表"""
        if not self.subtitles:
            return
        
        self.subtitle_list.clear()
        for subtitle in self.subtitles:
            text = subtitle.get('text', '')
            start_time = subtitle.get('start_time', 0)
            end_time = subtitle.get('end_time', 0)
            
            # 如果有过滤文本，检查字幕文本是否包含过滤文本
            if filter_text and filter_text.lower() not in text.lower():
                continue
            
            start_str = self.format_time(start_time)
            end_str = self.format_time(end_time)
            
            self.logger.debug(f"添加字幕: {text} ({start_str}-{end_str})")
            item_text = f"[{start_str} - {end_str}] {text}"
            self.subtitle_list.addItem(item_text)
        
        self.logger.info(f"字幕列表更新完成，显示 {len(self.subtitles)} 条")

    def on_subtitle_clicked(self, item):
        """字幕点击事件处理"""
        index = self.subtitle_list.row(item)
        if 0 <= index < len(self.subtitles):
            start_time = self.subtitles[index].get('start_time', 0)
            self.logger.debug(f"跳转到字幕时间点: {start_time}ms")
            self.video_player.set_position(start_time)

    def format_time(self, milliseconds):
        """格式化时间（毫秒转为时:分:秒.毫秒）"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        hours = minutes // 60
        milliseconds %= 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    

    def show_text_editor(self):
        """显示文本编辑器"""
        if not self.words_timestamps:
            QMessageBox.warning(self, "提示", "请先转录视频生成逐字稿", 
                                QMessageBox.StandardButton.Ok)
            return
        
        self.logger.info(f"已导入逐字稿，共 {len(self.words_timestamps)} 个字")
        
        # 创建文本编辑器
        self.text_editor = QTextEdit()
        self.text_editor.setReadOnly(False)  # 允许选择文本
        self.text_editor.setMinimumHeight(200)
        self.text_editor.mouseReleaseEvent = self.on_text_editor_mouse_release
        
        # 创建预览按钮
        preview_button = QPushButton("预览")
        preview_button.clicked.connect(self.preview_marked_text)
        
        # 创建导出按钮
        export_button = QPushButton("导出剪辑计划")
        export_button.clicked.connect(self.export_edit_plan)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(preview_button)
        button_layout.addWidget(export_button)
        
        # # 清空并重新设置标签页布局
        # for i in reversed(range(self.text_edit_tab_layout.count())): 
        #     self.text_edit_tab_layout.itemAt(i).widget().setParent(None)
        
        self.text_edit_tab_layout.addWidget(self.text_editor)
        self.text_edit_tab_layout.addLayout(button_layout)
        
        # 切换到文本编辑标签页
        self.tab_widget.setCurrentWidget(self.text_edit_tab)
        
        # 显示文本内容
        self.display_text_content()

    def on_auto_mark_changed(self, state):
        """自动标记模式状态改变事件处理"""
        if state == Qt.CheckState.Checked.value:
            self.logger.info("启用自动标记模式")
            self.text_editor.setReadOnly(False)
            self.text_editor.textChanged.connect(self.on_text_changed)
        else:
            self.text_editor.setReadOnly(True)
            self.text_editor.textChanged.disconnect(self.on_text_changed)

    def preview_marked_text(self):
        """预览标记的文本"""
        if not self.marked_indices:
            QMessageBox.information(self, "提示", "请先标记需要删除的文本", 
                                    QMessageBox.StandardButton.Ok)
            return
        
        # 获取需要跳过的时间段
        merged_segments = self.get_merged_segments()
        self.logger.info(f"开始预览，跳过 {len(merged_segments)} 个片段")
        
        # 保存当前编辑器状态
        self.text_editor.setReadOnly(True)
        # 预览播放
        current_position = 0
        for start, end in merged_segments:
            # 播放到下一个跳过片段的开始
            if current_position < start:
                self.video_player.set_position(current_position)
                self.video_player.play()
                while self.video_player.get_position() < start:
                    QApplication.processEvents()
                self.video_player.pause()
            
            self.logger.debug(f"跳过片段: {self.format_time(start)} - {self.format_time(end)}")
            current_position = end
            self.video_player.set_position(current_position)
        
        # 播放剩余部分
        if current_position < self.video_player.get_duration():
            self.video_player.set_position(current_position)
            self.video_player.play()
            while self.video_player.get_position() < self.video_player.get_duration():
                QApplication.processEvents()
            self.video_player.pause()
        
        self.logger.info("预览结束，恢复编辑器界面")
        self.text_editor.setReadOnly(False)

    def export_edit_plan(self):
        """导出剪辑计划"""
        if not self.marked_indices:
            QMessageBox.information(self, "提示", "请先标记需要删除的文本", 
                                    QMessageBox.StandardButton.Ok)
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存剪辑计划",
            "",
            "JSON文件 (*.json)"
        )
        
        if file_path:
            merged_segments = self.get_merged_segments()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'video_path': self.media_path,
                    'segments': merged_segments
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"剪辑计划已导出: {file_path}")
            QMessageBox.information(self, "导出成功", "剪辑计划已成功导出", 
                                    QMessageBox.StandardButton.Ok)

    def show_progress_dialog(self, title, message):
        """显示进度对话框"""
        self.progress_dialog = ProgressDialog(self, title, message)
        self.progress_dialog.show()

    def setup_playback_controls(self):
        """设置播放控制面板"""
        # 创建播放控制组件
        self.player_controls = VideoPlayerControls()
        
        # 连接信号
        self.player_controls.play_clicked.connect(self.video_player.toggle_play)
        self.player_controls.position_changed.connect(self.on_progress_changed)
        self.player_controls.volume_changed.connect(self.video_player.set_volume)
        
        # 连接视频播放器的信号
        self.video_player.position_changed.connect(self.update_position)
        # self.video_player.duration_changed.connect(self.update_duration)
        self.video_player.state_changed.connect(self.update_play_button)
        
        # 添加到左侧布局
        self.left_layout.addWidget(self.player_controls)
        
    def update_position(self, position):
        """更新播放位置和字幕显示"""
        if self.video_player.get_duration() > 0:
            self.player_controls.update_progress(position, self.video_player.get_duration())
            
            # 更新字幕显示
            if self.subtitles:
                current_subtitle = None
                for subtitle in self.subtitles:
                    start_time = subtitle.get('start_time', 0)
                    end_time = subtitle.get('end_time', 0)
                    if start_time <= position <= end_time:
                        current_subtitle = subtitle.get('text', '')
                        break
                self.video_player.set_subtitle(current_subtitle)
            self.video_player.set_position(position)
            
    def on_progress_changed(self, value):
        """进度条值改变事件处理"""
        if self.video_player.get_duration() > 0:
            position = (value / 1000.0) * self.video_player.get_duration()
            self.video_player.set_position(position)
            
    def update_play_button(self, is_playing):
        """更新播放按钮状态"""
        self.player_controls.update_play_button_state(is_playing)

    def get_merged_segments(self):
        """获取合并后的时间段"""
        if not self.marked_indices or not self.words_timestamps:
            return []
        
        self.logger.info(f"开始合并，标记了 {self.marked_indices} ")
        # 将标记的索引转换为时间段
        segments = []
        for index in sorted(self.marked_indices.keys()):
            if index < len(self.words_timestamps):
                word_info = self.words_timestamps[index]
                segments.append((word_info['start'], word_info['end']))
        
        # 合并重叠或相邻的时间段
        if not segments:
            return []
        
        merged = [segments[0]]
        for current in segments[1:]:
            previous = merged[-1]
            # 如果当前段与前一段重叠或相邻（间隔小于100ms），则合并
            if current[0] - previous[1] <= 100:
                merged[-1] = (previous[0], max(previous[1], current[1]))
            else:
                merged.append(current)
        
        return merged

    def display_text_content(self):
        """显示文本内容"""
        if not self.words_timestamps:
            return
        
        # 暂时断开文本变化信号
        try:
            self.text_editor.textChanged.disconnect(self.on_text_changed)
        except TypeError:
            # 如果信号未连接，直接忽略
            pass
        
        # 获取当前光标位置
        cursor = self.text_editor.textCursor()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        
        # 清空文本编辑器
        self.text_editor.clear()
        
        # 显示所有文字
        text = ''.join(word['word'] for word in self.words_timestamps)
        self.text_editor.setPlainText(text)
        
        # 标记已选中的文字
        cursor = self.text_editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(True)  # 设置删除线效果
        fmt.setBackground(QColor('#ffcccc'))  # 设置红色背景
        
        for index in self.marked_indices:
            if index < len(self.words_timestamps):
                start_pos = sum(len(word['word']) for word in self.words_timestamps[:index])
                length = len(self.words_timestamps[index]['word'])
                cursor.setPosition(start_pos)
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, length)
                cursor.mergeCharFormat(fmt)
        
        # 恢复光标位置
        cursor = self.text_editor.textCursor()
        cursor.setPosition(selection_start)
        if selection_start != selection_end:
            cursor.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
        self.text_editor.setTextCursor(cursor)
          
    def on_text_changed(self):
        """文本变化事件处理"""
        if not self.auto_mark_checkbox.isChecked() or not self.words_timestamps:
            return
        
        # 暂时断开文本变化信号
        self.text_editor.textChanged.disconnect(self.on_text_changed)
        
        try:
            # 获取当前文本和光标位置
            current_text = self.text_editor.toPlainText()
            cursor = self.text_editor.textCursor()
            selection_start = cursor.selectionStart()
            selection_end = cursor.selectionEnd()
            
            # 如果有选中文本
            if selection_start != selection_end:
                # 计算选中范围内的所有字符对应的单词索引
                total_length = 0
                for i, word in enumerate(self.words_timestamps):
                    word_length = len(word['word'])
                    word_start = total_length
                    word_end = total_length + word_length
                    
                    # 如果当前单词与选中范围有重叠
                    if not (word_end <= selection_start or word_start >= selection_end):
                        # 切换该字的标记状态
                        if i in self.marked_indices:
                            del self.marked_indices[i]
                        else:
                            self.marked_indices[i] = True
                    
                    total_length += word_length
            else:
                # 单字符处理逻辑
                cursor_pos = cursor.position()
                total_length = 0
                for i, word in enumerate(self.words_timestamps):
                    word_length = len(word['word'])
                    if total_length <= cursor_pos < total_length + word_length:
                        # 切换该字的标记状态
                        if i in self.marked_indices:
                            del self.marked_indices[i]
                        else:
                            self.marked_indices[i] = True
                        break
                    total_length += word_length
            
            # 重新显示文本内容
            self.display_text_content()
            
            # 恢复光标位置
            cursor = self.text_editor.textCursor()
            cursor.setPosition(selection_start)
            if selection_start != selection_end:
                cursor.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
            self.text_editor.setTextCursor(cursor)
        finally:
            # 重新连接文本变化信号
            self.text_editor.textChanged.connect(self.on_text_changed)

    def on_text_editor_mouse_release(self, event):
        """处理文本编辑器的鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self.text_editor.textCursor()
            if cursor.hasSelection():
                # 获取选中的文本范围
                selection_start = cursor.selectionStart()
                selection_end = cursor.selectionEnd()
                
                # 创建删除选项对话框
                reply = QMessageBox.question(self, "删除确认",
                                        "是否要删除选中的文本？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 计算选中范围内的所有字符对应的单词索引
                    total_length = 0
                    for i, word in enumerate(self.words_timestamps):
                        word_length = len(word['word'])
                        word_start = total_length
                        word_end = total_length + word_length
                        
                        # 如果当前单词与选中范围有重叠
                        if not (word_end <= selection_start or word_start >= selection_end):
                            self.marked_indices[i] = True
                        
                        total_length += word_length
                    
                    # 重新显示文本内容
                    self.display_text_content()
                    
                    # 恢复光标位置
                    cursor = self.text_editor.textCursor()
                    cursor.setPosition(selection_start)
                    if selection_start != selection_end:
                        cursor.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
                    self.text_editor.setTextCursor(cursor)
    

    def setup_subtitle_style_controls(self):
        """设置字幕样式控制面板"""
        style_panel = QWidget()
        style_layout = QVBoxLayout(style_panel)
        
        # 字幕操作按钮
        button_layout = QHBoxLayout()
        self.merge_button = QPushButton("合并选中字幕")
        self.merge_button.clicked.connect(self.merge_selected_subtitles)
        self.split_button = QPushButton("分割字幕")
        self.split_button.clicked.connect(self.split_subtitle)
        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.split_button)
        
        style_layout.addLayout(button_layout)
        style_layout.addWidget(QLabel("字幕样式:"))
        # 字体选择
        font_layout = QHBoxLayout()
        font_label = QLabel("字体:")
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.on_font_changed)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_combo)
        
        # 字体大小
        size_layout = QHBoxLayout()
        size_label = QLabel("大小:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(16)
        self.size_spin.valueChanged.connect(self.on_size_changed)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        
        # 字体颜色
        color_layout = QHBoxLayout()
        color_label = QLabel("颜色:")
        self.color_button = QPushButton()
        self.color_button.setFixedSize(24, 24)
        self.color_button.setStyleSheet("background-color: white;")
        self.color_button.clicked.connect(self.on_color_clicked)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_button)
        
        # 背景颜色
        bg_layout = QHBoxLayout()
        bg_label = QLabel("背景:")
        self.bg_button = QPushButton()
        self.bg_button.setFixedSize(24, 24)
        self.bg_button.setStyleSheet("background-color: rgba(0,0,0,128);")
        self.bg_button.clicked.connect(self.on_bg_clicked)
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(self.bg_button)
        
        # 添加所有控件到布局
        style_layout.addLayout(font_layout)
        style_layout.addLayout(size_layout)
        style_layout.addLayout(color_layout)
        style_layout.addLayout(bg_layout)
        
        # 添加到左侧面板
        self.left_layout.addWidget(style_panel)
        
    def on_font_changed(self, font):
        """字体改变事件处理"""
        if self.video_player:
            current_size = self.video_player.subtitle_font.pointSize()
            font.setPointSize(current_size)
            self.video_player.set_subtitle_font(font)
            
    def on_size_changed(self, size):
        """字体大小改变事件处理"""
        if self.video_player:
            font = self.video_player.subtitle_font
            font.setPointSize(size)
            self.video_player.set_subtitle_font(font)
            
    def on_color_clicked(self):
        """字体颜色选择事件处理"""
        color = QColorDialog.getColor(self.video_player.subtitle_color if self.video_player else Qt.white)
        if color.isValid():
            self.color_button.setStyleSheet(f"background-color: {color.name()};")
            if self.video_player:
                self.video_player.set_subtitle_color(color)
                
    def on_bg_clicked(self):
        """背景颜色选择事件处理"""
        color = QColorDialog.getColor(self.video_player.subtitle_background if self.video_player else QColor(0,0,0,128))
        if color.isValid():
            self.bg_button.setStyleSheet(f"background-color: {color.name()};")
            if self.video_player:
                self.video_player.set_subtitle_background(color)

    def on_time_offset_changed(self, offset):
        """字幕时间偏移调整"""
        if self.subtitles:
            for subtitle in self.subtitles:
                subtitle['start_time'] = subtitle.get('start_time', 0) + offset * 1000
                subtitle['end_time'] = subtitle.get('end_time', 0) + offset * 1000
            self.update_subtitle_list()

    def merge_selected_subtitles(self):
        """合并选中的字幕"""
        selected_items = self.subtitle_list.selectedItems()
        if len(selected_items) < 2:
            QMessageBox.warning(self, "警告", "请至少选择两个字幕进行合并")
            return
            
        indices = [self.subtitle_list.row(item) for item in selected_items]
        indices.sort()
        
        # 确保选中的字幕是连续的
        if indices[-1] - indices[0] + 1 != len(indices):
            QMessageBox.warning(self, "警告", "只能合并连续的字幕")
            return
            
        # 合并字幕
        merged_text = ' '.join(self.subtitles[i]['text'] for i in indices)
        merged_subtitle = {
            'text': merged_text,
            'start_time': self.subtitles[indices[0]]['start_time'],
            'end_time': self.subtitles[indices[-1]]['end_time']
        }
        
        # 更新字幕列表
        for i in reversed(indices[1:]):
            del self.subtitles[i]
        self.subtitles[indices[0]] = merged_subtitle
        self.update_subtitle_list()
        
    def split_subtitle(self):
        """分割选中的字幕"""
        selected_items = self.subtitle_list.selectedItems()
        if len(selected_items) != 1:
            QMessageBox.warning(self, "警告", "请选择一个字幕进行分割")
            return
            
        index = self.subtitle_list.row(selected_items[0])
        subtitle = self.subtitles[index]
        text = subtitle['text']
        
        # 创建分割对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("分割字幕")
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)
        
        button_box = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取分割后的文本
            new_texts = [t.strip() for t in text_edit.toPlainText().split('\n') if t.strip()]
            if len(new_texts) < 2:
                QMessageBox.warning(self, "警告", "请至少分割成两个字幕")
                return
                
            # 计算每个字幕的时间
            duration = subtitle['end_time'] - subtitle['start_time']
            interval = duration / len(new_texts)
            
            # 创建新字幕
            new_subtitles = []
            for i, text in enumerate(new_texts):
                new_subtitle = {
                    'text': text,
                    'start_time': subtitle['start_time'] + i * interval,
                    'end_time': subtitle['start_time'] + (i + 1) * interval
                }
                new_subtitles.append(new_subtitle)
                
            # 更新字幕列表
            self.subtitles[index:index+1] = new_subtitles
            self.update_subtitle_list()

    def export_video(self):
        """导出剪辑后的视频"""
        if not self.marked_indices:
            QMessageBox.information(self, "提示", "请先标记需要删除的文本", 
                                    QMessageBox.StandardButton.Ok)
            return
        
        # 获取输出文件路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存剪辑视频",
            "",
            "MP4文件 (*.mp4)"
        )
        
        if not file_path:
            return
        
        # 获取需要跳过的时间段
        merged_segments = self.get_merged_segments()
        if not merged_segments:
            QMessageBox.information(self, "提示", "没有找到有效的剪辑片段", 
                                    QMessageBox.StandardButton.Ok)
            return
        
        # 显示进度对话框
        self.show_progress_dialog("视频导出", "正在处理视频...")
        
        # 创建视频处理器
        self.video_processor = VideoProcessor()
        self.video_processor.progress_updated.connect(self.on_video_progress)
        self.video_processor.process_completed.connect(self.on_video_completed)
        self.video_processor.process_error.connect(self.on_video_error)
        
        # 开始处理视频
        self.video_processor.process_video(self.media_path, merged_segments, file_path)
    
    def on_video_progress(self, progress, message):
        """视频处理进度更新"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.set_progress(progress)
            self.progress_dialog.set_message(message)
    
    def on_video_completed(self, output_path):
        """视频处理完成"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        self.logger.info(f"视频导出成功: {output_path}")
        QMessageBox.information(self, "导出成功", f"视频已成功导出到:\n{output_path}", 
                                QMessageBox.StandardButton.Ok)
    
    def on_video_error(self, error_message):
        """视频处理错误"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        self.logger.error(f"视频导出错误: {error_message}")
        QMessageBox.critical(self, "导出失败", f"视频导出失败:\n{error_message}", 
                            QMessageBox.StandardButton.Ok)

    def apply_simple_style(self):
        """应用简单的窗口样式"""