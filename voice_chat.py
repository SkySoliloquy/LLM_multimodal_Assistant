#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
语音对话系统 - 结合ASR和LLM，支持多轮对话
按z键录音，语音转文字后发送给模型
"""

import os
import time
import threading
import pyaudio
import wave
import numpy as np
from openai import OpenAI
from typing import Optional, Dict, Any
import keyboard
import torch
import torchaudio
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

class ChatManager:
    """多轮对话管理器"""
    
    def __init__(self, system_prompt, max_history=10):
        """
        初始化对话管理器
        :param system_prompt: 系统提示词
        :param max_history: 最大保留的对话轮数（不包括system消息）
        """
        self.system_prompt = system_prompt
        self.max_history = max_history
        self.history = []
    
    def add_user_message(self, content):
        """添加用户消息到历史"""
        self.history.append({"role": "user", "content": content})
        self._trim_history()
    
    def add_assistant_message(self, content):
        """添加助手消息到历史"""
        self.history.append({"role": "assistant", "content": content})
        self._trim_history()
    
    def _trim_history(self):
        """修剪历史记录，保持在最大长度内"""
        if len(self.history) > self.max_history * 2:  # 每轮对话有user和assistant两条消息
            # 保留最近的对话
            self.history = self.history[-(self.max_history * 2):]
    
    def get_messages(self):
        """获取完整的消息列表（包括system prompt）"""
        return [{"role": "system", "content": self.system_prompt}] + self.history
    
    def clear_history(self):
        """清空对话历史"""
        self.history = []
    
    def get_history_count(self):
        """获取当前历史记录条数"""
        return len(self.history)
    
    def display_history(self):
        """显示对话历史"""
        print("\n" + "="*50)
        print("对话历史:")
        print("="*50)
        for i, msg in enumerate(self.history, 1):
            role = "用户" if msg["role"] == "user" else "助手"
            print(f"{i}. [{role}]: {msg['content'][:50]}{'...' if len(msg['content']) > 50 else ''}")
        print("="*50 + "\n")

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
            
            # 执行语音识别
            result = self.model.generate(
                input=audio_data,
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

class VoiceChatSystem:
    """语音对话系统"""
    
    def __init__(self):
        # 初始化ASR客户端（直接调用）
        self.asr = SenseVoiceASRDirect(
            model_dir=r"C:\Users\Administrator\.cache\modelscope\hub\models\iic\SenseVoiceSmall",
            device="cuda:0"
        )
        
        # 读取系统提示词
        with open("system_content.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 初始化LLM客户端
        self.client = OpenAI(
            api_key="YDHHpjDZwdGh7SBOgNGn50_LcNLnCpq84tjZ_fRECrs7wwoOG4SWNPyRPsX1Z7Zj7hFZgiJW2MqzDGIl98U-7Q",
            base_url="https://www.sophnet.com/api/open-apis/v1"
        )
        
        # 初始化对话管理器
        self.chat_manager = ChatManager(system_prompt, max_history=10)
        
        # 录音参数
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.RECORD_SECONDS = 5  # 最大录音时长
        
        # 录音状态
        self.is_recording = False
        self.audio_frames = []
        self.audio = None
        self.stream = None
        
    def start_recording(self):
        """开始录音"""
        if self.is_recording:
            return
            
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
            
            print("🎤 开始录音... (松开z键停止)")
            
            # 录音线程
            def record():
                while self.is_recording:
                    data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    self.audio_frames.append(data)
            
            record_thread = threading.Thread(target=record)
            record_thread.daemon = True
            record_thread.start()
            
        except Exception as e:
            print(f"录音启动失败: {e}")
            self.is_recording = False
    
    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
            
        print("⏹️ 录音结束")
        
        # 处理录音数据
        if self.audio_frames:
            self.process_audio()
        else:
            print("❌ 没有录到音频数据")
    
    def process_audio(self):
        """处理录音数据"""
        try:
            # 将录音数据转换为numpy数组
            audio_data = b''.join(self.audio_frames)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # 转换为float32并归一化到[-1, 1]范围
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # 检查音频长度
            duration = len(audio_array) / self.RATE
            if duration < 0.5:  # 少于0.5秒认为太短
                print("❌ 录音时间太短，请重新录音")
                return
            
            print(f"📊 录音时长: {duration:.2f}秒")
            
            # 语音转文字
            print("🔄 正在转录音频...")
            asr_start_time = time.time()
            
            asr_result = self.asr.transcribe_audio_data(
                audio_array, 
                sample_rate=self.RATE, 
                language="auto"
            )
            
            asr_end_time = time.time()
            asr_duration = asr_end_time - asr_start_time
            
            if "error" in asr_result:
                print(f"❌ 语音识别失败: {asr_result['error']}")
                return
            
            transcribed_text = asr_result["clean_text"]
            print(f"✅ 识别结果: {transcribed_text}")
            print(f"⏱️ ASR耗时: {asr_duration:.3f}秒")
            
            # 发送给LLM
            self.chat_with_llm(transcribed_text)
            
        except Exception as e:
            print(f"❌ 处理音频失败: {e}")
    
    def chat_with_llm(self, user_message):
        """与LLM对话（支持多轮对话）"""
        print("\n🤖 正在生成回复...")
        
        # 添加用户消息到对话历史
        self.chat_manager.add_user_message(user_message)
        
        # 调用接口（流式输出）
        llm_start_time = time.time()
        response = self.client.chat.completions.create(
            model="DeepSeek-V3.2-Exp",
            messages=self.chat_manager.get_messages(),  # 使用完整的对话历史
            stream=True
        )
        
        # 性能指标
        first_token_time = None
        token_count = 0
        full_content = ""
        
        print("\n助手: ", end="", flush=True)
        
        # 打印结果（流式逐块输出）
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                
                # 记录首个token时间
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - llm_start_time
                
                # 输出内容
                print(content, end="", flush=True)
                full_content += content
                token_count += 1
        
        # 计算总时间和速率
        llm_end_time = time.time()
        total_llm_time = llm_end_time - llm_start_time
        generation_time = llm_end_time - (first_token_time if first_token_time else llm_start_time)
        
        print("\n")
        print("-" * 50)
        print(f"首Token时间 (TTFT): {ttft:.3f}秒" if first_token_time else "未检测到token")
        print(f"总字符数: {len(full_content)}")
        if generation_time > 0:
            print(f"字符速度: {len(full_content) / generation_time:.2f} tokens/秒")
        print(f"LLM总耗时: {total_llm_time:.3f}秒")
        print(f"对话轮次: {self.chat_manager.get_history_count() // 2}")
        print("-" * 50)
        
        # 添加助手回复到对话历史
        self.chat_manager.add_assistant_message(full_content)
    
    def run(self):
        """运行语音对话系统（支持多轮对话）"""
        print("=" * 60)
        print("🎤 语音对话系统 - 多轮对话版本")
        print("=" * 60)
        print("🎤 按 'z' 键开始录音，松开停止")
        print("⌨️  按 't' 键输入文字对话")
        print("📜 按 'h' 键查看对话历史")
        print("🗑️  按 'c' 键清空对话历史")
        print("❌ 按 'q' 键退出程序")
        print("=" * 60)
        print()
        
        try:
            while True:
                # 检测按键
                if keyboard.is_pressed('z') and not self.is_recording:
                    self.start_recording()
                elif not keyboard.is_pressed('z') and self.is_recording:
                    self.stop_recording()
                elif keyboard.is_pressed('t'):
                    self.handle_text_input()
                    time.sleep(0.5)  # 防止重复触发
                elif keyboard.is_pressed('h'):
                    self.chat_manager.display_history()
                    time.sleep(0.5)  # 防止重复触发
                elif keyboard.is_pressed('c'):
                    self.chat_manager.clear_history()
                    print("\n✅ 对话历史已清空")
                    time.sleep(0.5)  # 防止重复触发
                elif keyboard.is_pressed('q'):
                    print("\n👋 退出程序")
                    break
                
                time.sleep(0.01)  # 避免CPU占用过高
                
        except KeyboardInterrupt:
            print("\n👋 程序被中断")
        finally:
            if self.is_recording:
                self.stop_recording()
    
    def handle_text_input(self):
        """处理文字输入"""
        print("\n" + "="*50)
        print("📝 文字输入模式")
        print("="*50)
        user_input = input("请输入文字消息: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("返回语音模式")
            return
        
        if user_input.lower() == 'clear':
            self.chat_manager.clear_history()
            print("✅ 对话历史已清空")
            return
        
        if user_input.lower() == 'history':
            self.chat_manager.display_history()
            return
        
        if not user_input:
            print("❌ 输入不能为空")
            return
        
        print(f"\n📝 用户输入: {user_input}")
        self.chat_with_llm(user_input)

def main():
    """主函数"""
    try:
        voice_chat = VoiceChatSystem()
        voice_chat.run()
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        print("请确保:")
        print("1. SenseVoice模型已正确下载到指定路径")
        print("2. 已安装所需依赖: pip install pyaudio keyboard torch torchaudio funasr openai numpy")
        print("3. 麦克风权限已开启")
        print("4. GPU可用或修改device参数为'cpu'")
        print("5. system_content.txt文件存在且可读")

if __name__ == "__main__":
    main()
