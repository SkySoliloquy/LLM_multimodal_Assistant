# GPT-SoVITS API 使用说明

## 📖 项目概述

这是一个完整的GPT-SoVITS API调用方案，允许你在任意Python环境中通过API接口调用GPT-SoVITS进行语音合成。

## 🎯 你的模型信息

- **GPT模型路径**: `D:\GPT_Sovits\GPT-SoVITS-v2pro-20250604\GPT_weights_v4\Athna-e10.ckpt`
- **SoVITS模型路径**: `D:\GPT_Sovits\GPT-SoVITS-v2pro-20250604\SoVITS_weights_v4\Athna_e2_s320_l32.pth`
- **模型版本**: v4

## 🚀 快速开始

### 第一步: 启动API服务

1. 双击运行 `start_api_server.bat`
2. 等待看到类似以下输出，表示服务启动成功:
   ```
   INFO:     Uvicorn running on http://0.0.0.0:9880 (Press CTRL+C to quit)
   ```

### 第二步: 准备参考音频

你需要准备一个参考音频文件（参考音频是指你想要模仿的声音样本）:

- **格式**: WAV格式
- **时长**: 建议3-10秒
- **内容**: 清晰的人声，最好是你训练时使用的角色声音
- **位置**: 可以放在任意位置，调用API时指定完整路径

**示例**: 
```
D:\GPT_Sovits\GPT-SoVITS-v2pro-20250604\参考音频.wav
```

### 第三步: 调用API

#### 方式1: 使用提供的Python客户端（推荐）

```python
from gpt_sovits_client import GPTSoVITSClient

# 创建客户端
client = GPTSoVITSClient(api_url="http://127.0.0.1:9880")

# 调用语音合成
client.text_to_speech(
    text="你好，这是一段测试语音。",
    ref_audio_path="D:/GPT_Sovits/GPT-SoVITS-v2pro-20250604/参考音频.wav",
    output_path="输出语音.wav",
    text_lang="zh",
    prompt_lang="zh",
    prompt_text="参考音频的文字内容",  # 参考音频说的是什么
)
```

#### 方式2: 使用requests直接调用

```python
import requests

response = requests.post(
    "http://127.0.0.1:9880/tts",
    json={
        "text": "你好，这是一段测试语音。",
        "text_lang": "zh",
        "ref_audio_path": "D:/GPT_Sovits/GPT-SoVITS-v2pro-20250604/参考音频.wav",
        "prompt_text": "参考音频的文字内容",
        "prompt_lang": "zh",
    }
)

# 保存音频
with open("output.wav", "wb") as f:
    f.write(response.content)
```

## 📝 API参数说明

### 必填参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `text` | 要合成的文本 | "你好世界" |
| `text_lang` | 文本语言 | "zh" (中文) / "en" (英文) / "ja" (日文) |
| `ref_audio_path` | 参考音频路径 | "参考音频.wav" |
| `prompt_lang` | 参考音频语言 | "zh" |

### 可选参数

| 参数 | 说明 | 默认值 | 推荐范围 |
|------|------|--------|----------|
| `prompt_text` | 参考音频的文本内容 | "" | - |
| `top_k` | 采样参数 | 5 | 1-20 |
| `top_p` | 采样参数 | 1.0 | 0.5-1.0 |
| `temperature` | 温度参数，控制随机性 | 1.0 | 0.6-1.5 |
| `speed_factor` | 语速控制 | 1.0 | 0.5-2.0 |
| `text_split_method` | 文本切分方法 | "cut5" | cut0-cut5 |
| `batch_size` | 批处理大小 | 1 | 1-8 |
| `sample_steps` | 采样步数(v4模型) | 32 | 4/8/16/32 |

## 💡 使用技巧

### 1. 参考音频选择

- ✅ **好的参考音频**: 清晰、无背景噪音、情绪表达清晰、3-10秒
- ❌ **不好的参考音频**: 有背景音乐、有噪音、过长或过短、多人说话

### 2. 语言设置

| 语言代码 | 说明 |
|---------|------|
| `zh` | 中文 |
| `en` | 英文 |
| `ja` | 日文 |
| `ko` | 韩文 |
| `yue` | 粤语 |
| `auto` | 自动检测 |

### 3. 文本切分方法

- `cut0`: 不切分
- `cut1`: 按标点符号切分
- `cut2`: 按标点符号和停顿切分
- `cut3`: 按标点符号、停顿和长度切分
- `cut4`: 更细粒度的切分
- `cut5`: 最细粒度的切分（推荐）

### 4. 参数调优建议

**追求稳定输出**:
```python
top_k=5
top_p=0.8
temperature=0.8
```

**追求多样性**:
```python
top_k=15
top_p=1.0
temperature=1.2
```

**加快语速**:
```python
speed_factor=1.2  # 加快20%
```

**放慢语速**:
```python
speed_factor=0.8  # 减慢20%
```

