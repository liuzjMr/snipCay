import logging
from pathlib import Path
from logging.config import dictConfig
from ..config import Config

def setup_logger(name: str = __name__) -> logging.Logger:
    """配置日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    # 确保日志目录存在
    log_dir = Config.ROOT_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # 更新日志文件路径
    logging_config = Config.LOGGING.copy()
    logging_config['handlers']['file']['filename'] = str(log_dir / 'app.log')
    
    # 应用日志配置
    dictConfig(logging_config)
    
    # 获取日志记录器
    return logging.getLogger(name)

# 创建全局日志记录器
logger = setup_logger('snipCay')