from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar

class ProgressDialog(QDialog):
    """进度对话框组件"""
    
    def __init__(self, parent=None, title="处理中", message="请稍候..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(300, 100)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 添加标签和进度条
        self.label = QLabel(message)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度模式
        
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
    
    def set_message(self, message):
        """更新进度信息"""
        self.label.setText(message)
    
    def set_progress(self, value, maximum=100):
        """设置进度值"""
        # 确保value和maximum都是整数类型
        try:
            value = int(value)
            maximum = int(maximum) if isinstance(maximum, (int, float, str)) else 100
        except (ValueError, TypeError):
            value = 0
            maximum = 100
            
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)