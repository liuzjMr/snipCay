#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow


def main():
    """
    应用程序入口
    """
    app = QApplication(sys.argv)
    app.setApplicationName("SubtitleCut")
    app.setOrganizationName("SubtitleCut")
    
    # 设置样式表
    with open("app/resources/style.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 