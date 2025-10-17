#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
流式TTS管理器
支持实时文本流式传输和语音合成
"""

import time
import threading
import queue
from typing import Optional, Callable, List
from collections import deque
from gpt_sovits_client import GPTSoVITSClient


class StreamingTTSManager:
    """流式TTS管理器"""
    
    def __init__(self, 
                 tts_client: GPTSoVITSClient,
                 chunk_size: int = 30,
                 min_chunk_size: int = 10,
                 max_chunk_size: int = 50,
                 split_punctuation: str = '。！？.!?，,;；',
                 overlap_chars: int = 3):
        """
        初始化流式TTS管理器
        
        Args:
            tts_client: TTS客户端
            chunk_size: 每次传给TTS的字符数
            min_chunk_size: 最小字符数
            max_chunk_size: 最大字符数
            split_punctuation: 切分标点符号
            overlap_chars: 语音片段重叠字符数
        """
        self.tts_client = tts_client
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.split_punctuation = split_punctuation
        self.overlap_chars = overlap_chars
        
        # 文本缓冲
        self.text_buffer = ""
        self.processed_length = 0
        self.is_processing = False
        
        # 音频队列和播放控制
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.current_audio_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.on_text_chunk: Optional[Callable[[str], None]] = None
        self.on_audio_ready: Optional[Callable[[str], None]] = None
        self.on_playback_complete: Optional[Callable[[], None]] = None
        
        # 线程控制
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 统计信息
        self.stats = {
            "total_chunks": 0,
            "total_characters": 0,
            "average_chunk_size": 0,
            "processing_time": 0
        }
    
    def set_callbacks(self,
                     on_text_chunk: Optional[Callable[[str], None]] = None,
                     on_audio_ready: Optional[Callable[[str], None]] = None,
                     on_playback_complete: Optional[Callable[[], None]] = None):
        """设置回调函数"""
        self.on_text_chunk = on_text_chunk
        self.on_audio_ready = on_audio_ready
        self.on_playback_complete = on_playback_complete
    
    def start_streaming(self):
        """开始流式处理"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.stop_event.clear()
        
        # 重置文本缓冲区和处理位置，确保新的响应从干净状态开始
        self.text_buffer = ""
        self.processed_length = 0
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        print("🎙️ 流式TTS处理已启动")
    
    def stop_streaming(self):
        """停止流式处理"""
        if not self.is_processing:
            return
        
        self.is_processing = False
        self.stop_event.set()
        
        # 处理剩余的文本
        if self.text_buffer.strip():
            self._process_remaining_text()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        print("⏹️ 流式TTS处理已停止")
    
    def add_text(self, text: str):
        """添加文本到流式处理"""
        if not text.strip():
            return
        
        self.text_buffer += text
        
        # 更新统计信息
        self.stats["total_characters"] += len(text)
        
        print(f"📝 添加文本: {text[:30]}... (总长度: {len(self.text_buffer)})")
    
    def _processing_loop(self):
        """处理循环"""
        while not self.stop_event.is_set():
            try:
                if len(self.text_buffer) - self.processed_length >= self.min_chunk_size:
                    # 检查是否可以切分
                    next_chunk = self._get_next_chunk()
                    
                    if next_chunk:
                        self._process_chunk(next_chunk)
                
                time.sleep(0.1)  # 避免CPU占用过高
                
            except Exception as e:
                print(f"❌ 处理循环异常: {e}")
                break
    
    def _get_next_chunk(self) -> Optional[str]:
        """获取下一个文本块"""
        if self.processed_length >= len(self.text_buffer):
            return None
        
        # 从已处理位置开始，不使用重叠
        start_pos = self.processed_length
        end_pos = start_pos + self.chunk_size
        
        # 如果文本不够长，取剩余部分
        if end_pos >= len(self.text_buffer):
            chunk = self.text_buffer[start_pos:]
            return chunk if chunk.strip() else None
        
        # 寻找合适的切分点
        chunk = self.text_buffer[start_pos:end_pos]
        
        # 向后寻找标点符号（句号、问号、感叹号优先）
        best_split = -1
        for i in range(len(chunk) - 1, -1, -1):
            if chunk[i] in '。！？.!?':
                best_split = i
                break
            elif chunk[i] in '，,;；' and best_split == -1:
                best_split = i
        
        # 如果找到合适的切分点
        if best_split > 0:
            end_pos = start_pos + best_split + 1
            chunk = self.text_buffer[start_pos:end_pos]
        
        # 确保块大小在合理范围内
        if len(chunk) < self.min_chunk_size and end_pos < len(self.text_buffer):
            # 如果块太小，尝试扩展到下一个句号
            extend_end = min(start_pos + self.max_chunk_size, len(self.text_buffer))
            search_chunk = self.text_buffer[start_pos:extend_end]
            
            # 寻找下一个句号
            for i in range(len(search_chunk)):
                if search_chunk[i] in '。！？.!?':
                    end_pos = start_pos + i + 1
                    chunk = self.text_buffer[start_pos:end_pos]
                    break
            else:
                # 如果没找到句号，使用最大长度
                chunk = search_chunk
        
        return chunk.strip() if chunk.strip() else None
    
    def _process_chunk(self, chunk: str):
        """处理文本块"""
        try:
            print(f"🔄 处理文本块: {chunk}")
            
            # 更新统计信息
            self.stats["total_chunks"] += 1
            self.stats["average_chunk_size"] = self.stats["total_characters"] / self.stats["total_chunks"]
            
            # 调用文本块回调
            if self.on_text_chunk:
                self.on_text_chunk(chunk)
            
            # 异步处理TTS
            tts_thread = threading.Thread(
                target=self._synthesize_chunk,
                args=(chunk,),
                daemon=True
            )
            tts_thread.start()
            
            # 更新处理位置（不减去重叠字符）
            self.processed_length += len(chunk)
            
        except Exception as e:
            print(f"❌ 处理文本块失败: {e}")
    
    def _synthesize_chunk(self, chunk: str):
        """合成语音块"""
        try:
            start_time = time.time()
            
            # 生成唯一的输出文件名
            timestamp = int(time.time() * 1000)  # 使用毫秒时间戳
            output_path = f"streaming_tts_{timestamp}.wav"
            
            # 调用TTS合成
            success = self.tts_client.text_to_speech(
                text=chunk,
                ref_audio_path="参考音频.wav",  # 使用固定的参考音频路径
                output_path=output_path,
                text_lang="zh",
                prompt_lang="zh",
                prompt_text="伊里奥斯的古代废墟是受国际保护的历史遗址。",
                top_k=5,
                top_p=0.8,
                temperature=0.8,
                speed_factor=1.0,
                text_split_method="cut4",
                batch_size=1,
                sample_steps=4
            )
            
            processing_time = time.time() - start_time
            self.stats["processing_time"] += processing_time
            
            if success:
                print(f"✅ 语音块合成成功: {chunk[:20]}... (耗时: {processing_time:.2f}秒)")
                
                # 将音频文件加入队列
                self.audio_queue.put(output_path)
                
                # 调用音频就绪回调
                if self.on_audio_ready:
                    self.on_audio_ready(output_path)
                
                # 开始播放（如果还没有播放）
                if not self.is_playing:
                    self._start_playback()
            else:
                print(f"❌ 语音块合成失败: {chunk[:20]}...")
                
        except Exception as e:
            print(f"❌ 合成语音块异常: {e}")
    
    def _start_playback(self):
        """开始播放"""
        if self.is_playing:
            return
        
        self.is_playing = True
        
        # 启动播放线程
        self.current_audio_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.current_audio_thread.start()
    
    def _playback_loop(self):
        """播放循环"""
        while self.is_playing:
            try:
                # 等待音频文件
                try:
                    audio_path = self.audio_queue.get(timeout=1.0)
                except queue.Empty:
                    # 检查是否还有更多音频要处理
                    if self.is_processing and (self.text_buffer and self.processed_length < len(self.text_buffer)):
                        continue
                    else:
                        # 没有更多音频，停止播放
                        break
                
                # 播放音频
                self._play_audio_file(audio_path)
                
                # 清理文件
                self._cleanup_file(audio_path)
                
            except Exception as e:
                print(f"❌ 播放循环异常: {e}")
                break
        
        self.is_playing = False
        
        # 调用播放完成回调
        if self.on_playback_complete:
            self.on_playback_complete()
    
    def _play_audio_file(self, audio_path: str):
        """播放音频文件"""
        try:
            import pygame
            
            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            pygame.mixer.music.unload()
            
        except ImportError:
            print("⚠️ 未安装pygame，无法播放音频")
        except Exception as e:
            print(f"❌ 播放音频失败: {e}")
    
    def _cleanup_file(self, file_path: str):
        """清理文件"""
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"⚠️ 清理文件失败: {e}")
    
    def _process_remaining_text(self):
        """处理剩余文本"""
        remaining = self.text_buffer[self.processed_length:]
        if remaining.strip():
            print(f"🔄 处理剩余文本: {remaining}")
            self._process_chunk(remaining)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.copy()
    
    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            "is_processing": self.is_processing,
            "is_playing": self.is_playing,
            "buffer_length": len(self.text_buffer),
            "processed_length": self.processed_length,
            "queue_size": self.audio_queue.qsize(),
            "stats": self.stats
        }
