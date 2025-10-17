#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
配置管理模块
统一管理所有配置参数
"""

import os
from typing import Dict, Any


class Config:
    """配置管理类"""
    
    # ASR模型配置
    ASR_MODEL_DIR = r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall"
    VAD_MODEL_DIR = r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch"
    ASR_DEVICE = "cuda:0"  # 可选: "cpu", "cuda:0", "cuda:1" 等
    
    # LLM配置
    LLM_API_KEY = "YDHHpjDZwdGh7SBOgNGn50_LcNLnCpq84tjZ_fRECrs7wwoOG4SWNPyRPsX1Z7Zj7hFZgiJW2MqzDGIl98U-7Q"
    LLM_BASE_URL = "https://www.sophnet.com/api/open-apis/v1"
    LLM_MODEL_NAME = "DeepSeek-V3.2-Exp"
    
    # 系统提示词文件路径
    SYSTEM_PROMPT_FILE = "System_Content.txt"
    
    # 对话管理配置
    MAX_HISTORY_ROUNDS = 10  # 最大保留的对话轮数
    
    # 音频录制配置
    AUDIO_CHUNK = 1024
    AUDIO_FORMAT = "paInt16"  # pyaudio格式
    AUDIO_CHANNELS = 1
    AUDIO_RATE = 16000
    AUDIO_MIN_DURATION = 0.5  # 最小录音时长（秒）
    
    # 用户界面配置
    UI_SHOW_STATS = True
    UI_SHOW_HISTORY_PREVIEW = True
    UI_HISTORY_PREVIEW_LENGTH = 50
    
    # 按键配置
    KEY_RECORD = 'z'
    KEY_TEXT_INPUT = 't'
    KEY_SHOW_HISTORY = 'h'
    KEY_CLEAR_HISTORY = 'c'
    KEY_QUIT = 'q'
    
    @classmethod
    def get_asr_config(cls) -> Dict[str, Any]:
        """获取ASR配置"""
        return {
            "model_dir": cls.ASR_MODEL_DIR,
            "vad_model_dir": cls.VAD_MODEL_DIR,
            "device": cls.ASR_DEVICE
        }
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """获取LLM配置"""
        return {
            "api_key": cls.LLM_API_KEY,
            "base_url": cls.LLM_BASE_URL,
            "model_name": cls.LLM_MODEL_NAME
        }
    
    @classmethod
    def get_audio_config(cls) -> Dict[str, Any]:
        """获取音频配置"""
        import pyaudio
        return {
            "chunk": cls.AUDIO_CHUNK,
            "format": getattr(pyaudio, cls.AUDIO_FORMAT),
            "channels": cls.AUDIO_CHANNELS,
            "rate": cls.AUDIO_RATE,
            "min_duration": cls.AUDIO_MIN_DURATION
        }
    
    @classmethod
    def get_chat_config(cls) -> Dict[str, Any]:
        """获取对话配置"""
        return {
            "max_history": cls.MAX_HISTORY_ROUNDS,
            "system_prompt_file": cls.SYSTEM_PROMPT_FILE
        }
    
    @classmethod
    def get_ui_config(cls) -> Dict[str, Any]:
        """获取UI配置"""
        return {
            "show_stats": cls.UI_SHOW_STATS,
            "show_history_preview": cls.UI_SHOW_HISTORY_PREVIEW,
            "history_preview_length": cls.UI_HISTORY_PREVIEW_LENGTH,
            "keys": {
                "record": cls.KEY_RECORD,
                "text_input": cls.KEY_TEXT_INPUT,
                "show_history": cls.KEY_SHOW_HISTORY,
                "clear_history": cls.KEY_CLEAR_HISTORY,
                "quit": cls.KEY_QUIT
            }
        }
    
    @classmethod
    def load_system_prompt(cls) -> str:
        """加载系统提示词"""
        try:
            if os.path.exists(cls.SYSTEM_PROMPT_FILE):
                with open(cls.SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
                    return f.read().strip()
            else:
                print(f"⚠️ 系统提示词文件 {cls.SYSTEM_PROMPT_FILE} 不存在，使用默认提示词")
                return "你是一个有用的AI助手，请用中文回答用户的问题。"
        except Exception as e:
            print(f"❌ 读取系统提示词文件失败: {e}")
            return "你是一个有用的AI助手，请用中文回答用户的问题。"
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置"""
        errors = []
        
        # 检查ASR模型路径
        if not os.path.exists(cls.ASR_MODEL_DIR):
            errors.append(f"ASR模型路径不存在: {cls.ASR_MODEL_DIR}")
        
        # 检查VAD模型路径
        if not os.path.exists(cls.VAD_MODEL_DIR):
            errors.append(f"VAD模型路径不存在: {cls.VAD_MODEL_DIR}")
        
        # 检查系统提示词文件
        if not os.path.exists(cls.SYSTEM_PROMPT_FILE):
            errors.append(f"系统提示词文件不存在: {cls.SYSTEM_PROMPT_FILE}")
        
        # 检查API密钥
        if not cls.LLM_API_KEY or len(cls.LLM_API_KEY) < 10:
            errors.append("LLM API密钥无效")
        
        if errors:
            print("❌ 配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print("✅ 配置验证通过")
        return True
    
    @classmethod
    def print_config_summary(cls):
        """打印配置摘要"""
        print("=" * 50)
        print("配置摘要:")
        print("=" * 50)
        print(f"ASR模型: {cls.ASR_MODEL_DIR}")
        print(f"ASR设备: {cls.ASR_DEVICE}")
        print(f"LLM模型: {cls.LLM_MODEL_NAME}")
        print(f"LLM API: {cls.LLM_BASE_URL}")
        print(f"最大对话轮数: {cls.MAX_HISTORY_ROUNDS}")
        print(f"音频采样率: {cls.AUDIO_RATE}Hz")
        print(f"系统提示词文件: {cls.SYSTEM_PROMPT_FILE}")
        print("=" * 50)
