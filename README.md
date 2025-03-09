# 字幕视频剪辑工具 (SubtitleCut)

一个用于根据字幕进行视频剪辑的桌面应用程序。

## 功能特点

- 选择视频或音频文件并自动转录为字幕和纯文本
- 点击字幕可以跳转到视频/音频的对应时间点
- 删除字幕内容将自动剪掉对应的视频/音频片段
- 编辑完成后可以预览和导出处理后的视频

## 界面预览

应用程序界面分为三个主要部分：
1. 视频播放器 - 用于预览原始和编辑后的视频
2. 字幕编辑器 - 用于编辑和删除字幕
3. 时间轴 - 显示字幕在视频中的时间位置

## 安装说明

### 系统要求

- Python 3.8 或更高版本
- 支持的操作系统：Windows、macOS、Linux

### 安装步骤

1. 克隆或下载此仓库

```bash
git clone https://github.com/yourusername/subtitlecut.git
cd subtitlecut
```

2. 安装所需依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
python main.py
```

## 使用说明

1. 点击"打开"按钮加载视频或音频文件
2. 点击"转录"按钮将视频/音频转录为字幕
3. 编辑字幕 - 修改文本或删除不需要的部分
4. 点击"预览"按钮查看编辑效果
5. 点击"导出"按钮将编辑好的视频保存到本地

## 技术实现

- UI框架：PyQt6
- 视频处理：FFmpeg (通过Python包装器)
- 音频转录：可扩展以支持多种转录服务

## 扩展开发

### 实现音频转录

在 `app/utils/transcriber.py` 中，您可以集成各种语音识别服务：
- OpenAI Whisper (推荐用于本地转录)
- Google Speech-to-Text
- 其他第三方服务

### 视频处理实现

在 `app/utils/video_processor.py` 中，您可以使用 FFmpeg 或类似工具来实现视频剪辑功能。

## 许可协议

[MIT](LICENSE)

## 贡献指南

欢迎贡献代码、报告问题或提出功能建议。 