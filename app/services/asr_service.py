#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import traceback
import torch
from funasr import AutoModel
from pathlib import Path
from ..config import Config
from ..utils.logger import logger
from ..utils.event_bus import event_bus

class ASRService:
    """语音识别服务 - 基于FunASR的自动语音识别"""
    
    def __init__(self):
        """初始化ASR服务"""
        # 初始化配置
        self.temp_dir = tempfile.gettempdir()
        
        # 设置模型缓存目录
        os.environ["MODELSCOPE_CACHE"] = Config.MODEL_CACHE_DIR
        
        # 初始化FunASR模型
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"使用设备: {device}")
        
        self.model = AutoModel(
            model=Config.ASR_MODEL["model"],
            vad_model=Config.ASR_MODEL["vad_model"],
            punc_model=Config.ASR_MODEL["punc_model"],
            spk_model=Config.ASR_MODEL["spk_model"],
            device=device
        )
        logger.info("ASR模型已加载")
        event_bus.publish('asr_model_loaded',self)
        
    def process_funasr_result(self, result):
        """处理FunASR识别结果，解析为字幕列表和文字时间戳"""
        logger.info("===== 开始解析FunASR结果 =====")
        
        subtitles = []
        words_timestamps = []
        
        result = result[0]  # 使用列表中的第一个字典
        # 查找sentence_info字段（包含句子级别的识别结果）
        sentences = result['sentence_info']
        logger.info(f"找到 sentence_info，包含 {len(sentences)} 条句子信息")
        
        for i, sentence in enumerate(sentences):
            # 提取每个句子的信息
            text = sentence.get('text', '').strip()
            start_time = sentence.get('start', 0)
            end_time = sentence.get('end', 0)
            subtitle = {
                'id': i + 1,
                'start_time': start_time,
                'end_time': end_time,
                'text': text
            }
            subtitles.append(subtitle)
            
            # 发布字幕进度事件
            progress = (i + 1) / len(sentences)
            event_bus.publish('asr_progress', {
                'progress': progress,
                'current_subtitle': subtitle
            })
            
            for t, times in zip(sentence['raw_text'], sentence['timestamp']):
                if words_timestamps:
                    last_timestamp = words_timestamps[-1]
                    last_end = last_timestamp['end']
                    # 超过100ms，添加一个新的时间戳
                    if times[0] - last_end > 100:
                        word_timestamp = {
                            "word": ' ',
                            "start": last_timestamp['end'],
                            "end": times[0]
                        }
                        words_timestamps.append(word_timestamp)
                word_timestamp = {
                    "word": t,
                    "start": times[0],
                    "end": times[1]
                }
                words_timestamps.append(word_timestamp)

        logger.info(f"解析完成，共提取 {len(subtitles)} 条字幕")
        return subtitles, words_timestamps
            
    def transcribe(self, media_path):
        """转录语音为字幕"""
        try:
            # 设置模型路径和参数
            if not os.path.exists(media_path):
                raise FileNotFoundError(f"媒体文件不存在: {media_path}")
            
            logger.info("开始转录...")
            event_bus.publish('asr_start', {'media_path': media_path})
            
            # 调用FunASR进行识别
            result = self.model.generate(
                input=media_path,
                batch_size_s=300,
                return_spk_res=True,
                return_raw_text=True,
                is_final=True,
                hotword='魔搭'
            )
            
            # 保存原始结果（用于调试）
            if isinstance(result, list) or isinstance(result, dict):
                with open("funasr_raw_result.json", "w", encoding="utf-8") as f:
                    import json
                    json.dump(result, f, ensure_ascii=False, indent=2)
                    logger.debug("原始结果已保存到 funasr_raw_result.json")
            
            # 处理结果为字幕格式和文字时间戳
            subtitles, words_timestamps = self.process_funasr_result(result)
            
            # 自动保存SRT文件到视频文件所在目录下的srt子目录中
            if subtitles and len(subtitles) > 0:
                # 获取视频文件所在目录
                video_dir = os.path.dirname(media_path)
                # 创建srt子目录
                srt_dir = os.path.join(video_dir, "srt")
                os.makedirs(srt_dir, exist_ok=True)
                # 获取视频文件名（不含扩展名）
                video_name = os.path.splitext(os.path.basename(media_path))[0]
                # 构建SRT文件路径
                srt_path = os.path.join(srt_dir, f"{video_name}.srt")
                # 保存SRT文件
                self.convert_to_srt(subtitles, srt_path)
                logger.info(f"已自动保存SRT文件到: {srt_path}")
            
            # 发布转录完成事件
            event_bus.publish('asr_result', {
                'subtitles': subtitles,
                'words_timestamps': words_timestamps
            })
            
            # 发布转录完成事件
            event_bus.publish('asr_complete', {
                'subtitles': subtitles,
                'words_timestamps': words_timestamps
            })
            
            # 返回字幕列表和文字时间戳
            return subtitles, words_timestamps
            
        except Exception as e:
            error_info = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            event_bus.publish('asr_error', error_info)
            logger.error(f"转录出错: {str(e)}")
            logger.error(traceback.format_exc())
            return [], []
    
    def convert_to_srt(self, subtitles, output_path):
        """将字幕转换为SRT格式并保存"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles):
                start_time_str = self.ms_to_srt_time(sub["start_time"])
                end_time_str = self.ms_to_srt_time(sub["end_time"])
                
                # SRT格式：序号、时间码、文本内容，每个字幕条目之间用空行分隔
                f.write(f"{i+1}\n")
                f.write(f"{start_time_str} --> {end_time_str}\n")
                f.write(f"{sub['text']}\n\n")
                
        logger.info(f"SRT文件已保存: {output_path}")
        event_bus.publish('srt_saved', {'output_path': output_path})
    
    def ms_to_srt_time(self, ms):
        """将毫秒转换为SRT时间格式 (00:00:00,000)"""
        s, ms = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"