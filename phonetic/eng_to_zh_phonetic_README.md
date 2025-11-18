# 英文转中文谐音预处理模块

## 功能说明

这是一个独立的预处理模块，用于将文本中的英文单词/字母转换为中文谐音，方便在中文TTS系统中使用。

## 使用方法

### 基础用法

```python
from eng_to_zh_phonetic import convert_eng_to_zh_phonetic

# 智能模式（推荐）：只转换独立的英文单词
text = "我使用AI技术进行机器学习"
result = convert_eng_to_zh_phonetic(text, convert_mode='smart')
print(result)  # 输出: 我使用诶艾技术进行机器学习

# 保留模式：在英文后添加谐音
text = "AI is great"
result = convert_eng_to_zh_phonetic(text, convert_mode='preserve')
print(result)  # 输出: AI(诶艾) is(艾斯) great(基阿尔伊提)
```

### 高级用法

```python
from eng_to_zh_phonetic import EngToZhPhonetic

# 创建转换器实例
converter = EngToZhPhonetic()

# 使用自定义映射文件
converter = EngToZhPhonetic(mapping_file='eng_to_zh_phonetic_mapping.txt')

# 添加自定义映射
converter.add_word_mapping('GPT', '基皮提')
converter.add_letter_mapping('X', '艾克斯')

# 转换文本
result = converter.convert_text("我使用GPT模型", convert_mode='smart')
```

## 转换模式

- **smart（智能模式，推荐）**：只转换**全大写的英文单词**或**自定义热词**，直接替换为谐音，不保留原文本
- **all（全部模式）**：转换所有英文字母（包括单词中的字母）
- **preserve（保留模式）**：保留原英文，在括号中添加谐音，格式：`英文(谐音)`，仅全大写或热词

### 转换规则

- ✅ **会转换**：全大写的英文单词（如 `AI`, `ML`, `CPU`, `GPU`）
- ✅ **会转换**：自定义热词映射表中的单词（不区分大小写）
- ❌ **不转换**：小写或混合大小写的英文单词（如 `ai`, `Ai`, `model`, `is`）
- ❌ **不转换**：中文文本

## 自定义映射

### 方法1：使用映射文件

创建或编辑 `eng_to_zh_phonetic_mapping.txt` 文件：

```
# 注释行
AI=诶艾
ML=艾姆艾勒
GPU=基皮由
```

### 方法2：代码中添加

```python
converter = EngToZhPhonetic()
converter.add_word_mapping('AI', '诶艾')
converter.add_letter_mapping('A', '诶')
```

## 集成到GPT-SoVITS

### 方案1：在文本输入前预处理

```python
from eng_to_zh_phonetic import convert_eng_to_zh_phonetic

# 在调用 get_tts_wav 之前
original_text = "我使用AI技术"
processed_text = convert_eng_to_zh_phonetic(original_text, convert_mode='smart')

# 然后使用 processed_text 进行TTS
# get_tts_wav(..., text=processed_text, text_language="all_zh", ...)
```

### 方案2：在webui输入框后处理

在 `inference_webui.py` 的 `get_tts_wav` 函数开始处添加：

```python
from eng_to_zh_phonetic import convert_eng_to_zh_phonetic

def get_tts_wav(...):
    # 预处理文本
    if text_language == "all_zh" or text_language == "zh":
        text = convert_eng_to_zh_phonetic(text, convert_mode='smart')
    
    # 原有的处理逻辑...
```

### 方案3：创建包装函数

```python
from eng_to_zh_phonetic import convert_eng_to_zh_phonetic
from GPT_SoVITS.inference_webui import get_tts_wav as original_get_tts_wav

def get_tts_wav_with_phonetic(*args, **kwargs):
    # 预处理文本参数
    if 'text' in kwargs:
        text_language = kwargs.get('text_language', 'auto')
        if text_language in ['all_zh', 'zh']:
            kwargs['text'] = convert_eng_to_zh_phonetic(kwargs['text'], convert_mode='smart')
    
    # 调用原始函数
    return original_get_tts_wav(*args, **kwargs)
```

## 内置映射

模块已内置常见技术术语的映射：
- AI, ML, DL, GPU, CPU
- API, HTTP, HTTPS, URL
- HTML, CSS, JS, JSON
- NLP, CV, OCR, CNN, RNN
- GPT, BERT, LLM, AGI
- iOS, Android, Windows, Linux
- SQL, NoSQL, MySQL, MongoDB
- Git, GitHub, Docker, Kubernetes
- AWS, Azure, GCP
- 等等...

## 注意事项

1. **映射优先级**：单词映射 > 字母映射
2. **大小写**：映射不区分大小写
3. **中文文本**：中文文本不会被转换
4. **标点符号**：标点符号保持原样
5. **数字**：数字保持原样

## 测试

运行测试：

```bash
python eng_to_zh_phonetic.py
```

## 扩展

如需添加更多映射，可以：
1. 编辑 `eng_to_zh_phonetic_mapping.txt` 文件
2. 或在代码中使用 `add_word_mapping()` 方法

