# SenseVoice语音对话系统使用手册

## 📖 项目概述

这是一个基于SenseVoice的智能语音对话系统，集成了语音识别(ASR)、大语言模型(LLM)对话和语音合成(TTS)功能。系统支持多轮对话、实时语音检测、流式TTS播放等高级功能，为用户提供完整的语音交互体验。

### 🎯 核心功能

- **多语言语音识别**: 支持中文、英文、粤语、日语、韩语等多种语言
- **智能对话管理**: 支持多轮对话，自动管理对话历史
- **实时语音检测**: 自动检测语音开始和结束，无需手动按键
- **流式语音合成**: 实时将LLM回复转换为语音并播放
- **多种交互方式**: 支持按键录音、实时语音、文字输入等多种交互模式
- **Web界面**: 提供基于Gradio的Web界面进行语音识别测试

## 🛠️ 系统架构

### 主要组件

```
SenseVoice语音对话系统
├── 语音识别模块 (ASR)
│   ├── SenseVoiceASRDirect - 直接调用SenseVoice模型
│   └── 实时语音录制器 - 连续语音检测和录制
├── 对话管理模块
│   ├── ChatManager - 多轮对话历史管理
│   └── LLMClient - 大语言模型客户端
├── 语音合成模块 (TTS)
│   ├── GPTSoVITSClient - GPT-SoVITS API客户端
│   └── StreamingTTSManager - 流式TTS管理器
├── 音频处理模块
│   ├── AudioRecorder - 按键录音器
│   └── 音频预处理和格式转换
└── 配置管理
    ├── Config - 统一配置管理
    └── 系统提示词管理
```

## 📋 环境要求

### 硬件要求
- **GPU**: 推荐NVIDIA GPU (CUDA支持)
- **内存**: 至少8GB RAM
- **存储**: 至少10GB可用空间
- **音频设备**: 麦克风和扬声器

### 软件要求
- **Python**: 3.8+
- **CUDA**: 11.8+ (如果使用GPU)
- **操作系统**: Windows 10/11, Linux, macOS

## 🔧 安装步骤

### 1. 克隆项目
```bash
git clone <项目地址>
cd SenseVoice-main
```

### 2. 安装Python依赖
```bash
pip install -r requirements.txt
```

主要依赖包括：
- `torch==2.0.1+cu118` - PyTorch深度学习框架
- `torchaudio==2.0.2` - 音频处理
- `funasr>=1.1.2` - 语音识别工具包
- `openai` - LLM API客户端
- `keyboard` - 键盘监听
- `pyaudio` - 音频录制
- `pygame` - 音频播放
- `requests` - HTTP请求
- `gradio` - Web界面

### 3. 下载模型文件

#### SenseVoice模型
系统会自动从ModelScope下载SenseVoice模型到：
```
C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall
```

#### VAD模型
VAD模型会自动下载到：
```
C:\Users\Administrator\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch
```

### 4. 配置系统

#### 编辑配置文件 `config.py`
```python
# ASR模型配置
ASR_MODEL_DIR = r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall"
VAD_MODEL_DIR = r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch"
ASR_DEVICE = "cuda:0"  # 或 "cpu"

# LLM配置
LLM_API_KEY = "你的API密钥"
LLM_BASE_URL = "https://www.sophnet.com/api/open-apis/v1"
LLM_MODEL_NAME = "DeepSeek-V3.1-Fast"

# TTS配置
TTS_API_URL = "http://127.0.0.1:9880"
TTS_REF_AUDIO_PATH = "参考音频.wav"
```

#### 准备参考音频
将你的参考音频文件命名为 `参考音频.wav` 并放在项目根目录。

#### 创建系统提示词
创建 `System_Content.txt` 文件，内容示例：
```
你是一个追求高效沟通的对话助手，在保持简洁精准的基础上，注重自然交流的节奏与温度。
```

### 5. 启动GPT-SoVITS服务 (可选)
如果使用TTS功能，需要启动GPT-SoVITS API服务：
```bash
# 在GPT-SoVITS目录下运行
python api_v2.py
```

## 🚀 使用方法

### 1. 启动主程序
```bash
python voice_chat.py
```

### 2. 操作说明

#### 按键控制
- **Z键**: 按住录音，松开停止
- **R键**: 切换实时语音模式
- **T键**: 文字输入模式
- **H键**: 查看对话历史
- **C键**: 清空对话历史
- **V键**: 切换TTS开关
- **Q键**: 退出程序

