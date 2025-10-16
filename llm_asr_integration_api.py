#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
SenseVoice + LLM 对话集成方案 - API版本
"""

import requests
import json
import os
from typing import Optional, Dict, Any
import soundfile as sf
import io
import numpy as np

class SenseVoiceASR:
    """SenseVoice ASR API客户端"""
    
    def __init__(self, api_url: str = "http://localhost:50000"):
        self.api_url = api_url
        self.asr_endpoint = f"{api_url}/api/v1/asr"
    
    def transcribe_audio(self, audio_file_path: str, language: str = "auto") -> str:
        """
        转录音频文件
        
        Args:
            audio_file_path: 音频文件路径
            language: 语言设置 ("auto", "zh", "en", "yue", "ja", "ko")
        
        Returns:
            转录的文本
        """
        try:
            with open(audio_file_path, 'rb') as f:
                files = {'files': f}
                data = {
                    'lang': language,
                    'keys': os.path.basename(audio_file_path)
                }
                
                response = requests.post(self.asr_endpoint, files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('result') and len(result['result']) > 0:
                        # 返回清理后的文本
                        return result['result'][0].get('clean_text', '')
                    else:
                        return "未识别到语音内容"
                else:
                    return f"API调用失败: {response.status_code}"
                    
        except Exception as e:
            return f"转录错误: {str(e)}"
    
    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "auto") -> str:
        """
        转录音频数据
        
        Args:
            audio_data: 音频numpy数组
            sample_rate: 采样率
            language: 语言设置
        
        Returns:
            转录的文本
        """
        try:
            # 将音频数据保存为临时文件
            temp_file = io.BytesIO()
            sf.write(temp_file, audio_data, sample_rate, format='WAV')
            temp_file.seek(0)
            
            files = {'files': ('temp.wav', temp_file, 'audio/wav')}
            data = {'lang': language, 'keys': 'temp_audio'}
            
            response = requests.post(self.asr_endpoint, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result') and len(result['result']) > 0:
                    return result['result'][0].get('clean_text', '')
                else:
                    return "未识别到语音内容"
            else:
                return f"API调用失败: {response.status_code}"
                
        except Exception as e:
            return f"转录错误: {str(e)}"

class LLMDialogueSystem:
    """LLM对话系统集成"""
    
    def __init__(self, asr_client: SenseVoiceASR, llm_client=None):
        self.asr = asr_client
        self.llm = llm_client  # 这里可以集成你的LLM客户端
    
    def process_voice_input(self, audio_input, language: str = "auto") -> str:
        """
        处理语音输入并生成LLM回复
        
        Args:
            audio_input: 音频文件路径或音频数据
            language: 语音语言
        
        Returns:
            LLM回复文本
        """
        # 1. 语音转文字
        if isinstance(audio_input, str):
            # 文件路径
            transcribed_text = self.asr.transcribe_audio(audio_input, language)
        else:
            # 音频数据
            transcribed_text = self.asr.transcribe_audio_data(audio_input, language=language)
        
        if not transcribed_text or transcribed_text.startswith("转录错误") or transcribed_text.startswith("API调用失败"):
            return f"语音识别失败: {transcribed_text}"
        
        print(f"识别结果: {transcribed_text}")
        
        # 2. 发送给LLM处理
        if self.llm:
            llm_response = self.llm.chat(transcribed_text)
            return llm_response
        else:
            # 模拟LLM回复
            return f"我听到了: {transcribed_text}。这是一个模拟的LLM回复。"
    
    def chat_with_voice(self, audio_file_path: str, language: str = "auto") -> Dict[str, str]:
        """
        语音对话接口
        
        Returns:
            包含用户语音转录和LLM回复的字典
        """
        transcribed_text = self.asr.transcribe_audio(audio_file_path, language)
        
        if self.llm:
            llm_response = self.llm.chat(transcribed_text)
        else:
            llm_response = f"基于你的语音输入'{transcribed_text}'，这是我的回复。"
        
        return {
            "user_speech": transcribed_text,
            "llm_response": llm_response,
            "language": language
        }

# 使用示例
def main():
    """使用示例"""
    
    # 1. 初始化ASR客户端
    asr_client = SenseVoiceASR("http://localhost:50000")
    
    # 2. 初始化对话系统
    dialogue_system = LLMDialogueSystem(asr_client)
    
    # 3. 处理语音输入
    audio_file = "参考音频备份.wav"  # 替换为你的音频文件
    if os.path.exists(audio_file):
        result = dialogue_system.chat_with_voice(audio_file, "auto")
        
        print("=== 语音对话结果 ===")
        print(f"用户语音: {result['user_speech']}")
        print(f"LLM回复: {result['llm_response']}")
        print(f"识别语言: {result['language']}")
    else:
        print(f"音频文件不存在: {audio_file}")

if __name__ == "__main__":
    main()
