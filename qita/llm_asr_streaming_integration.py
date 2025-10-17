#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
SenseVoice + LLM 流式对话集成方案
支持实时语音输入和流式LLM回复
"""

import threading
import queue
import time
try:
    import pyaudio
    import wave
except ImportError:
    print("警告: pyaudio未安装，流式录音功能将不可用")
    pyaudio = None
    wave = None
import numpy as np
from typing import Optional, Callable, Dict, Any
import json
from datetime import datetime
import os

# 假设你已经有了前面的SenseVoiceASRDirect类
from llm_asr_integration_direct import SenseVoiceASRDirect, LLMDialogueSystemDirect

class AudioRecorder:
    """音频录制器"""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024, channels: int = 1):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.audio_format = pyaudio.paInt16
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.audio_data = []
    
    def start_recording(self):
        """开始录音"""
        if self.is_recording:
            return
        
        self.audio_data = []
        self.stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        self.is_recording = True
        
        # 启动录音线程
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.start()
    
    def stop_recording(self) -> np.ndarray:
        """停止录音并返回音频数据"""
        if not self.is_recording:
            return np.array([])
        
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.recording_thread:
            self.recording_thread.join()
        
        # 转换为numpy数组
        audio_array = np.frombuffer(b''.join(self.audio_data), dtype=np.int16)
        audio_array = audio_array.astype(np.float32) / 32768.0  # 归一化
        
        return audio_array
    
    def _record_audio(self):
        """录音线程"""
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk_size)
                self.audio_data.append(data)
            except Exception as e:
                print(f"录音错误: {e}")
                break

class StreamingLLMDialogue:
    """流式LLM对话系统"""
    
    def __init__(self, asr_client: SenseVoiceASRDirect, llm_client=None):
        self.asr = asr_client
        self.llm = llm_client
        self.audio_recorder = AudioRecorder()
        self.is_running = False
        self.conversation_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.conversation_history = []
        
        # 回调函数
        self.on_speech_detected: Optional[Callable] = None
        self.on_llm_response: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    def start_conversation(self):
        """开始对话"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self._process_conversations)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        print("对话系统已启动，按回车键开始录音，再次按回车键停止录音...")
    
    def stop_conversation(self):
        """停止对话"""
        self.is_running = False
        if hasattr(self, 'processing_thread'):
            self.processing_thread.join()
    
    def record_and_process(self):
        """录制语音并处理"""
        try:
            print("开始录音...")
            self.audio_recorder.start_recording()
            
            # 等待用户停止录音
            input("按回车键停止录音...")
            
            print("停止录音，正在处理...")
            audio_data = self.audio_recorder.stop_recording()
            
            if len(audio_data) > 0:
                # 添加到处理队列
                self.conversation_queue.put({
                    "type": "audio",
                    "data": audio_data,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                print("没有录制到音频数据")
                
        except Exception as e:
            error_msg = f"录音处理错误: {str(e)}"
            print(error_msg)
            if self.on_error:
                self.on_error(error_msg)
    
    def _process_conversations(self):
        """处理对话队列"""
        while self.is_running:
            try:
                # 等待队列中的任务
                task = self.conversation_queue.get(timeout=1.0)
                
                if task["type"] == "audio":
                    self._process_audio_input(task)
                
                self.conversation_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                error_msg = f"处理错误: {str(e)}"
                print(error_msg)
                if self.on_error:
                    self.on_error(error_msg)
    
    def _process_audio_input(self, task: Dict[str, Any]):
        """处理音频输入"""
        try:
            audio_data = task["data"]
            timestamp = task["timestamp"]
            
            # 语音识别
            print("正在进行语音识别...")
            asr_result = self.asr.transcribe_audio_data(
                audio_data, 
                sample_rate=16000, 
                language="auto"
            )
            
            if "error" in asr_result:
                error_msg = f"语音识别失败: {asr_result['error']}"
                print(error_msg)
                if self.on_error:
                    self.on_error(error_msg)
                return
            
            transcribed_text = asr_result["clean_text"]
            print(f"识别结果: {transcribed_text}")
            
            if self.on_speech_detected:
                self.on_speech_detected(transcribed_text)
            
            # LLM处理
            if self.llm:
                print("正在生成LLM回复...")
                try:
                    llm_response = self.llm.chat(transcribed_text)
                except Exception as e:
                    llm_response = f"LLM处理错误: {str(e)}"
            else:
                llm_response = f"我听到了: {transcribed_text}。这是一个模拟的LLM回复。"
            
            print(f"LLM回复: {llm_response}")
            
            # 保存对话历史
            conversation_turn = {
                "timestamp": timestamp,
                "user_speech": transcribed_text,
                "llm_response": llm_response,
                "asr_result": asr_result
            }
            self.conversation_history.append(conversation_turn)
            
            if self.on_llm_response:
                self.on_llm_response(llm_response)
                
        except Exception as e:
            error_msg = f"音频处理错误: {str(e)}"
            print(error_msg)
            if self.on_error:
                self.on_error(error_msg)
    
    def get_conversation_history(self) -> list:
        """获取对话历史"""
        return self.conversation_history
    
    def save_conversation_to_file(self, filename: str):
        """保存对话历史到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
            print(f"对话历史已保存到: {filename}")
        except Exception as e:
            print(f"保存对话历史失败: {e}")

class SimpleLLMClient:
    """简单的LLM客户端模拟"""
    
    def __init__(self):
        self.responses = [
            "这是一个很有趣的问题。",
            "我理解你的想法。",
            "让我想想如何回答这个问题。",
            "基于你的描述，我认为...",
            "这确实是一个值得深入讨论的话题。"
        ]
        self.response_index = 0
    
    def chat(self, text: str) -> str:
        """模拟LLM聊天"""
        # 简单的关键词匹配
        if "你好" in text or "hello" in text.lower():
            return "你好！很高兴与你对话！"
        elif "再见" in text or "bye" in text.lower():
            return "再见！期待下次与你交流！"
        elif "时间" in text:
            return f"当前时间是: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            response = self.responses[self.response_index % len(self.responses)]
            self.response_index += 1
            return response

def main():
    """流式对话示例"""
    
    print("=== SenseVoice + LLM 流式对话系统 ===")
    
    # 1. 初始化ASR客户端
    try:
        asr_client = SenseVoiceASRDirect(device="cuda:0")
    except Exception as e:
        print(f"ASR客户端初始化失败: {e}")
        return
    
    # 2. 初始化简单的LLM客户端
    llm_client = SimpleLLMClient()
    
    # 3. 初始化流式对话系统
    dialogue_system = StreamingLLMDialogue(asr_client, llm_client)
    
    # 4. 设置回调函数
    def on_speech_detected(text):
        print(f"🎤 检测到语音: {text}")
    
    def on_llm_response(response):
        print(f"🤖 LLM回复: {response}")
    
    def on_error(error):
        print(f"❌ 错误: {error}")
    
    dialogue_system.on_speech_detected = on_speech_detected
    dialogue_system.on_llm_response = on_llm_response
    dialogue_system.on_error = on_error
    
    # 5. 启动对话系统
    dialogue_system.start_conversation()
    
    try:
        while True:
            print("\n" + "="*50)
            print("选择操作:")
            print("1. 录音对话")
            print("2. 查看对话历史")
            print("3. 保存对话历史")
            print("4. 退出")
            
            choice = input("请输入选择 (1-4): ").strip()
            
            if choice == "1":
                dialogue_system.record_and_process()
            elif choice == "2":
                history = dialogue_system.get_conversation_history()
                if history:
                    print("\n=== 对话历史 ===")
                    for i, turn in enumerate(history, 1):
                        print(f"\n轮次 {i} ({turn['timestamp']}):")
                        print(f"  用户: {turn['user_speech']}")
                        print(f"  LLM: {turn['llm_response']}")
                else:
                    print("暂无对话历史")
            elif choice == "3":
                filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                dialogue_system.save_conversation_to_file(filename)
            elif choice == "4":
                break
            else:
                print("无效选择，请重试")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    finally:
        dialogue_system.stop_conversation()
        print("对话系统已停止")

if __name__ == "__main__":
    main()
