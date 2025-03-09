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
        
        self.model = AutoModel(
            model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
            spk_model="damo/speech_campplus_sv_zh-cn_16k-common",
            device=device
        )
        print("ASR模型已加载")
        
    def extract_audio(self, video_path):
        """
        从视频文件中提取音频，使用moviepy库
        
        Args:
            video_path (str): 视频文件路径
            
        Returns:
            str: 提取的音频文件路径
        """
        # 使用临时文件
        audio_path = os.path.join(self.temp_dir, "subtitlecut", "extracted_audio.wav")
        
        print(f"从视频中提取音频: {video_path}")
        
        # 使用moviepy库提取音频
        try:
            from moviepy.editor import VideoFileClip
            
            print("使用moviepy提取音频...")
            video_clip = VideoFileClip(video_path)
            audio_clip = video_clip.audio
            
            # 设置音频参数 (16kHz, 单声道)
            audio_clip.write_audiofile(
                audio_path,
                fps=16000,  # 采样率设为16kHz
                nbytes=2,   # 16位PCM
                codec='pcm_s16le',
                ffmpeg_params=["-ac", "1"]  # 单声道
            )
            
            # 关闭剪辑对象释放资源
            audio_clip.close()
            video_clip.close()
            
            print(f"音频已提取: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"moviepy提取音频失败: {str(e)}")
            
            # 尝试使用pydub作为备选方案
            try:
                from pydub import AudioSegment
                
                print("尝试使用pydub提取音频...")
                # 读取视频中的音频
                audio = AudioSegment.from_file(video_path)
                
                # 转换为单声道、16kHz的WAV
                audio = audio.set_channels(1).set_frame_rate(16000)
                
                # 保存为WAV文件
                audio.export(audio_path, format="wav")
                
                print(f"音频已使用pydub提取: {audio_path}")
                return audio_path
                
            except Exception as e2:
                print(f"pydub提取音频失败: {str(e2)}")
                print("警告: 无法提取音频，将使用原始文件")
                return video_path
    
    def transcribe(self, media_path):
        """
        转录音频/视频文件为字幕
        
        Args:
            media_path (str): 媒体文件路径
            
        Returns:
            list: 字幕列表，每项包含id, start_time, end_time, text
        """
        # 检查文件是否存在
        if not os.path.exists(media_path):
            raise FileNotFoundError(f"文件不存在: {media_path}")
        
        print(f"开始转录: {media_path}")
        
        # 如果是视频文件，先提取音频
        _, ext = os.path.splitext(media_path.lower())
        if ext in ['.mp4', '.avi', '.mov', '.mkv']:
            audio_path = self.extract_audio(media_path)
        else:
            audio_path = media_path
        
        # 使用FunASR进行语音识别
        try:
            # 获取FunASR的原始结果
            raw_result = self.model.generate(
                input=audio_path,
                batch_size_s=300,
                return_spk_res=True,
                return_raw_text=True,
                is_final=True
            )
            
            # 详细打印原始结果，辅助调试
            print('\n========== FunASR原始结果 ==========')
            print(f'结果类型: {type(raw_result)}')
            
            if isinstance(raw_result, dict):
                print(f'字典键: {list(raw_result.keys())}')
                for key, value in raw_result.items():
                    print(f'键 "{key}" 的值类型: {type(value)}')
                    try:
                        if isinstance(value, list) and len(value) > 0:
                            print(f'  第一项类型: {type(value[0])}')
                            if isinstance(value[0], list) and len(value[0]) > 0:
                                print(f'  第一项第一元素: {value[0][0]}')
                            elif isinstance(value[0], dict):
                                print(f'  第一项键: {list(value[0].keys())}')
                    except:
                        pass
            elif isinstance(raw_result, list):
                print(f'列表长度: {len(raw_result)}')
                if len(raw_result) > 0:
                    print(f'第一项类型: {type(raw_result[0])}')
                    print(f'第一项内容: {raw_result[0]}')
            
            # 保存原始结果供后续分析
            import json
            try:
                with open('funasr_raw_result.json', 'w', encoding='utf-8') as f:
                    json.dump(raw_result, f, ensure_ascii=False, indent=2)
                print('原始结果已保存到 funasr_raw_result.json')
            except:
                print('无法保存原始结果')
            
            # 使用专门的函数处理FunASR结果
            return self.process_funasr_result(raw_result)
            
        except Exception as e:
            import traceback
            error_info = traceback.format_exc()
            print(f"转录出错: {str(e)}")
            print(f"详细错误信息: {error_info}")
            
            # 其他错误，返回简单字幕
            return [{"id": 1, "start_time": 0, "end_time": 0, "text": f"转录失败: {str(e)}"}]
    
    def process_funasr_result(self, funasr_result):
        """
        专门处理FunASR的转录结果，根据其具体格式进行解析
        
        Args:
            funasr_result: FunASR的原始转录结果
            
        Returns:
            list: 字幕列表
        """
        subtitles = []
        
        try:
            print("\n===== 开始解析FunASR结果 =====")
            
            # 检查结果是否为列表，并获取第一项
            if isinstance(funasr_result, list) and len(funasr_result) > 0:
                print(f"处理列表类型结果，使用第一项")
                result = funasr_result[0]
            else:
                print("结果不是列表类型，直接处理")
                result = funasr_result
            
            # 获取句子信息列表
            sentence_info = []
            if isinstance(result, dict):
                sentence_info = result.get('sentence_info', [])
                print(f"找到 sentence_info，包含 {len(sentence_info)} 条句子信息")
            
            # 处理每个句子
            subtitle_id = 0
            for item in sentence_info:
                # 提取文本和时间戳
                text = item.get('text', None)
                start_time = item.get('start', None)  # 注意：使用'start'而不是'start_time'
                end_time = item.get('end', None)      # 注意：使用'end'而不是'end_time'
                
                # 验证数据有效性
                if text is None or start_time is None or end_time is None:
                    print(f"跳过无效句子: text={text}, start={start_time}, end={end_time}")
                    continue
                
                # 转换时间戳为整数（如果需要）
                if not isinstance(start_time, int):
                    try:
                        start_time = int(float(start_time))
                    except:
                        start_time = 0
                
                if not isinstance(end_time, int):
                    try:
                        end_time = int(float(end_time))
                    except:
                        end_time = start_time + 1000  # 默认持续1秒
                
                # 创建字幕
                subtitle_id += 1
                subtitle = {
                    "id": subtitle_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": text.strip() if text else f"字幕 {subtitle_id}"
                }
                
                print(f"字幕 #{subtitle_id}: {text[:30]}... ({start_time}-{end_time})")
                
                # 添加到字幕列表
                subtitles.append(subtitle)
            
            # 如果没有提取到有效字幕，提供默认字幕
            if not subtitles:
                print("未找到有效字幕，使用默认字幕")
                subtitles = [{
                    "id": 1,
                    "start_time": 0,
                    "end_time": 60000,  # 60秒
                    "text": "无法解析转录结果"
                }]
            
            print(f"解析完成，共提取 {len(subtitles)} 条字幕")
            return subtitles
            
        except Exception as e:
            import traceback
            print(f"处理FunASR结果出错: {str(e)}")
            print(traceback.format_exc())
            
            # 返回错误字幕
            return [{
                "id": 1,
                "start_time": 0,
                "end_time": 0,
                "text": f"处理转录结果出错: {str(e)}"
            }]
    
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
