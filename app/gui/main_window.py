from PyQt6.QtWidgets import QProgressDialog, QLabel, QProgressBar, QWidget, QFrame, QVBoxLayout, QMainWindow, QStatusBar, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QEvent, QTimer, QColor
from app.gui.threads import TranscribeThread
from app.gui.asr_thread import ASRModelLoaderThread, ASRTranscribeThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... 其他初始化代码 ...
        
        # ASR模型相关
        self.asr_model = None
        self.model_loading = False
        self.model_loader_thread = None
        self.transcribe_thread = None
        
        # 在初始化时添加状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # ... 其他初始化代码 ...
        
        # 设置字幕列表
        self.setup_subtitle_list()
    
    def transcribe_video(self):
        """处理视频转录"""
        if not self.current_media:
            self.show_message("请先选择媒体文件", "警告")
            return
        
        # 禁用界面上的按钮，防止重复点击
        self.transcribe_button.setEnabled(False)
        self.import_video_button.setEnabled(False)
        
        # 如果模型未加载，先加载模型
        if self.asr_model is None:
            if self.model_loading:
                self.show_message("模型加载中，请稍候...", "提示")
                return
                
            self.model_loading = True
            self.show_loading_indicator("加载语音识别模型...")
            
            # 创建并启动模型加载线程
            self.model_loader_thread = ASRModelLoaderThread()
            self.model_loader_thread.progress_signal.connect(self.update_model_progress)
            self.model_loader_thread.model_ready_signal.connect(self.model_loaded)
            self.model_loader_thread.error_signal.connect(self.model_load_error)
            self.model_loader_thread.finished.connect(self.model_load_finished)
            self.model_loader_thread.start()
            
        else:
            # 模型已加载，直接开始转录
            self.start_transcribe()
    
    def update_model_progress(self, progress, message):
        """更新模型加载进度"""
        if hasattr(self, 'loading_progress') and self.loading_progress:
            self.loading_progress.setValue(progress)
            
        if hasattr(self, 'loading_label') and self.loading_label:
            self.loading_label.setText(message)
            
        self.statusBar.showMessage(message)
    
    def model_loaded(self, model):
        """模型加载完成的处理"""
        self.asr_model = model
        self.model_loading = False
        
        # 隐藏加载指示器
        self.hide_loading_indicator()
        
        # 开始转录
        self.start_transcribe()
    
    def model_load_error(self, error_message):
        """模型加载错误的处理"""
        self.model_loading = False
        self.hide_loading_indicator()
        self.enable_ui_elements()
        self.show_message(error_message, "错误")
    
    def model_load_finished(self):
        """模型加载线程完成的处理"""
        if not self.asr_model and not self.model_loading:
            self.enable_ui_elements()
    
    def start_transcribe(self):
        """开始转录过程"""
        # 显示加载指示器
        self.show_loading_indicator("转录音频...")
        
        # 创建并启动转录线程
        self.transcribe_thread = ASRTranscribeThread(self.asr_model, self.current_media)
        self.transcribe_thread.progress_signal.connect(self.update_model_progress)
        self.transcribe_thread.result_signal.connect(self.handle_transcribe_result)
        self.transcribe_thread.error_signal.connect(self.handle_transcribe_error)
        self.transcribe_thread.finished.connect(self.transcribe_finished)
        self.transcribe_thread.start()
    
    def handle_transcribe_result(self, subtitles):
        """处理转录结果"""
        # 保存字幕数据
        self.subtitles = subtitles
        
        # 更新字幕列表和文本编辑器
        self.update_subtitle_list()
        self.update_text_editor()
        
        # 显示成功消息
        self.show_message(f"转录完成，共 {len(subtitles)} 条字幕", "成功")
    
    def handle_transcribe_error(self, error_message):
        """处理转录错误"""
        # 显示错误消息
        self.show_message(error_message, "错误")
    
    def transcribe_finished(self):
        """转录线程完成后的处理"""
        # 隐藏加载指示器
        self.hide_loading_indicator()
        
        # 重新启用界面元素
        self.enable_ui_elements()
        
        # 更新状态栏
        self.statusBar.showMessage("转录完成")

    def show_loading_indicator(self, message="处理中..."):
        """显示加载指示器"""
        # 创建半透明背景
        self.loading_overlay = QWidget(self)
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 50);")
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.show()
        
        # 创建加载框
        self.loading_frame = QFrame(self.loading_overlay)
        self.loading_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #cccccc;
            }
        """)
        self.loading_frame.setFixedSize(300, 150)
        
        # 居中显示
        center_point = self.loading_overlay.rect().center()
        self.loading_frame.move(center_point.x() - self.loading_frame.width() // 2,
                               center_point.y() - self.loading_frame.height() // 2)
        self.loading_frame.show()
        
        # 创建垂直布局
        layout = QVBoxLayout(self.loading_frame)
        
        # 添加加载标签
        self.loading_label = QLabel(message)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 14px; color: #333333; background-color: transparent;")
        layout.addWidget(self.loading_label)
        
        # 添加进度条
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 100)
        self.loading_progress.setValue(0)
        self.loading_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4a86e8;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.loading_progress)

    def hide_loading_indicator(self):
        """隐藏加载指示器"""
        if hasattr(self, 'loading_overlay') and self.loading_overlay:
            self.loading_overlay.hide()
            self.loading_overlay.deleteLater()
        
    def enable_ui_elements(self):
        """重新启用界面元素"""
        self.transcribe_button.setEnabled(True)
        self.import_video_button.setEnabled(True)

    def update_subtitle_list(self):
        """更新字幕列表显示"""
        if not hasattr(self, 'subtitles') or not self.subtitles:
            return
        
        # 清空当前列表
        self.subtitle_list.clear()
        
        # 添加字幕项
        for subtitle in self.subtitles:
            # 转换时间为可读格式
            start_time = subtitle["start_time"]
            end_time = subtitle["end_time"]
            start_time_str = self.format_time(start_time)
            end_time_str = self.format_time(end_time)
            
            # 创建列表项
            text = subtitle["text"].strip()
            item_text = f"{start_time_str} - {end_time_str}\n{text}"
            
            item = QListWidgetItem(item_text)
            # 存储时间信息用于跳转
            item.setData(Qt.ItemDataRole.UserRole, {
                "start_time": start_time,
                "end_time": end_time
            })
            
            self.subtitle_list.addItem(item)
        
        # 设置列表项样式
        self.subtitle_list.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f0f7ff;
            }
        """)

    def setup_subtitle_list(self):
        """设置字幕列表控件"""
        self.subtitle_list = QListWidget()
        self.subtitle_list.setWordWrap(True)  # 允许文本换行
        self.subtitle_list.setSpacing(2)      # 设置项目间距
        
        # 连接点击事件
        self.subtitle_list.itemClicked.connect(self.on_subtitle_clicked)
        
        # 添加到布局
        self.right_layout.addWidget(self.subtitle_list)
        
        # 创建定时器用于更新当前字幕
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)  # 每100ms更新一次
        self.update_timer.timeout.connect(self.update_current_subtitle)
        self.update_timer.start()

    def update_current_subtitle(self):
        """更新当前播放的字幕高亮显示"""
        if not hasattr(self, 'video_player') or not hasattr(self, 'subtitles'):
            return
        
        current_position = self.video_player.get_position()
        
        # 查找当前时间对应的字幕
        current_index = -1
        for i, subtitle in enumerate(self.subtitles):
            if subtitle["start_time"] <= current_position <= subtitle["end_time"]:
                current_index = i
                break
        
        # 更新高亮显示
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            if i == current_index:
                item.setBackground(QColor("#e3f2fd"))
                self.subtitle_list.scrollToItem(item)  # 自动滚动到当前字幕
            else:
                item.setBackground(QColor("transparent"))

    def on_subtitle_clicked(self, item):
        """处理字幕项点击事件"""
        # 获取时间信息
        time_data = item.data(Qt.ItemDataRole.UserRole)
        if time_data and self.video_player:
            # 跳转到对应时间点
            start_time = time_data["start_time"]
            self.video_player.seek(start_time)
            # 自动开始播放
            self.video_player.play()
            
            # 高亮显示当前项
            for i in range(self.subtitle_list.count()):
                self.subtitle_list.item(i).setBackground(QColor("transparent"))
            item.setBackground(QColor("#e3f2fd"))

    def format_time(self, ms):
        """将毫秒转换为可读时间格式"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        seconds %= 60
        minutes %= 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def update_text_editor(self):
        """更新文本编辑器显示"""
        if not hasattr(self, 'subtitles') or not self.subtitles:
            return
        
        # 准备完整文本
        full_text = ""
        
        # 使用HTML格式显示文本，便于未来扩展样式
        html_text = "<html><body style='font-family: Arial; font-size: 14px;'>"
        
        for subtitle in self.subtitles:
            # 添加带时间标记的段落
            start_time_str = self.format_time(subtitle["start_time"])
            text = subtitle["text"]
            
            # 创建可点击的段落
            paragraph = f"""
            <p>
                <span style='color: #666; font-size: 12px;'>[{start_time_str}]</span> 
                <span class='subtitle-text' data-start='{subtitle["start_time"]}'>{text}</span>
            </p>
            """
            html_text += paragraph
            
            # 同时构建纯文本
            full_text += text + "\n"
        
        html_text += "</body></html>"
        
        # 设置HTML内容
        self.text_editor.setHtml(html_text)
        
        # 存储纯文本版本，便于编辑
        self.full_text = full_text

    def setup_connections(self):
        """设置信号连接"""
        # 原有的连接...
        
        # 字幕列表点击
        self.subtitle_list.itemClicked.connect(self.subtitle_item_clicked)
        
        # 文本编辑器事件过滤器
        self.text_editor.installEventFilter(self)
    
    def subtitle_item_clicked(self, item):
        """处理字幕项点击"""
        # 获取字幕数据
        subtitle = item.data(Qt.ItemDataRole.UserRole)
        if not subtitle:
            return
        
        # 跳转到对应时间
        if hasattr(self, 'video_player') and self.video_player:
            position = subtitle["start_time"]
            self.video_player.setPosition(position)
            
            # 如果视频暂停中，自动开始播放
            if self.video_player.state() != self.video_player.PlayingState:
                self.video_player.play()
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理文本编辑器点击"""
        if obj == self.text_editor and event.type() == QEvent.Type.MouseButtonPress:
            # 获取光标位置
            cursor = self.text_editor.cursorForPosition(event.pos())
            
            # 获取当前HTML位置
            frame = cursor.currentFrame()
            if not frame:
                return super().eventFilter(obj, event)
            
            # 检查是否点击了字幕文本
            element = cursor.charFormat().anchorHref()
            if element and element.startswith('time:'):
                # 提取时间
                try:
                    time_ms = int(element.split(':')[1])
                    # 跳转到对应时间
                    if hasattr(self, 'video_player') and self.video_player:
                        self.video_player.setPosition(time_ms)
                        
                        # 如果视频暂停中，自动开始播放
                        if self.video_player.state() != self.video_player.PlayingState:
                            self.video_player.play()
                except:
                    pass
        
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """窗口关闭时的处理"""
        # 停止更新定时器
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        super().closeEvent(event) 