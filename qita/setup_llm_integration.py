#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
SenseVoice + LLM 集成设置脚本
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_dependencies():
    """检查依赖项"""
    required_packages = [
        "torch",
        "torchaudio", 
        "funasr",
        "gradio",
        "requests",
        "soundfile",
        "pyaudio",
        "numpy"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 未安装")
    
    if missing_packages:
        print(f"\n需要安装的包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    return True

def setup_model_paths():
    """设置模型路径"""
    print("\n=== 模型路径设置 ===")
    
    # 检查SenseVoice模型
    sensevoice_paths = [
        r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall",
    ]
    
    model_found = False
    for path in sensevoice_paths:
        if os.path.exists(path) or path == r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall":
            print(f"✅ 找到SenseVoice模型: {path}")
            model_found = True
            break
    
    if not model_found:
        print("❌ 未找到SenseVoice模型")
        print("请确保模型已下载到正确位置")
    
    return model_found

def create_config_file():
    """创建配置文件"""
    config = {
        "sensevoice": {
            "model_dir": r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall",
            "device": "cuda:0",
            "language": "auto",
            "use_itn": True
        },
        "api": {
            "host": "localhost",
            "port": 50000,
            "base_url": "http://localhost:50000"
        },
        "llm": {
            "type": "custom",  # "custom", "openai", "claude", etc.
            "model_name": "your_llm_model",
            "api_key": "your_api_key"
        },
        "audio": {
            "sample_rate": 16000,
            "chunk_size": 1024,
            "channels": 1
        }
    }
    
    config_file = "llm_asr_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 配置文件已创建: {config_file}")
    return config_file

def create_example_usage():
    """创建使用示例"""
    example_code = '''
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
'''
    
    with open("usage_example.py", 'w', encoding='utf-8') as f:
        f.write(example_code)
    
    print("✅ 使用示例已创建: usage_example.py")

def main():
    """主函数"""
    print("=== SenseVoice + LLM 集成设置 ===")
    
    # 1. 检查依赖
    print("\n1. 检查依赖项...")
    if not check_dependencies():
        print("\n请先安装缺失的依赖项")
        return
    
    # 2. 检查模型
    print("\n2. 检查模型...")
    if not setup_model_paths():
        print("\n请确保SenseVoice模型已正确安装")
        return
    
    # 3. 创建配置文件
    print("\n3. 创建配置文件...")
    config_file = create_config_file()
    
    # 4. 创建使用示例
    print("\n4. 创建使用示例...")
    create_example_usage()
    
    print("\n=== 设置完成 ===")
    print("接下来你可以:")
    print("1. 启动SenseVoice API: python api.py")
    print("2. 运行WebUI: python webui.py") 
    print("3. 使用集成脚本: python llm_asr_integration_api.py")
    print("4. 查看使用示例: usage_example.py")

if __name__ == "__main__":
    main()
