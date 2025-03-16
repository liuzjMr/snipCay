from pathlib import Path

class Config:
    """应用配置类"""
    
    # 项目根目录
    ROOT_DIR = Path(__file__).parent.parent
    
    # ASR模型配置
    ASR_MODEL = {
        "model": "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "vad_model": "damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "punc_model": "damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "spk_model": "damo/speech_campplus_sv_zh-cn_16k-common"
    }
    
    # 模型缓存目录
    MODEL_CACHE_DIR = "funasr_model"
    
    # 视频播放器配置
    VIDEO_PLAYER = {
        "min_width": 640,
        "min_height": 360
    }
    
    # 主窗口配置
    MAIN_WINDOW = {
        "title": "视频字幕剪辑工具",
        "width": 1200,
        "height": 700
    }
    
    # 日志配置
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "filename": "app.log",
                "maxBytes": 10485760,
                "backupCount": 3
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": True
            }
        }
    }