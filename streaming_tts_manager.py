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
                 chunk_size: int = 40,
                 min_chunk_size: int = 10,
                 max_chunk_size: int = 80,
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
        self.on_first_audio_playback: Optional[Callable[[], None]] = None  # 第一次开始播放时触发
        
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

        # 停止控制
        self.interrupted = False  # 是否被中断
        self.interrupted_text = ""  # 中断时的已处理文本
        self.interrupted_position = 0  # 中断位置

    def set_callbacks(self,
                      on_text_chunk: Optional[Callable[[str], None]] = None,
                      on_audio_ready: Optional[Callable[[str], None]] = None,
                      on_playback_complete: Optional[Callable[[], None]] = None,
                      on_first_audio_playback: Optional[Callable[[], None]] = None):
        """设置回调函数"""
        self.on_text_chunk = on_text_chunk
        self.on_audio_ready = on_audio_ready
        self.on_playback_complete = on_playback_complete
        self.on_first_audio_playback = on_first_audio_playback

    def start_streaming(self):
        """开始流式处理"""
        if self.is_processing:
            return

        self.is_processing = True
        self.stop_event.clear()

        # 重置文本缓冲区和处理位置，确保新的响应从干净状态开始
        self.text_buffer = ""
        self.processed_length = 0
        
        # 重置中断状态
        self.interrupted = False
        self.interrupted_text = ""
        self.interrupted_position = 0
        # 重置首段播放触发标记
        self._first_playback_fired = False
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        print("🎙️ 流式TTS处理已启动")
    
    def stop_streaming(self):
        """停止流式处理（LLM完成时的正常停止）"""
        if not self.is_processing:
            return
        
        print("📝 LLM输出已完成，文本处理将停止（等待音频播放完成）")
        
        # 处理剩余的文本
        if self.text_buffer.strip():
            self._process_remaining_text()
        
        # 停止文本处理，但不清除 stop_event，让音频继续播放
        self.is_processing = False
        
        print("⏹️ 文本处理已停止（音频继续播放中）")
    
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
        if self.processed_length >= len(self.text_buffer):
            return None

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
        weak_punct = '，,;；'

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
                #ref_audio_path=r"D:\Project\SenseVoice-main\U_Offical.mp3",  # 使用固定的参考音频路径
                ref_audio_path="D:\Project\SenseVoice-main\Athna.wav",
                output_path=output_path,
                text_lang="zh",
                prompt_lang="zh",
                #prompt_text="新年特别直播，用味觉巡游这片大地。",
                prompt_text="伊利奥斯的古代废墟是受国际保护的历史遗址。",
                top_k=10,
                top_p=0.8,
                temperature=1,
                speed_factor=1,
                text_split_method="cut4",
                batch_size=4,
                sample_steps=4
            )
            
            processing_time = time.time() - start_time
            self.stats["processing_time"] += processing_time
            
            if success:
                print(f"✅ 语音块合成成功: {chunk} (耗时: {processing_time:.2f}秒)")
                
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
                # 首先检查是否被用户主动中断（只检查interrupted标志）
                if self.interrupted:
                    print("🛑 播放循环检测到用户中断，清空队列")
                    # 用户主动中断，清空队列并退出
                    while not self.audio_queue.empty():
                        try:
                            remaining_audio = self.audio_queue.get_nowait()
                            self._cleanup_file(remaining_audio)
                        except queue.Empty:
                            break
                    break
                
                # 等待音频文件
                try:
                    audio_path = self.audio_queue.get(timeout=1.0)
                except queue.Empty:
                    # 检查是否还有更多音频要处理
                    if not self.is_processing and self.audio_queue.empty():
                        # 文本处理已完成且队列为空，停止播放
                        print("✅ 所有音频已播放完成")
                        break
                    elif self.is_processing and (self.text_buffer and self.processed_length < len(self.text_buffer)):
                        # 还有文本在处理，继续等待
                        continue
                    else:
                        # 队列为空但有文本在处理，继续等待
                        continue

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
            
            # 如果已经被中断，跳过播放
            if self.interrupted:
                print("⚠️ 音频已被中断，跳过播放")
                return
            
            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            # 首次开始播放时回调（用于外部计时停止）
            if not getattr(self, "_first_playback_fired", False):
                self._first_playback_fired = True
                if self.on_first_audio_playback:
                    try:
                        self.on_first_audio_playback()
                    except Exception as _:
                        pass
            
            # 等待播放完成，只检查用户主动中断
            while pygame.mixer.music.get_busy():
                # 只有用户主动中断时才停止播放
                if self.interrupted:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                    print("🛑 播放被用户中断")
                    return
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

    def interrupt_streaming(self):
        """中断流式处理"""
        # 无论is_processing状态如何，都允许中断
        if self.interrupted:
            return  # 已经中断过了

        print("🛑 中断流式TTS处理...")
        
        # 设置中断标志（必须在最前面）
        self.interrupted = True
        
        # 强制停止播放循环
        self.is_playing = False
        
        # 停止当前播放的音频（优先执行）
        self._stop_current_playback()
        
        # 清空等待播放的音频队列
        self._clear_audio_queue()
        
        if self.is_processing:
            # 记录已处理的文本
            self.interrupted_text = self.text_buffer[:self.processed_length]
            self.interrupted_position = self.processed_length
            
            # 立即停止处理循环
            self.stop_event.set()
            
            # 标记is_processing为False，但保留相关状态
            self.is_processing = False
            
            print(f"✅ 已中断，处理了 {self.interrupted_position} 个字符")
        else:
            print(f"✅ 已中断当前播放")

    def _clear_audio_queue(self):
        """清空音频队列"""
        while not self.audio_queue.empty():
            try:
                audio_path = self.audio_queue.get_nowait()
                self._cleanup_file(audio_path)
            except queue.Empty:
                break

    def _stop_current_playback(self):
        """停止当前播放"""
        try:
            import pygame
            # 强制停止pygame mixer
            pygame.mixer.pause()
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            # 重新初始化以便后续可以继续播放
            pygame.mixer.init()
            print("🛑 已强制停止当前音频播放")
        except Exception as e:
            print(f"⚠️ 停止播放时出错: {e}")

    def get_current_playing_text(self) -> str:
        """获取当前正在播放的文字"""
        # 返回已处理的文本内容
        return self.interrupted_text

    def get_interrupted_state(self):
        """获取中断状态"""
        return {
            "interrupted": self.interrupted,
            "text_so_far": self.interrupted_text if self.interrupted_text else self.text_buffer[:self.processed_length],
            "position": self.interrupted_position if self.interrupted_position > 0 else self.processed_length
        }

    def reset_interrupt_state(self):
        """重置中断状态"""
        self.interrupted = False
        self.interrupted_text = ""
        self.interrupted_position = 0
