#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QListWidget, QLabel, QFileDialog, 
                            QSplitter,  QTabWidget, QTextEdit, QApplication,
                            QMessageBox, QDialog, QLineEdit,
                            QFontComboBox, QSpinBox, QColorDialog,QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from app.components.video_player import VideoPlayer
from app.utils.asr_transcribe import ASRTranscribeThread
from app.utils.model_loader_task import ModelLoadThread
from app.utils.batch_transcribe_queue import BatchTranscribeQueue
from app.components.progress_dialog import ProgressDialog
from app.utils.logger import setup_logger
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
        self.batch_queue = BatchTranscribeQueue()  # 批量转录队列
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局和组件"""
        # 创建主布局
        main_layout = QHBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(main_layout)
        self.setCentralWidget(self.central_widget)

         # 左侧视频列表面板
        left_list_panel = QWidget()
        left_list_layout = QVBoxLayout(left_list_panel)
        left_list_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加视频列表
        self.video_list = QListWidget()
        self.video_list.setAlternatingRowColors(True)
        self.video_list.itemDoubleClicked.connect(self.on_video_list_double_clicked)
        self.video_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.video_list.customContextMenuRequested.connect(self.show_video_context_menu)
        self.video_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)  # 支持多选
        self.video_list.setFixedWidth(200)
        self.video_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        left_list_layout.addWidget(self.video_list)
        
        # 左侧面板 - 视频播放区域
        left_panel = QWidget()
        self.left_layout = QVBoxLayout(left_panel)
        self.left_layout.setContentsMargins(10, 10, 10, 10)
        self.left_layout.setSpacing(10)
        
        # 视频播放器
        self.video_player = VideoPlayer()
        self.video_player.setMinimumSize(640, 360)  # 确保视频播放器有足够大的尺寸
        self.left_layout.addWidget(self.video_player)
        
        
        # 添加字幕样式设置面板
        self.setup_subtitle_style_controls()

          # 创建左侧分割器
        left_splitter = QSplitter(Qt.Orientation.Horizontal)
        left_splitter.addWidget(left_list_panel)
        left_splitter.addWidget(left_panel)
        left_splitter.setSizes([200, 800])  # 设置初始宽度比例
        
        # 右侧面板 - 字幕和控制按钮
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 导入按钮区域
        import_layout = QHBoxLayout()
        self.import_button = QPushButton("导入视频")
        self.import_button.clicked.connect(self.import_video)
        self.import_button.setMinimumHeight(40)
        
        
        import_layout.addWidget(self.import_button)
        
        # 转录按钮区域
        transcribe_layout = QHBoxLayout()
        self.transcribe_button = QPushButton("转录字幕")
        self.transcribe_button.clicked.connect(self.transcribe_video)
        self.transcribe_button.setMinimumHeight(40)
        
        transcribe_layout.addWidget(self.transcribe_button)
        
        # 添加文本剪辑按钮
        self.text_edit_button = QPushButton("按文本剪辑")
        self.text_edit_button.clicked.connect(self.show_text_editor)
        self.text_edit_button.setMinimumHeight(40)
        
        # 添加导出视频按钮
        self.export_video_button = QPushButton("导出视频")
        self.export_video_button.clicked.connect(self.export_video)
        self.export_video_button.setMinimumHeight(40)
        
        # 添加所有按钮到主按钮布局
        button_layout.addLayout(import_layout)
        button_layout.addLayout(transcribe_layout)
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
        splitter.addWidget(left_splitter)
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

    def on_asr_progress(self, data, message=''):
        """ASR进度事件处理"""
        # 处理来自ASRTranscribeThread的进度信号(int, str)和来自event_bus的进度事件(dict)
        if isinstance(data, dict):
            # 来自event_bus的事件数据
            progress = data.get('progress', 0)
            message = data.get('message', '')
        else:
            # 来自ASRTranscribeThread的信号数据
            progress = data
            # message参数已经通过第二个参数传入
            
        # 显示进度信息
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
            # 保存字幕文件
            self.save_subtitles(subtitles, words_timestamps)
            self.update_subtitle_list()
            self.statusBar().showMessage(f"转录完成，共 {len(subtitles)} 条字幕")
        else:
            self.logger.error("未接收到有效的转录结果")
            self.statusBar().showMessage("转录失败，未生成字幕")
            QMessageBox.warning(self, "转录失败", "转录过程未生成有效字幕，请检查视频文件。", 
                                QMessageBox.StandardButton.Ok)
                                
    def on_transcribe_result(self, subtitles, words_timestamps):
        """单个视频转录结果处理"""
        if subtitles:
            self.logger.info(f"转录完成，得到 {len(subtitles)} 条字幕")
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
                                
    def on_transcribe_error(self, error):
        """单个视频转录错误处理"""
        self.logger.error(f"转录错误: {error}")
        QMessageBox.critical(self, "转录错误", f"转录过程发生错误：{error}", 
                            QMessageBox.StandardButton.Ok)
        self.statusBar().showMessage("转录失败")
        
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()

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

    def save_subtitles(self, subtitles,words_timestamps):
        """保存字幕到srt文件"""
        if not self.media_path or not subtitles:
            return
            
        # 创建srt目录
        srt_dir = os.path.join(os.path.dirname(self.media_path), 'srt')
        os.makedirs(srt_dir, exist_ok=True)
        
        # 生成srt文件名
        video_name = os.path.splitext(os.path.basename(self.media_path))[0]
        srt_path = os.path.join(srt_dir, f"{video_name}.srt")
        
        # 写入srt文件
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, subtitle in enumerate(subtitles, 1):
                start_time = self.format_srt_time(subtitle['start_time'])
                end_time = self.format_srt_time(subtitle['end_time'])
                f.write(f"{i}\n{start_time} --> {end_time}\n{subtitle['text']}\n\n")
        self.logger.info(f"字幕已保存到: {srt_path}")

        words_path = os.path.join(srt_dir, f"{video_name}.words.json")
        with open(words_path, 'w', encoding='utf-8') as f:
            json.dump(self.words_timestamps, f, ensure_ascii=False, indent=2)
        self.logger.info(f"逐字稿已保存到: {words_path}")
        
        
    def format_srt_time(self, milliseconds):
        """格式化时间为srt格式 (HH:MM:SS,mmm)"""
        seconds = milliseconds // 1000
        ms = milliseconds % 1000
        minutes = seconds // 60
        seconds = seconds % 60
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

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
        """导入视频文件（支持多选）"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.flv);;所有文件 (*.*)"
        )
        
        if file_paths:
            self.logger.info(f"导入视频: {len(file_paths)} 个文件")
            
            # 清空当前队列和列表
            self.batch_queue.clear_queue()
            self.video_list.clear()
            
            # 添加视频到队列和列表
            self.batch_queue.add_videos(file_paths)
            for path in file_paths:
                self.video_list.addItem(os.path.basename(path))
            
            # 加载第一个视频到播放器
            if file_paths:
                self.media_path = file_paths[0]
                self.video_player.set_media(file_paths[0])
                
            self.statusBar().showMessage(f"已导入 {len(file_paths)} 个视频")
            

    def transcribe_video(self):
        """转录单个视频"""
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
        self.transcribe_thread.progress_signal.connect(self.on_asr_progress)
        self.transcribe_thread.result_signal.connect(self.on_transcribe_result)
        self.transcribe_thread.error_signal.connect(self.on_transcribe_error)
        self.transcribe_thread.start()
        
    def batch_transcribe_videos(self):
        """批量转录视频"""
        # 检查队列是否为空
        if not self.batch_queue.video_queue:
            QMessageBox.warning(self, "提示", "批量转录队列为空，请先批量导入视频", 
                                QMessageBox.StandardButton.Ok)
            return
        
        # 检查ASR模型是否加载完成
        if not self.asr_loaded or not self.asr:
            QMessageBox.warning(self, "提示", "AI引擎尚未加载完成，请稍候", 
                                QMessageBox.StandardButton.Ok)
            return
        
        # 连接批量转录队列的信号
        self.batch_queue.queue_progress_signal.connect(self.on_batch_progress)
        self.batch_queue.queue_completed_signal.connect(self.on_batch_completed)
        self.batch_queue.video_start_signal.connect(self.on_batch_video_start)
        self.batch_queue.video_completed_signal.connect(self.on_batch_video_completed)
        
        # 显示进度对话框
        self.show_progress_dialog("批量转录", "正在准备批量转录...")
        
        # 开始批量转录
        self.batch_queue.start_processing(self.asr)
        
    def on_batch_progress(self, current_index, total_count):
        """批量转录进度更新"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            progress = int((current_index / total_count) * 100)
            self.progress_dialog.set_progress(progress, f"正在处理第 {current_index}/{total_count} 个视频")
            self.statusBar().showMessage(f"批量转录进度: {current_index}/{total_count}")
            
    def on_batch_video_start(self, video_path):
        """批量转录开始处理某个视频"""
        self.logger.info(f"开始处理视频: {video_path}")
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.set_message(f"正在转录: {os.path.basename(video_path)}")
        
        # 设置当前视频到播放器
        self.media_path = video_path
        self.video_player.set_media(video_path)
        
        # 创建并启动转录线程
        self.transcribe_thread = ASRTranscribeThread(self.asr, video_path)
        self.transcribe_thread.progress_signal.connect(self.on_asr_progress)
        self.transcribe_thread.result_signal.connect(lambda subtitles, words_timestamps: 
                                                  self.on_batch_transcribe_result(video_path, subtitles, words_timestamps))
        self.transcribe_thread.error_signal.connect(lambda error: 
                                                self.on_batch_transcribe_error(video_path, error))
        self.transcribe_thread.start()
        
    def on_batch_video_completed(self, video_path):
        """批量转录某个视频完成"""
        self.logger.info(f"视频处理完成: {video_path}")
        
    def on_batch_completed(self):
        """批量转录全部完成"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            
        # 获取所有结果
        results = self.batch_queue.get_results()
        
        QMessageBox.information(
            self, 
            "批量转录完成", 
            f"批量转录已完成，共处理 {len(results)} 个视频。", 
            QMessageBox.StandardButton.Ok
        )
        
        self.statusBar().showMessage(f"批量转录完成，共处理 {len(results)} 个视频")
        
    def on_batch_transcribe_result(self, video_path, subtitles, words_timestamps):
        """批量转录单个视频结果处理"""
        self.logger.info(f"视频 {video_path} 转录完成，得到 {len(subtitles)} 条字幕")
        
        # 通知批量队列管理器该视频已处理完成
        self.batch_queue.on_video_transcribed(video_path, subtitles, words_timestamps)
        
        # 如果是当前显示的视频，更新UI
        if self.media_path == video_path:
            self.subtitles = subtitles
            self.words_timestamps = words_timestamps
            self.update_subtitle_list()
            
    def on_batch_transcribe_error(self, video_path, error):
        """批量转录单个视频错误处理"""
        self.logger.error(f"视频 {video_path} 转录失败: {error}")
        
        # 显示错误但继续处理队列
        QMessageBox.warning(
            self, 
            "视频转录失败", 
            f"视频 {os.path.basename(video_path)} 转录失败: {error}\n\n将继续处理队列中的其他视频。", 
            QMessageBox.StandardButton.Ok
        )
        
        # 通知批量队列管理器该视频已处理完成（虽然失败）
        self.batch_queue.on_video_transcribed(video_path, [], [])

    def update_subtitle_list(self, filter_text=""):
        """更新字幕列表"""
        self.subtitle_list.clear()
  
        # 如果内存中没有字幕，尝试从srt文件加载
        if not self.subtitles:
            srt_dir = os.path.join(os.path.dirname(self.media_path), 'srt')
            video_name = os.path.splitext(os.path.basename(self.media_path))[0]
            srt_path = os.path.join(srt_dir, f"{video_name}.srt")
            if os.path.exists(srt_path):
                self.load_srt_file(srt_path)
                self.logger.info(f"从文件加载字幕: {srt_path}")
        
        if not self.subtitles:
            return
            
        for subtitle in self.subtitles:
            text = subtitle.get('text', '')
            start_time = subtitle.get('start_time', 0)
            end_time = subtitle.get('end_time', 0)
            
            # 如果有过滤文本，检查字幕文本是否包含过滤文本
            if filter_text and filter_text.lower() not in text.lower():
                continue
            
            start_str = self.format_time(start_time)
            end_str = self.format_time(end_time)
            
            item_text = f"[{start_str} - {end_str}] {text}"
            self.subtitle_list.addItem(item_text)
        
        self.logger.info(f"字幕列表更新完成，显示 {self.subtitle_list.count()} 条")
        
    def load_srt_file(self, srt_path):
        """从srt文件加载字幕"""
        import pysrt
        subs = pysrt.open(srt_path, encoding='utf-8')
        
        subtitles = []
        for sub in subs:
            # 转换时间为毫秒
            start_time = (sub.start.hours * 3600 + sub.start.minutes * 60 + 
                        sub.start.seconds) * 1000 + sub.start.milliseconds
            end_time = (sub.end.hours * 3600 + sub.end.minutes * 60 + 
                        sub.end.seconds) * 1000 + sub.end.milliseconds
            
            subtitles.append({
                'text': sub.text,
                'start_time': start_time,
                'end_time': end_time
            })
        self.subtitles = subtitles
        self.logger.info(f"成功加载字幕文件: {srt_path}")

        # 尝试加载逐字稿
        words_path = os.path.join(os.path.dirname(srt_path), f"{os.path.splitext(os.path.basename(srt_path))[0]}.words.json")
        if os.path.exists(words_path):
            with open(words_path, 'r', encoding='utf-8') as f:
                self.words_timestamps = json.load(f)
            self.logger.info(f"成功加载逐字稿: {words_path}")
        else:
            self.logger.warning(f"未找到逐字稿文件: {words_path}")
            self.words_timestamps = None
        
        self.logger.info(f"成功加载字幕文件: {srt_path}")
        
            
    def parse_srt_time(self, time_str):
        """解析srt时间格式为毫秒"""
        time_parts = time_str.replace(',', ':').split(':')
        if len(time_parts) == 4:
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = int(time_parts[2])
            milliseconds = int(time_parts[3])
            return hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds
        return 0

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
         
        # 清空现有布局中的所有部件
        while self.text_edit_tab_layout.count():
            item = self.text_edit_tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 如果是布局，也需要清空
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                        
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



    def on_video_list_double_clicked(self, item):
        """视频列表双击事件处理"""
        index = self.video_list.row(item)
        video_paths = self.batch_queue.get_video_paths()
        if 0 <= index < len(video_paths):
            self.media_path = video_paths[index]
            self.video_player.set_media(video_paths[index])
            # 加载该视频的字幕（如果有）
            self.update_subtitle_list()
            self.video_player.play()  # 自动开始播放
            
    def show_video_context_menu(self, position):
        """显示视频右键菜单"""
        menu = QMenu()
        transcribe_action = menu.addAction("转录字幕")
        remove_action = menu.addAction("移除视频")

        # 获取当前选中的项
        item = self.video_list.itemAt(position)
        if item:
            action = menu.exec(self.video_list.mapToGlobal(position))
            if action == transcribe_action:
                index = self.video_list.row(item)
                video_paths = self.batch_queue.get_video_paths()
                if 0 <= index < len(video_paths):
                    self.media_path = video_paths[index]
                    self.video_player.set_media(video_paths[index])
                    self.transcribe_video()
            elif action == remove_action:
                index = self.video_list.row(item)
                # 从队列和列表中移除视频
                self.batch_queue.remove_video(index)
                self.video_list.takeItem(index)
                
                # 如果移除的是当前播放的视频，清空播放器
                if self.media_path == self.batch_queue.get_video_paths()[index]:
                    self.media_path = None
                    self.video_player.stop()
                    self.subtitles = None
                    self.words_timestamps = None
                    self.update_subtitle_list()