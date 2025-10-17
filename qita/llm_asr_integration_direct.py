#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
SenseVoice + LLM 对话集成方案 - 直接调用版本
"""

import torch
import torchaudio
import numpy as np
from typing import Optional, Dict, Any, Union
import os
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

class SenseVoiceASRDirect:
    """SenseVoice ASR 直接调用客户端"""
    
    def __init__(self, model_dir: str = r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall", device: str = "cuda:0"):
        """
        初始化SenseVoice模型
        
        Args:
            model_dir: 模型路径或名称
            device: 设备 ("cuda:0", "cpu")
        """
        self.device = device
        self.model_dir = model_dir
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            print("正在加载SenseVoice模型...")
            self.model = AutoModel(
                model=self.model_dir,
                trust_remote_code=True,
                remote_code="./model.py",
                vad_model=r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch",
                vad_kwargs={"max_single_segment_time": 30000},
                device=self.device,
            )
            print("模型加载成功!")
        except Exception as e:
            print(f"模型加载失败: {str(e)}")
            raise e
    
    def transcribe_audio_file(self, audio_file_path: str, language: str = "auto", use_itn: bool = True) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            audio_file_path: 音频文件路径
            language: 语言设置 ("auto", "zh", "en", "yue", "ja", "ko")
            use_itn: 是否使用逆文本规范化
        
        Returns:
            包含转录结果的字典
        """
        try:
            if not os.path.exists(audio_file_path):
                return {"error": f"音频文件不存在: {audio_file_path}"}
            
            # 执行语音识别
            result = self.model.generate(
                input=audio_file_path,
                cache={},
                language=language,
                use_itn=use_itn,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
            
            if result and len(result) > 0:
                raw_text = result[0]["text"]
                clean_text = rich_transcription_postprocess(raw_text)
                
                return {
                    "success": True,
                    "raw_text": raw_text,
                    "clean_text": clean_text,
                    "language": language,
                    "file_path": audio_file_path
                }
            else:
                return {"error": "未识别到语音内容"}
                
        except Exception as e:
            return {"error": f"转录错误: {str(e)}"}
    
    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000, 
                            language: str = "auto", use_itn: bool = True) -> Dict[str, Any]:
        """
        转录音频数据
        
        Args:
            audio_data: 音频numpy数组
            sample_rate: 采样率
            language: 语言设置
            use_itn: 是否使用逆文本规范化
        
        Returns:
            包含转录结果的字典
        """
        try:
            # 确保音频数据格式正确
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(-1)  # 转为单声道
            
            # 重采样到16kHz
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                audio_tensor = torch.from_numpy(audio_data).float()
                audio_data = resampler(audio_tensor[None, :])[0, :].numpy()
            
            # 执行语音识别
            result = self.model.generate(
                input=audio_data,
                cache={},
                language=language,
                use_itn=use_itn,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
            
            if result and len(result) > 0:
                raw_text = result[0]["text"]
                clean_text = rich_transcription_postprocess(raw_text)
                
                return {
                    "success": True,
                    "raw_text": raw_text,
                    "clean_text": clean_text,
                    "language": language,
                    "sample_rate": 16000
                }
            else:
                return {"error": "未识别到语音内容"}
                
        except Exception as e:
            return {"error": f"转录错误: {str(e)}"}

class LLMDialogueSystemDirect:
    """LLM对话系统 - 直接调用版本"""
    
    def __init__(self, asr_client: SenseVoiceASRDirect, llm_client=None):
        self.asr = asr_client
        self.llm = llm_client  # 这里可以集成你的LLM客户端
        self.conversation_history = []  # 对话历史
    
    def process_voice_input(self, audio_input: Union[str, np.ndarray], 
                          language: str = "auto", sample_rate: int = 16000) -> Dict[str, Any]:
        """
        处理语音输入并生成LLM回复
        
        Args:
            audio_input: 音频文件路径或音频数据
            language: 语音语言
            sample_rate: 音频采样率（仅当audio_input为numpy数组时使用）
        
        Returns:
            包含完整对话信息的字典
        """
        # 1. 语音转文字
        if isinstance(audio_input, str):
            asr_result = self.asr.transcribe_audio_file(audio_input, language)
        else:
            asr_result = self.asr.transcribe_audio_data(audio_input, sample_rate, language)
        
        if "error" in asr_result:
            return {
                "success": False,
                "error": asr_result["error"],
                "user_speech": "",
                "llm_response": ""
            }
        
        transcribed_text = asr_result["clean_text"]
        print(f"识别结果: {transcribed_text}")
        
        # 2. 发送给LLM处理
        if self.llm:
            try:
                llm_response = self.llm.chat(transcribed_text)
            except Exception as e:
                llm_response = f"LLM处理错误: {str(e)}"
        else:
            # 模拟LLM回复
            llm_response = f"我听到了: {transcribed_text}。这是一个模拟的LLM回复。"
        
        # 3. 保存对话历史
        conversation_turn = {
            "user_speech": transcribed_text,
            "llm_response": llm_response,
            "language": language,
            "timestamp": self._get_timestamp()
        }
        self.conversation_history.append(conversation_turn)
        
        return {
            "success": True,
            "user_speech": transcribed_text,
            "llm_response": llm_response,
            "language": language,
            "raw_asr_result": asr_result
        }
    
    def get_conversation_history(self) -> list:
        """获取对话历史"""
        return self.conversation_history
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def batch_process_audio_files(self, audio_files: list, language: str = "auto") -> list:
        """
        批量处理音频文件
        
        Args:
            audio_files: 音频文件路径列表
            language: 语言设置
        
        Returns:
            处理结果列表
        """
        results = []
        for audio_file in audio_files:
            result = self.process_voice_input(audio_file, language)
            results.append({
                "file": audio_file,
                "result": result
            })
        return results

# 使用示例和测试
def main():
    """使用示例"""
    
    # 1. 初始化ASR客户端
    try:
        asr_client = SenseVoiceASRDirect(
            model_dir=r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall",  # 或者使用本地路径
            device="cuda:0"  # 如果没有GPU，改为"cpu"
        )
    except Exception as e:
        print(f"ASR客户端初始化失败: {e}")
        return
    
    # 2. 初始化对话系统
    dialogue_system = LLMDialogueSystemDirect(asr_client)
    
    # 3. 处理语音输入
    test_audio_files = [
        "参考音频备份.wav"
    ]
    
    for audio_file in test_audio_files:
        if os.path.exists(audio_file):
            print(f"\n=== 处理音频文件: {audio_file} ===")
            result = dialogue_system.process_voice_input(audio_file, "auto")
            
            if result["success"]:
                print(f"用户语音: {result['user_speech']}")
                print(f"LLM回复: {result['llm_response']}")
                print(f"识别语言: {result['language']}")
            else:
                print(f"处理失败: {result['error']}")
        else:
            print(f"音频文件不存在: {audio_file}")
    
    # 4. 显示对话历史
    print("\n=== 对话历史 ===")
    history = dialogue_system.get_conversation_history()
    for i, turn in enumerate(history, 1):
        print(f"轮次 {i} ({turn['timestamp']}):")
        print(f"  用户: {turn['user_speech']}")
        print(f"  LLM: {turn['llm_response']}")

if __name__ == "__main__":
    main()
