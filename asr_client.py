#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
语音识别客户端模块
负责处理语音转文字功能
"""

import numpy as np
import torch
import torchaudio
from typing import Dict, Any, Optional
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


class SenseVoiceASRDirect:
    """SenseVoice ASR 直接调用客户端"""
    
    def __init__(self, model_dir: str, device: str = "cuda:0", vad_model_dir: Optional[str] = None):
        """
        初始化SenseVoice模型
        
        Args:
            model_dir: 模型路径或名称
            device: 设备 ("cuda:0", "cpu")
            vad_model_dir: VAD模型路径，如果为None则使用默认路径
        """
        self.device = device
        self.model_dir = model_dir
        self.vad_model_dir = vad_model_dir or r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch"
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """加载模型"""
        try:
            print("正在加载SenseVoice模型...")
            self.model = AutoModel(
                model=self.model_dir,
                trust_remote_code=True,
                remote_code="./model.py",
                vad_model=self.vad_model_dir,
                vad_kwargs={"max_single_segment_time": 30000},
                device=self.device,
            )
            print("✅ SenseVoice模型加载成功!")
        except Exception as e:
            print(f"❌ SenseVoice模型加载失败: {str(e)}")
            raise e
    
    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "auto") -> Dict[str, Any]:
        """
        转录音频数据
        
        Args:
            audio_data: 音频numpy数组
            sample_rate: 采样率
            language: 语言设置
            
        Returns:
            包含转录结果的字典
        """
        try:
            # 预处理音频数据
            processed_audio = self._preprocess_audio(audio_data, sample_rate)
            
            # 执行语音识别
            result = self.model.generate(
                input=processed_audio,
                cache={},
                language=language,
                use_itn=True,
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
                    "language": language
                }
            else:
                return {"error": "未识别到语音内容"}
                
        except Exception as e:
            return {"error": f"转录错误: {str(e)}"}
    
    def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        预处理音频数据
        
        Args:
            audio_data: 原始音频数据
            sample_rate: 采样率
            
        Returns:
            预处理后的音频数据
        """
        # 确保音频数据格式正确
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(-1)  # 转为单声道
        
        # 确保数据类型为float32
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # 重采样到16kHz
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            audio_tensor = torch.from_numpy(audio_data).float()
            audio_data = resampler(audio_tensor[None, :])[0, :].numpy()
            # 确保重采样后也是float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
        
        return audio_data
    
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None
    
    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            "model_dir": self.model_dir,
            "device": self.device,
            "vad_model_dir": self.vad_model_dir,
            "is_loaded": str(self.is_model_loaded())
        }
