import re

class SubtitleManager:
    """字幕管理器 - 用于处理和显示字幕"""
    
    def __init__(self):
        """初始化字幕管理器"""
        self.subtitles = []
        self.current_index = -1
    
    def load_subtitles(self, subtitles):
        """加载字幕数据"""
        if not subtitles:
            self.subtitles = []
            self.current_index = -1
            return
            
        # 确保字幕按时间排序
        self.subtitles = sorted(subtitles, key=lambda x: x.get('start_time', 0))
        
        # 重新分配ID
        for i, subtitle in enumerate(self.subtitles):
            subtitle['id'] = i + 1
            
        self.current_index = -1
    
    def get_subtitle_at_time(self, position_ms):
        """获取指定时间点的字幕"""
        if not self.subtitles:
            return None
            
        for subtitle in self.subtitles:
            start_time = subtitle.get('start_time', 0)
            end_time = subtitle.get('end_time', 0)
            
            if start_time <= position_ms <= end_time:
                return subtitle
                
        return None
    
    def get_subtitle_index_at_time(self, position_ms):
        """获取指定时间点字幕的索引"""
        if not self.subtitles:
            return -1
            
        for i, subtitle in enumerate(self.subtitles):
            start_time = subtitle.get('start_time', 0)
            end_time = subtitle.get('end_time', 0)
            
            if start_time <= position_ms <= end_time:
                return i
                
        return -1
    
    def format_subtitle_for_display(self, subtitle):
        """格式化字幕用于显示"""
        if not subtitle:
            return ""
            
        # 格式化时间
        start_time = subtitle.get('start_time', 0)
        end_time = subtitle.get('end_time', 0)
        
        start_time_str = self.format_time(start_time)
        end_time_str = self.format_time(end_time)
        
        # 获取文本
        text = subtitle.get('text', '').strip()
        
        return f"{start_time_str} - {end_time_str}\n{text}"
    
    def format_time(self, ms):
        """将毫秒转换为可读时间格式"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        seconds %= 60
        minutes %= 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_full_text(self):
        """获取所有字幕的完整文本"""
        if not self.subtitles:
            return ""
            
        return "\n".join([s.get('text', '') for s in self.subtitles])
    
    def export_as_srt(self, output_path):
        """导出为SRT格式字幕文件"""
        if not self.subtitles:
            return False
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, subtitle in enumerate(self.subtitles):
                    # SRT索引
                    f.write(f"{i+1}\n")
                    
                    # 时间格式
                    start_time = subtitle.get('start_time', 0)
                    end_time = subtitle.get('end_time', 0)
                    
                    start_time_str = self.ms_to_srt_time(start_time)
                    end_time_str = self.ms_to_srt_time(end_time)
                    
                    f.write(f"{start_time_str} --> {end_time_str}\n")
                    
                    # 字幕文本
                    f.write(f"{subtitle.get('text', '')}\n\n")
                    
            return True
        except Exception as e:
            print(f"导出SRT文件出错: {str(e)}")
            return False
    
    def ms_to_srt_time(self, ms):
        """将毫秒转换为SRT时间格式 (HH:MM:SS,mmm)"""
        ms = int(ms)
        seconds = ms // 1000
        ms = ms % 1000
        minutes = seconds // 60
        seconds = seconds % 60
        hours = minutes // 60
        minutes = minutes % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}" 