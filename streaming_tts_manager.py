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
from AddWindows import NewWindowPrinter

class StreamingTTSManager:
    """流式TTS管理器"""

    def __init__(self, 
                 tts_client: GPTSoVITSClient,
                 chunk_size=None,
                 min_chunk_size=None,
                 max_chunk_size=None,
                 split_punctuation=None,
                 overlap_chars=None):
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
        
        # 文本缓冲
        self.text_buffer = ""
        self.processed_length = 0
        self.is_processing = False

        # 首句低延迟控制
        self.first_delay = True

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

        #创建新窗口
        self.sensor_printer = NewWindowPrinter(window_name="语音合成数据窗口")

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

        # 重置首句延迟标志
        self.first_delay = True

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
        
        #print(f"📝 添加文本: {text[:30]}... (总长度: {len(self.text_buffer)})\n")

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
        # 检查已处理的文本长度是否大于或等于文本缓冲区的总长度
        # 如果是，说明没有更多文本需要处理，返回None
        if self.processed_length >= len(self.text_buffer):
            return None


        # 首句降低最小字符数，因为首句通常是打招呼
        if self.first_delay:
            self.first_delay = False
            self.temp = [self.chunk_size,self.min_chunk_size]
            self.chunk_size = 6
            self.min_chunk_size = 1
        else:
            self.chunk_size = self.temp[0]
            self.min_chunk_size = self.temp[1]


        # 从已处理位置开始
        start_pos = self.processed_length

        # 允许的最大查看范围（向前看，避免在句中截断）
        preferred_end = start_pos + self.chunk_size
        max_end = min(start_pos + self.max_chunk_size, len(self.text_buffer))

        # 当前可用文本不足最小块时，暂不切分（等待更多文本到来）
        available_len = len(self.text_buffer) - start_pos
        if available_len < self.min_chunk_size and not self.stop_event.is_set():
            return None

        # 在 [start_pos, max_end) 范围内寻找最佳切分点
        search_text = self.text_buffer[start_pos:max_end]

        strong_punct = '。！？.!?'
        weak_punct = '，,;；：'

        def find_split(text: str, prefer_len: int):
            # 先在强标点中找：优先选择 <= prefer_len 范围内的最后一个，其次选择 > prefer_len 的第一个
            last_before = -1
            first_after = -1
            for idx, ch in enumerate(text):
                if ch in strong_punct:
                    if idx <= prefer_len - 1:
                        last_before = idx
                    elif first_after == -1:
                        first_after = idx
            if last_before != -1:
                return last_before + 1
            if first_after != -1:
                return first_after + 1

            # 没有强标点，尝试弱标点，策略同上
            last_before = -1
            first_after = -1
            for idx, ch in enumerate(text):
                if ch in weak_punct:
                    if idx <= prefer_len - 1:
                        last_before = idx
                    elif first_after == -1:
                        first_after = idx
            if last_before != -1:
                return last_before + 1
            if first_after != -1:
                return first_after + 1

            return -1

        # 期望切分点基于 chunk_size
        prefer_len = min(self.chunk_size, len(search_text))
        split_offset = find_split(search_text, prefer_len)

        if split_offset == -1:
            # 若没有任何标点：
            # 1) 如果尚未达到最大查看窗口且未停止，就等待更多文本，避免句中截断
            if len(search_text) < (self.max_chunk_size - 0) and not self.stop_event.is_set():
                return None
            # 2) 若已达到最大窗口或已停止，才按窗口末尾切分
            end_pos = start_pos + len(search_text)
            chunk = self.text_buffer[start_pos:end_pos]
        else:
            end_pos = start_pos + split_offset
            chunk = self.text_buffer[start_pos:end_pos]

        # 去除首尾空白
        chunk = chunk.strip()

        # 避免出现以弱标点开头的块（例如以“，”开头），这种情况通常来源于前一块未包含该标点。
        # 如果不为空且首字符是弱标点，同时块长度过短，则尝试扩展一点点（不超过max_chunk_size）
        if chunk and chunk[0] in weak_punct and (end_pos < len(self.text_buffer)):
            # 再尝试在后续少量字符内找到一个更自然的切分点
            extra_end = min(end_pos + (self.min_chunk_size if self.min_chunk_size > 0 else 5), len(self.text_buffer))
            extra_search = self.text_buffer[start_pos:extra_end]
            extra_split = find_split(extra_search, len(chunk) + 1)
            if extra_split != -1 and extra_split > len(chunk):
                end_pos = start_pos + extra_split
                chunk = self.text_buffer[start_pos:end_pos].strip()

        return chunk if chunk else None

    def _process_chunk(self, chunk: str):
        """处理文本块"""
        try:
            #打印处理的文本块
            #self.sensor_printer.print_to_window(f"🔄 处理文本块: {chunk}")
            
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
            # 记录程序开始执行的时间，使用time模块的time()函数获取当前时间戳
            start_time = time.time()

            # 生成唯一的输出文件名
            timestamp = int(time.time() * 1000)  # 使用毫秒时间戳
            output_path = f"streaming_tts_{timestamp}.wav"
            
            # 调用TTS合成
            success = self.tts_client.text_to_speech(
                text=chunk,
                ref_audio_path=r"D:\Project\SenseVoice-main\resource\【中立_neutral】这个嘛，你或许起初只知道一点儿，然后不停的问呀问，最后就都搞清楚了。.wav",
                output_path=output_path,
                text_lang="zh",
                prompt_lang="zh",
                prompt_text="这个嘛，你或许起初只知道一点儿，然后不停的问呀问，最后就都搞清楚了。",
                top_k=5,
                top_p=1,
                temperature=1,
                speed_factor=0.95,
                text_split_method="cut4",
                batch_size=4,

            )

            processing_time = time.time() - start_time
            
            if success:
                self.sensor_printer.print_to_window(f"✅ 语音块合成成功: {chunk} (耗时: {processing_time:.2f}秒)\n")
                # 将音频文件加入队列
                self.audio_queue.put(output_path)
                
                # 调用音频就绪回调
                if self.on_audio_ready:
                    self.on_audio_ready(output_path)
                
                # 开始播放（如果还没有播放）
                if not self.is_playing:
                    self._start_playback()
            else:
                self.sensor_printer.print_to_window(f"❌ 语音块合成失败: {chunk[:20]}...")
                
        except Exception as e:
            self.sensor_printer.print_to_window(f"❌ 合成语音块异常: {e}")
    
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
            #print(f"🔄 处理剩余文本: {remaining}")
            self.sensor_printer.print_to_window(f"🔄 处理剩余文本: {remaining}\n")
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
