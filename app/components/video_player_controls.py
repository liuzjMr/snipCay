from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class VideoPlayerControls(QWidget):
    """视频播放器控制组件"""
    
    # 定义信号
    position_changed = pyqtSignal(int)  # 进度条位置改变信号
    volume_changed = pyqtSignal(int)    # 音量改变信号
    play_clicked = pyqtSignal()         # 播放按钮点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局"""
        # 创建主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # 播放/暂停按钮
        self.play_button = QPushButton("播放")
        self.play_button.setMinimumWidth(80)
        self.play_button.clicked.connect(self.play_clicked.emit)
        layout.addWidget(self.play_button)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.valueChanged.connect(self.position_changed.emit)
        layout.addWidget(self.progress_slider)
        
        # 音量控制
        volume_label = QLabel("音量")
        layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        layout.addWidget(self.volume_slider)
        
    def update_play_button_state(self, is_playing):
        """更新播放按钮状态"""
        self.play_button.setText("暂停" if is_playing else "播放")
        
    def update_progress(self, position, duration):
        """更新进度条位置"""
        if duration > 0:
            value = int((position / duration) * 1000)
            self.progress_slider.setValue(value)
            
    def get_progress_value(self):
        """获取进度条当前值"""
        return self.progress_slider.value()
        
    def get_volume_value(self):
        """获取音量值"""
        return self.volume_slider.value()