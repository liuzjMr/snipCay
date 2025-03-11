#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import time
from pathlib import Path
import wave
import json
from datetime import datetime
import torch
from funasr import AutoModel

class ASRProcessor:
    """语音识别处理类 - 基于FunASR的自动语音识别"""
    
    def __init__(self):
        """初始化ASR处理器"""
        # 初始化配置
        self.temp_dir = tempfile.gettempdir()
        os.makedirs(os.path.join(self.temp_dir, "subtitlecut"), exist_ok=True)
        
        # 设置模型缓存目录
        os.environ["MODELSCOPE_CACHE"] = "funasr_model"
        
        # 初始化FunASR模型
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"使用设备: {device}")
        
        self.model = AutoModel(model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                  vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                  punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                  spk_model="damo/speech_campplus_sv_zh-cn_16k-common",
                  device=device
                  # spk_model="cam++", spk_model_revision="v2.0.2",
                  )
        print("ASR模型已加载")
        
   
    def process_funasr_result(self, result):
        """处理FunASR识别结果，解析为字幕列表和文字时间戳"""
        print("===== 开始解析FunASR结果 =====")
        
        subtitles = []
        words_timestamps = []
        
        
        result = result[0]  # 使用列表中的第一个字典
        # 查找sentence_info字段（包含句子级别的识别结果）
        sentences = result['sentence_info']
        print(f"找到 sentence_info，包含 {len(sentences)} 条句子信息")
        for i, sentence in enumerate(sentences):
            # 提取每个句子的信息
            text = sentence.get('text', '').strip()
            start_time = sentence.get('start_time', 0)
            end_time = sentence.get('end_time', 0)
            subtitle = {
                'id': i + 1,
                'start_time': start_time,
                'end_time': end_time,
                'text': text
            }
            
            subtitles.append(subtitle)
        
        # 解析每个文字的时间戳
        raw_text = result['raw_text']
        timestamps = result['timestamp']
        raw_texts = raw_text.split(' ')
        # 确保文本和时间戳数量一致
        if len(raw_texts) != len(timestamps):
            print(f"警告: 文字数量({len(raw_texts)})与时间戳数量({len(timestamps)})不匹配")
            # 使用较短的长度
            length = min(len(raw_texts), len(timestamps))
            raw_texts = raw_texts[:length]
            timestamps = timestamps[:length]
        
        for (text, ts) in zip(raw_texts, timestamps):
            # 处理不同格式的时间戳
            word_timestamp = {
                "word": text,
                "start": ts[0],
                "end": ts[1]
            }
            words_timestamps.append(word_timestamp)
        print(f"解析完成，共提取 {len(subtitles)} 条字幕")
        return subtitles, words_timestamps
            
    
    def transcribe(self, media_path):
        """转录语音为字幕"""
        try:
            # 设置模型路径和参数
            if not os.path.exists(media_path):
                raise FileNotFoundError(f"媒体文件不存在: {media_path}")
            
            print("开始转录...")
            
            # 调用FunASR进行识别 - 注意使用self.model
            result = self.model.generate(input=media_path,
                     batch_size_s=300,
                     return_spk_res=True,
                     return_raw_text=True,
                     is_final=True,
                     hotword='魔搭')
            
            # 保存原始结果（用于调试）
            if isinstance(result, list) or isinstance(result, dict):
                with open("funasr_raw_result.json", "w", encoding="utf-8") as f:
                    import json
                    json.dump(result, f, ensure_ascii=False, indent=2)
                    print("原始结果已保存到 funasr_raw_result.json")
            
            # 处理结果为字幕格式和文字时间戳
            subtitles, words_timestamps = self.process_funasr_result(result)
            
            # 返回字幕列表和文字时间戳
            return subtitles, words_timestamps
            
        except Exception as e:
            print(f"转录出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return [], []
    
    def convert_to_srt(self, subtitles, output_path):
        """
        将字幕转换为SRT格式并保存
        
        Args:
            subtitles (list): 字幕列表
            output_path (str): 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles):
                start_time_str = self.ms_to_srt_time(sub["start_time"])
                end_time_str = self.ms_to_srt_time(sub["end_time"])
                
                f.write(f"{i+1}\n")
                f.write(f"{start_time_str} --> {end_time_str}\n")
                f.write(f"{sub['text']}\n\n")
                
        print(f"SRT文件已保存: {output_path}")
    
    def ms_to_srt_time(self, ms):
        """将毫秒转换为SRT时间格式 (00:00:00,000)"""
        s, ms = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        
    def cleanup(self):
        """清理临时文件"""
        temp_dir = os.path.join(self.temp_dir, "subtitlecut")
        for file in os.listdir(temp_dir):
            if file.startswith("extracted_audio"):
                os.remove(os.path.join(temp_dir, file))
