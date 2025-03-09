from PyQt6.QtCore import QThread, pyqtSignal
import os
import traceback

class ASRModelLoaderThread(QThread):
    """异步加载ASR模型的线程"""
    
    # 定义信号
    progress_signal = pyqtSignal(int, str)
    model_ready_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
    
    def run(self):
        """在单独线程中加载ASR模型"""
        try:
            # 报告进度
            self.progress_signal.emit(10, "初始化ASR环境...")
            
            # 导入所需模块 - 在线程中导入，避免阻塞主线程
            import torch
            from funasr import AutoModel
            
            # 设置模型缓存目录
            self.progress_signal.emit(20, "配置模型环境...")
            os.environ["MODELSCOPE_CACHE"] = "funasr_model"
            
            # 检测设备
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.progress_signal.emit(30, f"使用{device}加载模型...")
            
            # 加载模型 - 这是最耗时的操作
            self.progress_signal.emit(40, "加载语音识别模型...")
            model = AutoModel(
                model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                spk_model="damo/speech_campplus_sv_zh-cn_16k-common",
                device=device
            )
            
            self.progress_signal.emit(90, "模型加载完成!")
            
            # 发送模型对象
            self.model_ready_signal.emit(model)
            
            self.progress_signal.emit(100, "准备就绪")
            
        except Exception as e:
            # 捕获并发送错误信号
            error_details = traceback.format_exc()
            self.error_signal.emit(f"模型加载失败: {str(e)}\n\n{error_details}")