## 🔧 故障排除

### 问题1: 无法连接到API服务

**症状**: `❌ 错误: 无法连接到API服务`

**解决方法**:
1. 检查是否已运行 `start_api_server.bat`
2. 确认服务启动成功（查看控制台输出）
3. 检查端口9880是否被占用

### 问题2: 找不到参考音频

**症状**: `ref_audio_path is required` 或文件路径错误

**解决方法**:
1. 确保参考音频文件存在
2. 使用完整的绝对路径
3. Windows路径使用正斜杠 `/` 或双反斜杠 `\\`

### 问题3: 合成失败或音质差

**解决方法**:
1. 检查参考音频质量
2. 确保参考音频与训练数据风格一致
3. 调整 `top_k`, `top_p`, `temperature` 参数
4. 尝试不同的 `text_split_method`

### 问题4: 显存不足

**症状**: CUDA out of memory

**解决方法**:
1. 修改配置文件 `tts_infer_athna.yaml`:
   ```yaml
   device: cpu  # 改为使用CPU
   is_half: false
   ```
2. 或者减小 `batch_size` 参数

## 📚 完整示例代码

### 示例1: 基础使用

```python
from gpt_sovits_client import GPTSoVITSClient

client = GPTSoVITSClient()

client.text_to_speech(
    text="欢迎使用GPT-SoVITS语音合成系统。",
    ref_audio_path="参考音频.wav",
    output_path="输出.wav",
    text_lang="zh",
    prompt_lang="zh",
    prompt_text="这是参考音频的内容",
)
```

### 示例2: 批量处理

```python
from gpt_sovits_client import GPTSoVITSClient

client = GPTSoVITSClient()

texts = [
    "第一段要合成的文字。",
    "第二段要合成的文字。",
    "第三段要合成的文字。",
]

for i, text in enumerate(texts):
    client.text_to_speech(
        text=text,
        ref_audio_path="参考音频.wav",
        output_path=f"输出_{i+1}.wav",
        text_lang="zh",
        prompt_lang="zh",
    )
    print(f"完成 {i+1}/{len(texts)}")
```

### 示例3: 多语言支持

```python
from gpt_sovits_client import GPTSoVITSClient

client = GPTSoVITSClient()

# 中文
client.text_to_speech(
    text="这是中文语音。",
    ref_audio_path="参考音频_中文.wav",
    output_path="中文.wav",
    text_lang="zh",
    prompt_lang="zh",
)

# 英文
client.text_to_speech(
    text="This is English speech.",
    ref_audio_path="参考音频_英文.wav",
    output_path="英文.wav",
    text_lang="en",
    prompt_lang="en",
)
```

### 示例4: 高级参数调整

```python
from gpt_sovits_client import GPTSoVITSClient

client = GPTSoVITSClient()

client.text_to_speech(
    text="这是一段需要精细控制的语音合成。",
    ref_audio_path="参考音频.wav",
    output_path="高级输出.wav",
    text_lang="zh",
    prompt_lang="zh",
    prompt_text="参考音频文本",
    top_k=10,
    top_p=0.9,
    temperature=1.0,
    speed_factor=1.1,
    text_split_method="cut5",
    batch_size=2,
    sample_steps=32,
)
```

## 🌐 在局域网或远程调用

如果需要从其他机器访问API:

1. 启动服务时已绑定到 `0.0.0.0`，允许外部访问
2. 确保防火墙允许端口 9880
3. 在客户端指定服务器IP:

```python
client = GPTSoVITSClient(api_url="http://192.168.1.100:9880")
```

## 📞 API端点说明

### POST /tts
文字转语音主接口

### GET /set_gpt_weights
动态切换GPT模型

### GET /set_sovits_weights
动态切换SoVITS模型

### GET /control
控制命令 (restart/exit)

## ⚙️ 配置文件说明

配置文件位置: `GPT_SoVITS/configs/tts_infer_athna.yaml`

```yaml
custom:
  bert_base_path: GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large
  cnhuhbert_base_path: GPT_SoVITS/pretrained_models/chinese-hubert-base
  device: cuda           # 使用GPU (cuda) 或 CPU (cpu)
  is_half: true          # 是否使用半精度 (节省显存)
  t2s_weights_path: GPT_weights_v4/Athna-e10.ckpt  # GPT模型路径
  version: v4            # 模型版本
  vits_weights_path: SoVITS_weights_v4/Athna_e2_s320_l32.pth  # SoVITS模型路径
```

## 📖 相关文档

- [GPT-SoVITS GitHub](https://github.com/RVC-Boss/GPT-SoVITS)
- [API文档](api_v2.py) - 查看源码了解更多细节

## 🎉 祝你使用愉快！

如有问题，请检查:
1. API服务是否正常启动
2. 模型路径是否正确
3. 参考音频是否符合要求
4. 参数设置是否合理

