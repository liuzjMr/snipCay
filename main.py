#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
# 删除或修正错误的导入
# from subtitle_editor import SubtitleEditor  # 这行导致错误

from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()