class ASRTranscribeThread(QThread):
    """使用已加载的模型进行转录的线程"""
    
    # 定义信号
    progress_signal = pyqtSignal(int, str)
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, model, media_path):
        """初始化转录线程"""
        super().__init__()
        self.model = model  # 已加载的ASR模型
        self.media_path = media_path
    
    def run(self):
        """执行转录任务"""
        try:
            # 导入所需模块
            import os
            import tempfile
            
            self.progress_signal.emit(10, "准备转录...")
            
            # 如果是视频文件，提取音频
            _, ext = os.path.splitext(self.media_path.lower())
            if ext in ['.mp4', '.avi', '.mov', '.mkv']:
                self.progress_signal.emit(20, "从视频中提取音频...")
                audio_path = self.extract_audio(self.media_path)
            else:
                audio_path = self.media_path
            
            # 开始转录
            self.progress_signal.emit(30, "开始语音识别...")
            
            # 尝试使用不同参数组合
            result = None
            success = False
            
            # 方法1: 标准参数
            try:
                self.progress_signal.emit(40, "使用标准参数转录...")
                result = self.model.generate(
                    input=audio_path,
                    batch_size_s=300,
                    return_spk_res=True,
                    return_raw_text=True,
                    is_final=True
                )
                success = True
            except Exception as e1:
                print(f"标准参数转录失败: {str(e1)}")
                
            # 方法2: 不使用标点
            if not success:
                try:
                    self.progress_signal.emit(50, "尝试不使用标点转录...")
                    result = self.model.generate(
                        input=audio_path,
                        batch_size_s=300,
                        return_spk_res=True,
                        return_raw_text=True,
                        use_punc=False,
                        is_final=True
                    )
                    success = True
                except Exception as e2:
                    print(f"无标点转录失败: {str(e2)}")
                
            # 方法3: 简化参数
            if not success:
                try:
                    self.progress_signal.emit(60, "使用简化参数转录...")
                    result = self.model.generate(
                        input=audio_path,
                        is_final=True
                    )
                    success = True
                except Exception as e3:
                    print(f"简化参数转录失败: {str(e3)}")
            
            # 方法4: 最小参数集
            if not success:
                try:
                    self.progress_signal.emit(70, "最后尝试...")
                    result = self.model.generate(
                        input=audio_path
                    )
                    success = True
                except Exception as e4:
                    raise Exception(f"所有转录尝试均失败，最后错误: {str(e4)}")
            
            self.progress_signal.emit(80, "处理转录结果...")
            
            # 打印接收到的结果类型，帮助调试
            print(f"转录结果类型: {type(result)}")
            
            # 转换为字幕格式
            subtitles = self.convert_funasr_to_subtitles(result)
            
            self.progress_signal.emit(90, "转录完成!")
            
            # 发送结果
            self.result_signal.emit(subtitles)
            
            self.progress_signal.emit(100, "准备就绪")
            
        except Exception as e:
            # 捕获并发送错误信号
            import traceback
            error_details = traceback.format_exc()
            self.error_signal.emit(f"转录失败: {str(e)}\n\n{error_details}")
    
    def extract_audio(self, video_path):
        """从视频文件中提取音频"""
        try:
            # 使用临时目录
            temp_dir = tempfile.gettempdir()
            os.makedirs(os.path.join(temp_dir, "subtitlecut"), exist_ok=True)
            audio_path = os.path.join(temp_dir, "subtitlecut", "extracted_audio.wav")
            
            self.progress_signal.emit(25, "提取音频...")
            
            # 使用moviepy提取音频
            from moviepy.editor import VideoFileClip
            
            video_clip = VideoFileClip(video_path)
            audio_clip = video_clip.audio
            
            # 设置音频参数
            audio_clip.write_audiofile(
                audio_path,
                fps=16000,
                nbytes=2,
                codec='pcm_s16le',
                ffmpeg_params=["-ac", "1"],
                logger=None  # 禁用日志输出
            )
            
            # 关闭资源
            audio_clip.close()
            video_clip.close()
            
            return audio_path
            
        except Exception as e:
            print(f"提取音频失败: {str(e)}")
            # 尝试使用pydub
            try:
                self.progress_signal.emit(25, "使用备选方法提取音频...")
                from pydub import AudioSegment
                
                audio = AudioSegment.from_file(video_path)
                audio = audio.set_channels(1).set_frame_rate(16000)
                audio.export(audio_path, format="wav")
                
                return audio_path
                
            except Exception as e2:
                # 如果两种方法都失败，返回原始文件
                print(f"备选提取失败: {str(e2)}")
                return video_path
    
    def convert_funasr_to_subtitles(self, funasr_result):
        """将FunASR结果转换为字幕格式，简化且更健壮的实现"""
        # 输出原始结果结构，帮助调试
        print("结果类型:", type(funasr_result))
        if isinstance(funasr_result, dict):
            print("结果键:", funasr_result.keys())
        
        # 初始化空字幕列表
        subtitles = []
        
        try:
            # 第一种格式: 直接包含sentences列表
            if isinstance(funasr_result, dict) and 'sentences' in funasr_result:
                sentences = funasr_result['sentences']
                print(f"找到 {len(sentences)} 个句子")
                
                for i, sent in enumerate(sentences):
                    # 安全地获取时间和文本
                    start_time = int(float(sent.get('start', i*2)) * 1000)  # 默认按每句2秒估计
                    end_time = int(float(sent.get('end', (i+1)*2)) * 1000)
                    text = sent.get('text', '').strip()
                    
                    # 如果没有文本则跳过
                    if not text:
                        continue
                        
                    # 添加字幕
                    subtitles.append({
                        "id": i + 1,
                        "start_time": start_time,
                        "end_time": end_time,
                        "text": text
                    })
                
            # 第二种格式: 嵌套在某个字段中的结果
            elif isinstance(funasr_result, dict) and any(k in funasr_result for k in ['results', 'result', 'asr_result']):
                # 尝试找到结果字段
                result_field = None
                for field in ['results', 'result', 'asr_result']:
                    if field in funasr_result:
                        result_field = field
                        break
                        
                if result_field:
                    result_content = funasr_result[result_field]
                    
                    # 如果是列表类型，直接使用
                    if isinstance(result_content, list):
                        sentences = result_content
                    # 如果是字典类型，查找sentences字段
                    elif isinstance(result_content, dict) and 'sentences' in result_content:
                        sentences = result_content['sentences']
                    else:
                        sentences = []
                        
                    print(f"从 {result_field} 找到 {len(sentences)} 个句子")
                    
                    for i, sent in enumerate(sentences):
                        # 安全地获取时间和文本
                        if isinstance(sent, dict):
                            start_time = int(float(sent.get('start', i*2)) * 1000)
                            end_time = int(float(sent.get('end', (i+1)*2)) * 1000)
                            text = sent.get('text', '').strip()
                            if not text and 'content' in sent:
                                text = sent['content'].strip()
                        else:
                            # 如果句子不是字典，尝试直接使用字符串
                            text = str(sent).strip()
                            start_time = i * 2000  # 每2秒一句的估计值
                            end_time = (i + 1) * 2000
                        
                        # 如果没有文本则跳过
                        if not text:
                            continue
                            
                        # 添加字幕
                        subtitles.append({
                            "id": i + 1,
                            "start_time": start_time,
                            "end_time": end_time,
                            "text": text
                        })
            
            # 第三种格式: 直接使用text或raw_text作为整体结果
            elif isinstance(funasr_result, dict) and ('text' in funasr_result or 'raw_text' in funasr_result):
                text = ""
                if 'text' in funasr_result:
                    text = funasr_result['text']
                elif 'raw_text' in funasr_result:
                    text = funasr_result['raw_text']
                    
                print("找到整体文本，长度:", len(text))
                
                # 简单按句号、问号、感叹号分割成句子
                sentences = []
                import re
                for sent in re.split(r'[。！？.!?]', text):
                    sent = sent.strip()
                    if sent:
                        sentences.append(sent)
                        
                # 如果无法分割，则作为一个整体
                if not sentences and text:
                    sentences = [text]
                    
                # 生成字幕
                for i, sent in enumerate(sentences):
                    start_time = i * 3000  # 假设每句3秒
                    end_time = (i + 1) * 3000
                    
                    subtitles.append({
                        "id": i + 1,
                        "start_time": start_time,
                        "end_time": end_time,
                        "text": sent
                    })
            
            # 第四种情况: 如果funasr_result本身是字符串
            elif isinstance(funasr_result, str):
                text = funasr_result.strip()
                print("结果是字符串，长度:", len(text))
                
                if text:
                    # 添加为单个字幕
                    subtitles.append({
                        "id": 1,
                        "start_time": 0,
                        "end_time": 60000,  # 假设60秒
                        "text": text
                    })
            
            # 如果上述情况都不匹配，尝试进一步分析结构
            else:
                print("未识别的结果格式，尝试进一步分析...")
                
                # 如果是列表，尝试直接使用
                if isinstance(funasr_result, list):
                    for i, item in enumerate(funasr_result):
                        if isinstance(item, dict) and 'text' in item:
                            start_time = int(float(item.get('start', i*2)) * 1000)
                            end_time = int(float(item.get('end', (i+1)*2)) * 1000)
                            text = item['text']
                        elif isinstance(item, str):
                            text = item
                            start_time = i * 2000
                            end_time = (i + 1) * 2000
                        else:
                            continue
                            
                        subtitles.append({
                            "id": i + 1,
                            "start_time": start_time,
                            "end_time": end_time,
                            "text": text
                        })
                
                # 如果没有识别出任何结构，返回错误消息
                if not subtitles:
                    print("无法识别结果格式")
                    return [{"id": 1, "start_time": 0, "end_time": 0, "text": "无法识别转录结果格式"}]
        
        except Exception as e:
            # 捕获处理过程中的任何错误
            import traceback
            print(f"转换字幕时出错: {str(e)}")
            print(traceback.format_exc())
            
            # 如果处理过程中出错且没有生成任何字幕，返回错误消息
            if not subtitles:
                return [{"id": 1, "start_time": 0, "end_time": 0, "text": f"处理转录结果时出错: {str(e)}"}]
        
        # 最终检查：如果没有生成任何字幕，返回默认消息
        if not subtitles:
            return [{"id": 1, "start_time": 0, "end_time": 0, "text": "未能从转录结果提取字幕"}]
        
        print(f"最终提取了 {len(subtitles)} 条字幕")
        return subtitles 