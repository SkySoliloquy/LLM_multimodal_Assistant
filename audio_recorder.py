#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
音频录制模块
负责处理音频录制、格式转换和基本验证
"""

import threading
import time
import numpy as np
import pyaudio
from typing import List, Optional, Callable


class AudioRecorder:
    """音频录制器"""
    
    def __init__(self, 
                 chunk: int = 1024,
                 format: int = pyaudio.paInt16,
                 channels: int = 1,
                 rate: int = 16000,
                 min_duration: float = 0.5):
        """
        初始化音频录制器
        
        Args:
            chunk: 每次读取的帧数
            format: 音频格式
            channels: 声道数
            rate: 采样率
            min_duration: 最小录音时长（秒）
        """
        self.CHUNK = chunk
        self.FORMAT = format
        self.CHANNELS = channels
        self.RATE = rate
        self.MIN_DURATION = min_duration
        
        # 录音状态
        self.is_recording = False
        self.audio_frames: List[bytes] = []
        self.audio: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.record_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.on_recording_start: Optional[Callable] = None
        self.on_recording_stop: Optional[Callable] = None
        self.on_audio_processed: Optional[Callable[[np.ndarray], None]] = None
    
    def set_callbacks(self, 
                     on_start: Optional[Callable] = None,
                     on_stop: Optional[Callable] = None,
                     on_processed: Optional[Callable[[np.ndarray], None]] = None):
        """设置回调函数"""
        self.on_recording_start = on_start
        self.on_recording_stop = on_stop
        self.on_audio_processed = on_processed
    
    def start_recording(self) -> bool:
        """
        开始录音
        
        Returns:
            是否成功开始录音
        """
        if self.is_recording:
            return False
            
        self.is_recording = True
        self.audio_frames = []
        
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            # 调用开始录音回调
            if self.on_recording_start:
                self.on_recording_start()
            
            # 启动录音线程
            self.record_thread = threading.Thread(target=self._record_loop)
            self.record_thread.daemon = True
            self.record_thread.start()
            
            return True
            
        except Exception as e:
            print(f"录音启动失败: {e}")
            self.is_recording = False
            return False
    
    def stop_recording(self) -> bool:
        """
        停止录音
        
        Returns:
            是否成功停止录音
        """
        if not self.is_recording:
            return False
            
        self.is_recording = False
        
        # 等待录音线程结束
        if self.record_thread and self.record_thread.is_alive():
            self.record_thread.join(timeout=1.0)
        
        # 关闭音频流
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        
        # 调用停止录音回调
        if self.on_recording_stop:
            self.on_recording_stop()
        
        # 处理录音数据
        if self.audio_frames:
            return self._process_audio()
        else:
            print("❌ 没有录到音频数据")
            return False
    
    def _record_loop(self) -> None:
        """录音循环"""
        while self.is_recording:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                self.audio_frames.append(data)
            except Exception as e:
                print(f"录音过程中出错: {e}")
                break
    
    def _process_audio(self) -> bool:
        """
        处理录音数据
        
        Returns:
            是否成功处理音频
        """
        try:
            # 将录音数据转换为numpy数组
            audio_data = b''.join(self.audio_frames)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # 转换为float32并归一化到[-1, 1]范围
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # 检查音频长度
            duration = len(audio_array) / self.RATE
            if duration < self.MIN_DURATION:
                print(f"❌ 录音时间太短 ({duration:.2f}秒)，请重新录音")
                return False
            
            print(f"📊 录音时长: {duration:.2f}秒")
            
            # 调用音频处理回调
            if self.on_audio_processed:
                self.on_audio_processed(audio_array)
            
            return True
            
        except Exception as e:
            print(f"❌ 处理音频失败: {e}")
            return False
    
    def get_audio_duration(self) -> float:
        """获取当前录音的时长"""
        if not self.audio_frames:
            return 0.0
        
        total_frames = len(self.audio_frames) * self.CHUNK
        return total_frames / self.RATE
    
    def is_recording_active(self) -> bool:
        """检查是否正在录音"""
        return self.is_recording
    
    def get_recording_info(self) -> dict:
        """获取录音配置信息"""
        return {
            "chunk": self.CHUNK,
            "format": self.FORMAT,
            "channels": self.CHANNELS,
            "rate": self.RATE,
            "min_duration": self.MIN_DURATION,
            "is_recording": self.is_recording
        }
