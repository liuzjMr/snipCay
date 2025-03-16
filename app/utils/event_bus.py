from typing import Callable, Dict, List
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """事件总线，用于组件间通信"""
    
    # 定义信号
    event_signal = pyqtSignal(str, object)
    
    def __init__(self):
        super().__init__()
        self._handlers: Dict[str, List[Callable]] = {}
        self.event_signal.connect(self._dispatch_event)
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """取消订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    def publish(self, event_type: str, data: object = None) -> None:
        """发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        self.event_signal.emit(event_type, data)
    
    def _dispatch_event(self, event_type: str, data: object) -> None:
        """分发事件到对应的处理函数
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(data)

# 创建全局事件总线实例
event_bus = EventBus()