#### 交互模式

**1. 按键录音模式**
- 按住Z键开始录音
- 松开Z键停止录音并自动识别
- 识别完成后发送给LLM
- LLM回复后自动进行语音合成

**2. 实时语音模式**
- 按R键开启实时语音模式
- 系统自动检测语音开始和结束
- 无需手动按键，说话即可自动识别
- 支持连续对话

**3. 文字输入模式**
- 按T键进入文字输入模式
- 直接输入文字与LLM对话
- 输入 `exit` 返回语音模式

### 3. Web界面使用

#### 启动Web界面
```bash
python qita/webui.py
```

#### 功能说明
- 上传音频文件进行语音识别
- 支持多种语言选择
- 显示情感识别和事件检测结果
- 提供示例音频测试

### 4. API服务使用

#### 启动API服务
```bash
python qita/api.py
```

#### API接口
- **POST /api/v1/asr**: 语音识别接口
- **GET /docs**: API文档

## ⚙️ 配置详解

### 音频配置
```python
# 音频录制参数
AUDIO_CHUNK = 1024          # 每次读取的帧数
AUDIO_FORMAT = "paInt16"    # 音频格式
AUDIO_CHANNELS = 1          # 声道数
AUDIO_RATE = 16000          # 采样率
AUDIO_MIN_DURATION = 0.5    # 最小录音时长
```

### 实时语音配置
```python
# 实时语音检测参数
REALTIME_VOICE_SILENCE_THRESHOLD = 0.8    # 静音检测阈值
REALTIME_VOICE_MIN_SPEECH_LENGTH = 0.5    # 最小语音长度
REALTIME_VOICE_MAX_SPEECH_LENGTH = 30.0   # 最大语音长度
```

### 流式TTS配置
```python
# 流式TTS参数
STREAMING_TTS_CHUNK_SIZE = 30              # 每次传给TTS的字符数
STREAMING_TTS_MIN_CHUNK_SIZE = 10          # 最小字符数
STREAMING_TTS_MAX_CHUNK_SIZE = 50          # 最大字符数
STREAMING_TTS_SPLIT_PUNCTUATION = '。！？.!?，,;；'  # 切分标点符号
```

## 🔍 功能特性

### 1. 多语言支持
- **中文**: 支持普通话识别
- **英文**: 支持英语识别
- **粤语**: 支持粤语识别
- **日语**: 支持日语识别
- **韩语**: 支持韩语识别
- **自动检测**: 自动识别语音语言

### 2. 情感识别
系统能够识别语音中的情感：
- 😊 开心 (HAPPY)
- 😔 悲伤 (SAD)
- 😡 愤怒 (ANGRY)
- 😰 恐惧 (FEARFUL)
- 🤢 厌恶 (DISGUSTED)
- 😮 惊讶 (SURPRISED)
- 中性 (NEUTRAL)

### 3. 事件检测
系统能够检测音频中的事件：
- 🎼 背景音乐 (BGM)
- 👏 掌声 (Applause)
- 😀 笑声 (Laughter)
- 😭 哭声 (Cry)
- 🤧 喷嚏/咳嗽 (Sneeze/Cough)
- 呼吸声 (Breath)

### 4. 智能对话管理
- **多轮对话**: 自动维护对话上下文
- **历史管理**: 可查看和清空对话历史
- **上下文理解**: 基于历史对话进行回复

### 5. 流式语音合成
- **实时合成**: LLM回复时实时进行语音合成
- **分段处理**: 智能切分长文本进行合成
- **连续播放**: 音频片段无缝连接播放

## 🐛 故障排除

### 常见问题

#### 1. 模型加载失败
**症状**: `❌ SenseVoice模型加载失败`
**解决方案**:
- 检查网络连接，确保能访问ModelScope
- 检查磁盘空间是否充足
- 尝试手动下载模型文件

#### 2. 音频设备问题
**症状**: `录音启动失败` 或 `无法播放音频`
**解决方案**:
- 检查麦克风权限设置
- 确认音频设备正常工作
- 安装正确的音频驱动

#### 3. LLM API调用失败
**症状**: `❌ LLM请求失败`
**解决方案**:
- 检查API密钥是否正确
- 确认网络连接正常
- 检查API服务是否可用

#### 4. TTS服务连接失败
**症状**: `❌ 无法连接到API服务`
**解决方案**:
- 确认GPT-SoVITS服务已启动
- 检查端口9880是否被占用
- 验证参考音频文件路径正确

