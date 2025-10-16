# SenseVoice + LLM 对话集成指南

本项目提供了将SenseVoice语音识别模型与LLM对话系统集成的完整解决方案。

## 📋 目录

- [项目概述](#项目概述)
- [安装要求](#安装要求)
- [集成方案](#集成方案)
- [快速开始](#快速开始)
- [详细使用](#详细使用)
- [常见问题](#常见问题)

## 🎯 项目概述

SenseVoice是一个强大的多语言语音理解模型，支持：
- **多语言ASR**: 中文、英文、粤语、日语、韩语
- **情感识别**: 识别语音中的情感状态
- **事件检测**: 检测背景音乐、掌声、笑声等音频事件
- **高效推理**: 比Whisper快15倍的推理速度

## 📦 安装要求

### 基础依赖
```bash
pip install torch torchaudio funasr gradio requests soundfile pyaudio numpy
```

### 运行设置脚本
```bash
python setup_llm_integration.py
```

## 🚀 集成方案

### 方案一：API集成（推荐）

**优点**: 服务分离、易于扩展、支持并发
**适用场景**: 生产环境、多用户系统

```python
from llm_asr_integration_api import SenseVoiceASR, LLMDialogueSystem

# 1. 启动API服务
# 终端运行: python api.py

# 2. 使用客户端
asr_client = SenseVoiceASR("http://localhost:50000")
dialogue_system = LLMDialogueSystem(asr_client)

# 3. 语音对话
result = dialogue_system.chat_with_voice("audio.wav", "auto")
```

### 方案二：直接调用

**优点**: 延迟最低、资源控制精确
**适用场景**: 单用户应用、离线使用

```python
from llm_asr_integration_direct import SenseVoiceASRDirect, LLMDialogueSystemDirect

# 1. 初始化
asr_client = SenseVoiceASRDirect(device="cuda:0")
dialogue_system = LLMDialogueSystemDirect(asr_client)

# 2. 处理语音
result = dialogue_system.process_voice_input("audio.wav", "auto")
```

### 方案三：流式对话

**优点**: 实时交互、支持连续对话
**适用场景**: 实时语音助手、交互式应用

```python
from llm_asr_streaming_integration import StreamingLLMDialogue

# 1. 初始化
dialogue_system = StreamingLLMDialogue(asr_client, llm_client)
dialogue_system.start_conversation()

# 2. 实时录音对话
dialogue_system.record_and_process()
```

## ⚡ 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <your-repo>
cd SenseVoice-main

# 安装依赖
pip install -r requirements.txt

# 运行设置脚本
python setup_llm_integration.py
```

### 2. 启动SenseVoice服务
```bash
# 方式1: 启动API服务
python api.py

# 方式2: 启动WebUI
python webui.py
```

### 3. 测试集成
```bash
# 测试API集成
python llm_asr_integration_api.py

# 测试直接调用
python llm_asr_integration_direct.py

# 测试流式对话
python llm_asr_streaming_integration.py
```

## 📖 详细使用

### API集成详细步骤

1. **启动API服务**
```bash
export SENSEVOICE_DEVICE=cuda:0
python api.py
```

2. **使用Python客户端**
```python
import requests

# 上传音频文件进行转录
files = {'files': open('audio.wav', 'rb')}
data = {'lang': 'auto', 'keys': 'test_audio'}
response = requests.post('http://localhost:50000/api/v1/asr', files=files, data=data)
result = response.json()
print(result['result'][0]['clean_text'])
```

### 直接调用详细配置

```python
# 自定义配置
asr_client = SenseVoiceASRDirect(
    model_dir="iic/SenseVoiceSmall",  # 模型路径
    device="cuda:0"                   # 设备选择
)

# 高级参数
result = asr_client.transcribe_audio_file(
    audio_file_path="audio.wav",
    language="auto",      # 语言设置
    use_itn=True          # 逆文本规范化
)
```

### 流式对话高级功能

```python
# 设置回调函数
def on_speech_detected(text):
    print(f"检测到语音: {text}")

def on_llm_response(response):
    print(f"LLM回复: {response}")

dialogue_system.on_speech_detected = on_speech_detected
dialogue_system.on_llm_response = on_llm_response

# 批量处理
audio_files = ["audio1.wav", "audio2.wav", "audio3.wav"]
results = dialogue_system.batch_process_audio_files(audio_files)
```

## 🔧 配置选项

### 模型配置
```json
{
    "sensevoice": {
        "model_dir": "iic/SenseVoiceSmall",
        "device": "cuda:0",
        "language": "auto",
        "use_itn": true
    }
}
```

### 音频配置
```json
{
    "audio": {
        "sample_rate": 16000,
        "chunk_size": 1024,
        "channels": 1
    }
}
```

## 🤖 LLM集成

### 自定义LLM客户端

```python
class CustomLLMClient:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name
    
    def chat(self, text):
        # 实现你的LLM调用逻辑
        response = your_llm_api_call(text)
        return response

# 使用自定义LLM
llm_client = CustomLLMClient("your_api_key", "your_model")
dialogue_system = LLMDialogueSystemDirect(asr_client, llm_client)
```

### 支持的LLM类型
- OpenAI GPT系列
- Claude系列
- 本地部署的模型
- 自定义API接口

## 📊 性能优化

### 1. GPU加速
```python
# 使用GPU加速
asr_client = SenseVoiceASRDirect(device="cuda:0")
```

### 2. 批处理
```python
# 批量处理音频文件
results = dialogue_system.batch_process_audio_files(audio_files)
```

### 3. 缓存机制
```python
# 启用缓存
result = model.generate(input=audio, cache={})
```

## 🐛 常见问题

### Q: 模型加载失败
**A**: 检查模型路径和设备配置
```python
# 检查模型是否存在
import os
model_path = "iic/SenseVoiceSmall"
print(f"模型路径存在: {os.path.exists(model_path)}")
```

### Q: 音频格式不支持
**A**: 确保音频为16kHz采样率的WAV格式
```python
# 音频格式转换
import librosa
audio, sr = librosa.load("input.mp3", sr=16000)
librosa.output.write_wav("output.wav", audio, 16000)
```

### Q: API连接失败
**A**: 检查API服务是否启动
```bash
# 检查服务状态
curl http://localhost:50000/
```

### Q: 内存不足
**A**: 调整批处理大小或使用CPU
```python
# 使用CPU
asr_client = SenseVoiceASRDirect(device="cpu")

# 减小批处理大小
result = model.generate(input=audio, batch_size_s=30)
```

## 📝 示例文件

- `llm_asr_integration_api.py` - API集成示例
- `llm_asr_integration_direct.py` - 直接调用示例  
- `llm_asr_streaming_integration.py` - 流式对话示例
- `setup_llm_integration.py` - 环境设置脚本
- `usage_example.py` - 使用示例代码

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个集成方案！

## 📄 许可证

本项目遵循原SenseVoice项目的许可证。

---

**开始你的语音+LLM对话之旅吧！** 🎉
