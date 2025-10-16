
# SenseVoice + LLM 集成使用示例

## 方案一：API集成
from llm_asr_integration_api import SenseVoiceASR, LLMDialogueSystem

# 1. 启动SenseVoice API服务
# 在终端运行: python api.py

# 2. 使用API客户端
asr_client = SenseVoiceASR("http://localhost:50000")
dialogue_system = LLMDialogueSystem(asr_client)

# 3. 处理语音文件
result = dialogue_system.chat_with_voice("your_audio.wav", "auto")
print(f"用户语音: {result['user_speech']}")
print(f"LLM回复: {result['llm_response']}")

## 方案二：直接调用
from llm_asr_integration_direct import SenseVoiceASRDirect, LLMDialogueSystemDirect

# 1. 初始化
asr_client = SenseVoiceASRDirect(device="cuda:0")
dialogue_system = LLMDialogueSystemDirect(asr_client)

# 2. 处理语音
result = dialogue_system.process_voice_input("your_audio.wav", "auto")
print(f"用户语音: {result['user_speech']}")
print(f"LLM回复: {result['llm_response']}")

## 方案三：流式对话
from llm_asr_streaming_integration import StreamingLLMDialogue

# 1. 初始化流式对话
dialogue_system = StreamingLLMDialogue(asr_client, llm_client)
dialogue_system.start_conversation()

# 2. 实时录音对话
dialogue_system.record_and_process()