#### 5. 实时语音检测不准确
**症状**: 语音检测过于敏感或不敏感
**解决方案**:
- 调整VAD敏感度参数
- 校准噪声基线
- 改善录音环境

### 性能优化

#### 1. GPU内存不足
```python
# 在config.py中修改
ASR_DEVICE = "cpu"  # 使用CPU而不是GPU
```

#### 2. 提高识别速度
```python
# 调整批处理大小
batch_size_s = 30  # 减小批处理大小
```

#### 3. 优化TTS性能
```python
# 调整TTS参数
sample_steps = 4    # 减少采样步数
batch_size = 1      # 减小批处理大小
```

## 📊 性能指标

### 识别性能
- **识别准确率**: 中文 >95%, 英文 >90%
- **识别速度**: 10秒音频约70ms (GPU)
- **支持音频长度**: 最长30秒 (单次)

### 系统性能
- **内存占用**: 约4-6GB (GPU模式)
- **CPU占用**: 约20-30% (CPU模式)
- **响应延迟**: 首Token时间 <2秒

## 🔧 高级配置

### 1. 自定义按键
在 `config.py` 中修改按键配置：
```python
KEY_RECORD = 'z'           # 录音键
KEY_TEXT_INPUT = 't'       # 文字输入键
KEY_SHOW_HISTORY = 'h'     # 查看历史键
KEY_CLEAR_HISTORY = 'c'    # 清空历史键
KEY_TOGGLE_TTS = 'v'       # 切换TTS键
KEY_TOGGLE_REALTIME = 'r'  # 切换实时语音键
KEY_QUIT = 'q'             # 退出键
```

### 2. 调整VAD参数
```python
# 实时语音检测参数
REALTIME_VOICE_SILENCE_THRESHOLD = 1.0    # 增加静音阈值
REALTIME_VOICE_MIN_SPEECH_LENGTH = 0.8    # 增加最小语音长度
```

### 3. 自定义系统提示词
编辑 `System_Content.txt` 文件，设置AI助手的角色和行为。

### 4. 多模型支持
系统支持切换不同的GPT-SoVITS模型：
```python
# 在gpt_sovits_client.py中
client.change_gpt_weights("新模型路径.ckpt")
client.change_sovits_weights("新模型路径.pth")
```

## 📚 API文档

### 语音识别API

#### 请求格式
```http
POST /api/v1/asr
Content-Type: multipart/form-data

files: 音频文件
keys: 文件名
lang: 语言代码
```

#### 响应格式
```json
{
  "result": [
    {
      "key": "文件名",
      "text": "识别结果",
      "raw_text": "原始结果",
      "clean_text": "清理后结果"
    }
  ]
}
```

### LLM对话API
通过OpenAI兼容接口调用：
```python
# 使用OpenAI客户端
from openai import OpenAI

client = OpenAI(
    api_key="你的API密钥",
    base_url="API基础URL"
)

response = client.chat.completions.create(
    model="模型名称",
    messages=[{"role": "user", "content": "用户消息"}],
    stream=True
)
```

## 🎯 使用场景

### 1. 智能客服
- 语音问答系统
- 多轮对话支持
- 情感识别分析

### 2. 语音助手
- 个人语音助手
- 智能家居控制
- 语音交互应用

### 3. 教育培训
- 语音学习系统
- 口语练习平台
- 多语言学习

### 4. 内容创作
- 语音转文字
- 音频内容分析
- 情感分析应用

## 🔄 更新日志

### v1.0.0 (当前版本)
- ✅ 基础语音识别功能
- ✅ 多轮对话支持
- ✅ 实时语音检测
- ✅ 流式TTS播放
- ✅ Web界面支持
- ✅ API服务支持

### 计划功能
- 🔄 更多语言支持
- 🔄 语音克隆功能
- 🔄 离线模式支持
- 🔄 移动端适配

## 📞 技术支持

### 获取帮助
1. 查看项目文档
2. 检查常见问题解答
3. 提交Issue反馈问题
4. 加入技术交流群

### 贡献代码
欢迎提交Pull Request来改进项目：
1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

## 📄 许可证

本项目基于MIT许可证开源，详见LICENSE文件。

---

**注意**: 使用本系统前请确保已正确配置所有依赖和模型文件，并遵守相关API的使用条款和限制。
