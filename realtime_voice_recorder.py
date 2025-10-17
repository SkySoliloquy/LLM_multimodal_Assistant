#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
实时语音录制器
支持连续语音录制和静音检测
"""

import time
import threading
import numpy as np
import pyaudio
from typing import Optional, Callable
from collections import deque
from scipy import signal
import statistics


class RealtimeVoiceRecorder:
    """实时语音录制器"""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_size: int = 1024,
                 silence_threshold: float = 0.8,
                 min_speech_length: float = 1,
                 max_speech_length: float = 30.0,
                 vad_sensitivity: float = 0.9):
        """
        初始化实时语音录制器
        
        Args:
            sample_rate: 采样率
            chunk_size: 每次读取的音频块大小
            silence_threshold: 静音检测阈值（秒）
            min_speech_length: 最小语音长度（秒）
            max_speech_length: 最大语音长度（秒）
            vad_sensitivity: VAD敏感度 (0.0-1.0，越小越敏感)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.min_speech_length = min_speech_length
        self.max_speech_length = max_speech_length
        self.vad_sensitivity = vad_sensitivity
        
        # 音频参数
        self.format = pyaudio.paInt16
        self.channels = 1
        
        # 状态控制
        self.is_recording = False
        self.is_speech_detected = False
        self.current_speech_start = None
        self.last_speech_time = None
        
        # 改进的防抖机制
        self.speech_detection_debounce_time = 0.05  # 减少防抖时间提高响应性
        self.silence_detection_debounce_time = 0.1  # 静音检测防抖
        self.last_detection_time = 0
        self.last_silence_detection_time = 0
        
        # 音频数据缓存
        self.audio_buffer = deque(maxlen=int(sample_rate * max_speech_length))
        self.speech_buffer = []
        
        # 当前语音段缓存（独立于主缓冲区）
        self.current_speech_buffer = []
        
        # 回调函数
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_audio_data: Optional[Callable] = None
        
        # 线程控制
        self.recording_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 改进的VAD参数
        self.noise_baseline_samples = 50  # 用于建立噪声基线的样本数
        self.energy_history = deque(maxlen=200)  # 能量历史
        self.spectral_centroid_history = deque(maxlen=100)  # 频谱质心历史
        self.zero_crossing_history = deque(maxlen=100)  # 过零率历史
        
        # 自适应阈值
        self.energy_threshold = 500
        self.noise_baseline = 100
        self.spectral_threshold = 0.3
        self.zcr_threshold = 0.1
        
        # 状态计数器（用于稳定性检测）
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        self.min_speech_frames = int(0.1 * sample_rate / chunk_size)  # 最少语音帧数
        self.min_silence_frames = int(0.2 * sample_rate / chunk_size)  # 最少静音帧数
        
        # 初始化音频
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
    def set_callbacks(self, 
                     on_speech_start: Optional[Callable] = None,
                     on_speech_end: Optional[Callable] = None,
                     on_audio_data: Optional[Callable] = None):
        """设置回调函数"""
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_audio_data = on_audio_data
    
    def start_recording(self):
        """开始录制"""
        if self.is_recording:
            return
        
        try:
            self.is_recording = True
            self.stop_event.clear()
            
            # 初始化音频流（不使用回调，直接读取）
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            # 启动录制线程
            self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
            self.recording_thread.start()
            
            print("🎤 实时语音录制已启动")
            
        except Exception as e:
            print(f"❌ 启动实时录制失败: {e}")
            self.is_recording = False
    
    def stop_recording(self):
        """停止录制"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        self.stop_event.set()
        
        # 等待录制线程结束
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)
        
        # 关闭音频流
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"⚠️ 关闭音频流时出现异常: {e}")
            finally:
                self.stream = None
        
        print("⏹️ 实时语音录制已停止")
    
    def _recording_loop(self):
        """录制循环"""
        while not self.stop_event.is_set() and self.is_recording:
            try:
                if self.stream and self.stream.is_active():
                    # 读取音频数据
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    # 添加到主缓冲区（用于历史记录）
                    self.audio_buffer.extend(audio_data)
                    
                    # 添加到当前语音段缓冲区（用于当前语音检测）
                    self.current_speech_buffer.extend(audio_data)
                    
                    # 调用音频数据回调
                    if self.on_audio_data:
                        self.on_audio_data(audio_data)
                    
                    # 检测语音活动
                    self._detect_speech(audio_data)
                else:
                    # 如果流不活跃，稍等片刻
                    time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 录制循环异常: {e}")
                break
            except:
                # 捕获所有其他异常，避免线程崩溃
                break
    
    def _detect_speech(self, audio_data: np.ndarray):
        """改进的语音活动检测算法"""
        current_time = time.time()
        
        # 提取音频特征
        features = self._extract_audio_features(audio_data)
        
        # 更新历史数据
        self.energy_history.append(features['energy'])
        self.spectral_centroid_history.append(features['spectral_centroid'])
        self.zero_crossing_history.append(features['zero_crossing_rate'])
        
        # 自适应阈值更新
        self._update_adaptive_thresholds()
        
        # 语音活动检测
        is_speech_frame = self._is_speech_frame(features)
        
        # 状态机逻辑
        if is_speech_frame:
            self.speech_frame_count += 1
            self.silence_frame_count = 0
            
            # 更新最后语音时间
            if self.speech_frame_count >= self.min_speech_frames:
                self.last_speech_time = current_time
                
                if not self.is_speech_detected:
                    # 开始检测到语音
                    self._start_speech_detection(current_time)
        else:
            self.silence_frame_count += 1
            self.speech_frame_count = 0
            
            # 检查语音结束
            if self.is_speech_detected and self.last_speech_time:
                silence_duration = current_time - self.last_speech_time
                
                if (self.silence_frame_count >= self.min_silence_frames and 
                    silence_duration >= self.silence_threshold):
                    speech_duration = current_time - self.current_speech_start
                    
                    if speech_duration >= self.min_speech_length:
                        self._end_speech_detection()
                    else:
                        print(f"⚠️ 语音段太短 ({speech_duration:.2f}秒)，忽略")
                        self._reset_speech_state()
    
    def _extract_audio_features(self, audio_data: np.ndarray) -> dict:
        """提取音频特征用于语音检测"""
        # 转换为浮点数
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # 1. 能量特征
        energy = np.mean(audio_float ** 2)
        
        # 2. RMS特征
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        # 3. 频谱质心（语音的"亮度"）
        if len(audio_float) > 0:
            # 使用FFT计算频谱
            fft = np.fft.fft(audio_float)
            magnitude = np.abs(fft[:len(fft)//2])
            freqs = np.fft.fftfreq(len(audio_float), 1/self.sample_rate)[:len(fft)//2]
            
            if np.sum(magnitude) > 0:
                spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
            else:
                spectral_centroid = 0
        else:
            spectral_centroid = 0
        
        # 4. 过零率（Zero Crossing Rate）
        zero_crossings = np.sum(np.diff(np.sign(audio_float)) != 0)
        zero_crossing_rate = zero_crossings / len(audio_float) if len(audio_float) > 0 else 0
        
        # 5. 频谱滚降点（Spectral Rolloff）
        if len(magnitude) > 0 and np.sum(magnitude) > 0:
            cumsum_magnitude = np.cumsum(magnitude)
            rolloff_threshold = 0.85 * cumsum_magnitude[-1]
            rolloff_idx = np.where(cumsum_magnitude >= rolloff_threshold)[0]
            spectral_rolloff = freqs[rolloff_idx[0]] if len(rolloff_idx) > 0 else freqs[-1]
        else:
            spectral_rolloff = 0
        
        # 6. 最大幅度
        max_amplitude = np.max(np.abs(audio_float))
        
        return {
            'energy': energy,
            'rms': rms,
            'spectral_centroid': spectral_centroid,
            'zero_crossing_rate': zero_crossing_rate,
            'spectral_rolloff': spectral_rolloff,
            'max_amplitude': max_amplitude
        }
    
    def _update_adaptive_thresholds(self):
        """更新自适应阈值"""
        if len(self.energy_history) < self.noise_baseline_samples:
            return
        
        # 更新噪声基线
        recent_energies = list(self.energy_history)[-self.noise_baseline_samples:]
        self.noise_baseline = np.percentile(recent_energies, 25)  # 使用25%分位数作为噪声基线
        
        # 更新能量阈值（基于噪声基线和历史数据）
        if len(self.energy_history) >= 50:
            # 计算动态阈值
            energy_mean = np.mean(list(self.energy_history)[-50:])
            energy_std = np.std(list(self.energy_history)[-50:])
            
            # 自适应阈值：噪声基线 + 敏感度调整
            base_threshold = self.noise_baseline * (2.0 + self.vad_sensitivity)
            adaptive_threshold = base_threshold + energy_std * 0.5
            
            self.energy_threshold = max(adaptive_threshold, self.noise_baseline * 1.5)
        
        # 更新频谱质心阈值
        if len(self.spectral_centroid_history) >= 20:
            spectral_mean = np.mean(list(self.spectral_centroid_history)[-20:])
            self.spectral_threshold = spectral_mean * 0.8
        
        # 更新过零率阈值
        if len(self.zero_crossing_history) >= 20:
            zcr_mean = np.mean(list(self.zero_crossing_history)[-20:])
            self.zcr_threshold = zcr_mean * 1.2
    
    def _is_speech_frame(self, features: dict) -> bool:
        """判断当前帧是否为语音帧"""
        # 多重条件判断
        conditions = []
        
        # 1. 能量条件
        energy_condition = features['energy'] > self.energy_threshold
        conditions.append(energy_condition)
        
        # 2. 最大幅度条件
        amplitude_condition = features['max_amplitude'] > 0.01  # 避免非常微弱的信号
        conditions.append(amplitude_condition)
        
        # 3. 频谱质心条件（语音通常有特定的频谱特征）
        if len(self.spectral_centroid_history) >= 5:
            spectral_condition = features['spectral_centroid'] > self.spectral_threshold
            conditions.append(spectral_condition)
        
        # 4. 过零率条件（语音的过零率通常在一定范围内）
        if len(self.zero_crossing_history) >= 5:
            zcr_condition = (features['zero_crossing_rate'] > self.zcr_threshold * 0.5 and 
                           features['zero_crossing_rate'] < self.zcr_threshold * 3.0)
            conditions.append(zcr_condition)
        
        # 5. 能量与噪声基线的比值
        snr_condition = features['energy'] > self.noise_baseline * (1.5 + self.vad_sensitivity)
        conditions.append(snr_condition)
        
        # 需要满足大部分条件才认为是语音
        speech_score = sum(conditions) / len(conditions)
        
        # 根据敏感度调整判断阈值
        threshold = 0.6 - self.vad_sensitivity * 0.2  # 敏感度越高，阈值越低
        
        return speech_score >= threshold
    
    def _start_speech_detection(self, current_time: float):
        """开始语音检测"""
        self.is_speech_detected = True
        self.current_speech_start = current_time
        self.speech_buffer = []
        
        # 清空当前语音段缓冲区，开始新的语音段
        self.current_speech_buffer = []
        
        if self.on_speech_start:
            self.on_speech_start()
        
        print(f"🗣️ 检测到语音开始 (能量: {self.energy_history[-1]:.4f}, 阈值: {self.energy_threshold:.4f})")
    
    def _end_speech_detection(self):
        """结束语音检测"""
        speech_duration = time.time() - self.current_speech_start
        print(f"📝 语音结束，时长: {speech_duration:.2f}秒")
        
        # 处理语音段
        self._process_speech_segment()
        
        # 重置状态
        self._reset_speech_state()
    
    def _reset_speech_state(self):
        """重置语音状态"""
        self.is_speech_detected = False
        self.current_speech_start = None
        self.last_speech_time = None
        self.speech_buffer = []
        self.speech_frame_count = 0
        self.silence_frame_count = 0
    
    def _calculate_dynamic_silence_threshold(self, speech_duration: float) -> float:
        """计算动态静音阈值"""
        # 基础静音阈值
        base_threshold = self.silence_threshold
        
        # 根据语音长度调整
        if speech_duration < 1.0:
            # 短语音需要更短的静音时间
            return base_threshold * 0.6
        elif speech_duration < 3.0:
            # 中等长度语音
            return base_threshold
        else:
            # 长语音需要更长的静音时间，确保完整
            return base_threshold * 1.5
    
    def _process_speech_segment(self):
        """处理语音段"""
        try:
            # 使用当前语音段缓冲区，而不是主缓冲区
            speech_data = np.array(list(self.current_speech_buffer))
            
            if len(speech_data) > 0:
                speech_duration = len(speech_data) / self.sample_rate
                print(f"📝 处理语音段，长度: {speech_duration:.2f}秒")
                
                # 语音完整性检测
                if self._is_speech_complete(speech_data):
                    if self.on_speech_end:
                        self.on_speech_end(speech_data)
                else:
                    print("⚠️ 语音段不完整，等待更多数据...")
                    # 不处理不完整的语音段，继续等待
                    return
                
                # 清空当前语音段缓冲区，避免残留数据影响下次识别
                self.current_speech_buffer = []
            
        except Exception as e:
            print(f"❌ 处理语音段失败: {e}")
    
    def _is_speech_complete(self, speech_data: np.ndarray) -> bool:
        """改进的语音完整性检测"""
        if len(speech_data) == 0:
            return False
        
        # 转换为浮点数
        audio_float = speech_data.astype(np.float32) / 32768.0
        
        # 计算语音的统计特征
        energy = np.mean(np.abs(audio_float))
        rms = np.sqrt(np.mean(audio_float**2))
        max_amplitude = np.max(np.abs(audio_float))
        
        # 语音长度检查
        speech_duration = len(speech_data) / self.sample_rate
        if speech_duration < 0.1:  # 太短的语音段
            return False
        
        # 能量检查 - 确保有足够的信号强度
        if energy < 0.001:  # 能量太低
            return False
        
        # 检测语音结尾衰减（改进版）
        if len(speech_data) > 1600:  # 至少0.1秒的音频
            # 将语音分为前、中、后三段
            segment_length = len(speech_data) // 3
            if segment_length >= 100:  # 确保每段有足够的样本
                front_segment = audio_float[:segment_length]
                middle_segment = audio_float[segment_length:2*segment_length]
                back_segment = audio_float[2*segment_length:]
                
                # 计算各段的能量
                front_energy = np.mean(np.abs(front_segment))
                middle_energy = np.mean(np.abs(middle_segment))
                back_energy = np.mean(np.abs(back_segment))
                
                # 如果后段能量明显低于前段和中段，认为语音完整
                if (back_energy < front_energy * 0.4 and 
                    back_energy < middle_energy * 0.4 and
                    front_energy > 0.001 and middle_energy > 0.001):
                    return True
        
        # 检查语音的稳定性（避免检测到噪声）
        if speech_duration > 0.5:  # 较长的语音
            # 计算语音的方差，稳定的语音应该有适中的方差
            audio_variance = np.var(audio_float)
            if audio_variance < 1e-6:  # 方差太小，可能是噪声
                return False
            elif audio_variance > 0.1:  # 方差太大，可能是突发噪声
                return False
        
        # 如果语音足够长且能量合理，认为完整
        if speech_duration > 1.0 and energy > 0.001:
            return True
        
        # 对于短语音，要求更高的能量
        if speech_duration <= 1.0 and energy > 0.005:
            return True
        
        # 默认认为完整（避免无限等待）
        return True
    
    def get_current_audio_buffer(self) -> np.ndarray:
        """获取当前音频缓冲区数据"""
        return np.array(list(self.audio_buffer))
    
    def clear_buffer(self):
        """清空音频缓冲区"""
        self.audio_buffer.clear()
        self.speech_buffer = []
        self.current_speech_buffer = []
        
        # 重置语音检测相关状态
        self.is_speech_detected = False
        self.current_speech_start = None
        self.last_speech_time = None
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        
        # 重置历史数据和阈值
        self.energy_history.clear()
        self.spectral_centroid_history.clear()
        self.zero_crossing_history.clear()
        
        # 重置阈值到初始值
        self.energy_threshold = 500
        self.noise_baseline = 100
        self.spectral_threshold = 0.3
        self.zcr_threshold = 0.1
        
        print("🧹 音频缓冲区和检测状态已重置")
    
    def is_active(self) -> bool:
        """检查是否正在录制"""
        return self.is_recording
    
    def get_status(self) -> dict:
        """获取录制状态"""
        current_time = time.time()
        
        # 计算当前能量（如果有历史数据）
        current_energy = self.energy_history[-1] if len(self.energy_history) > 0 else 0
        current_spectral = self.spectral_centroid_history[-1] if len(self.spectral_centroid_history) > 0 else 0
        current_zcr = self.zero_crossing_history[-1] if len(self.zero_crossing_history) > 0 else 0
        
        return {
            "is_recording": self.is_recording,
            "is_speech_detected": self.is_speech_detected,
            "buffer_size": len(self.audio_buffer),
            "current_speech_buffer_size": len(self.current_speech_buffer),
            "current_speech_duration": current_time - self.current_speech_start if self.current_speech_start else 0,
            
            # VAD相关状态
            "energy_threshold": self.energy_threshold,
            "noise_baseline": self.noise_baseline,
            "current_energy": current_energy,
            "current_spectral_centroid": current_spectral,
            "current_zero_crossing_rate": current_zcr,
            
            # 历史数据大小
            "energy_history_size": len(self.energy_history),
            "spectral_history_size": len(self.spectral_centroid_history),
            "zcr_history_size": len(self.zero_crossing_history),
            
            # 帧计数
            "speech_frame_count": self.speech_frame_count,
            "silence_frame_count": self.silence_frame_count,
            
            # 阈值设置
            "vad_sensitivity": self.vad_sensitivity,
            "silence_threshold": self.silence_threshold,
            "min_speech_length": self.min_speech_length,
            
            # 检测质量指标
            "snr_ratio": current_energy / self.noise_baseline if self.noise_baseline > 0 else 0,
            "is_above_energy_threshold": current_energy > self.energy_threshold,
            "is_above_spectral_threshold": current_spectral > self.spectral_threshold if len(self.spectral_centroid_history) >= 5 else False
        }
    
    def print_debug_info(self):
        """打印调试信息"""
        status = self.get_status()
        print("\n" + "="*50)
        print("🎤 实时语音录制器调试信息")
        print("="*50)
        print(f"录制状态: {'🔴 录制中' if status['is_recording'] else '⏸️ 已停止'}")
        print(f"语音检测: {'🗣️ 检测到语音' if status['is_speech_detected'] else '🔇 静音'}")
        print(f"当前语音时长: {status['current_speech_duration']:.2f}秒")
        print()
        print("📊 VAD参数:")
        print(f"  能量阈值: {status['energy_threshold']:.4f}")
        print(f"  噪声基线: {status['noise_baseline']:.4f}")
        print(f"  当前能量: {status['current_energy']:.4f}")
        print(f"  信噪比: {status['snr_ratio']:.2f}")
        print(f"  超过能量阈值: {'✅' if status['is_above_energy_threshold'] else '❌'}")
        print()
        print("🎵 音频特征:")
        print(f"  频谱质心: {status['current_spectral_centroid']:.2f} Hz")
        print(f"  过零率: {status['current_zero_crossing_rate']:.4f}")
        print(f"  超过频谱阈值: {'✅' if status['is_above_spectral_threshold'] else '❌'}")
        print()
        print("📈 状态计数:")
        print(f"  语音帧数: {status['speech_frame_count']}")
        print(f"  静音帧数: {status['silence_frame_count']}")
        print(f"  历史数据量: 能量({status['energy_history_size']}), 频谱({status['spectral_history_size']}), 过零率({status['zcr_history_size']})")
        print("="*50)
    
    def set_vad_sensitivity(self, sensitivity: float):
        """动态调整VAD敏感度"""
        if 0.0 <= sensitivity <= 1.0:
            self.vad_sensitivity = sensitivity
            print(f"🎚️ VAD敏感度已调整为: {sensitivity:.2f}")
        else:
            print("❌ 敏感度必须在0.0-1.0之间")
    
    def calibrate_noise_baseline(self, duration: float = 3.0):
        """校准噪声基线"""
        print(f"🔧 开始校准噪声基线，请保持安静 {duration} 秒...")
        
        # 清空历史数据
        self.energy_history.clear()
        self.spectral_centroid_history.clear()
        self.zero_crossing_history.clear()
        
        # 记录开始时间
        start_time = time.time()
        
        def calibration_callback(audio_data):
            if time.time() - start_time < duration:
                features = self._extract_audio_features(audio_data)
                self.energy_history.append(features['energy'])
                self.spectral_centroid_history.append(features['spectral_centroid'])
                self.zero_crossing_history.append(features['zero_crossing_rate'])
        
        # 临时设置回调
        old_callback = self.on_audio_data
        self.on_audio_data = calibration_callback
        
        # 等待校准完成
        time.sleep(duration)
        
        # 恢复原回调
        self.on_audio_data = old_callback
        
        # 更新阈值
        self._update_adaptive_thresholds()
        
        print(f"✅ 噪声基线校准完成！")
        print(f"   噪声基线: {self.noise_baseline:.4f}")
        print(f"   能量阈值: {self.energy_threshold:.4f}")
        print(f"   采集样本: {len(self.energy_history)}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop_recording()
            if hasattr(self, 'audio') and self.audio:
                self.audio.terminate()
        except:
            pass  # 析构函数中忽略异常
