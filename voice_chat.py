#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
语音对话系统 - 结合ASR和LLM，支持多轮对话
按z键录音，语音转文字后发送给模型
"""

import time
import keyboard
import numpy as np
from typing import Optional

# 导入自定义模块
from config import Config
from chat_manager import ChatManager
from asr_client import SenseVoiceASRDirect
from audio_recorder import AudioRecorder
from llm_client import LLMClient
from common_utils import print_section, format_duration, print_file_info


class VoiceChatSystem:
    """语音对话系统"""
    
    def __init__(self):
        """初始化语音对话系统"""
        # 验证配置
        if not Config.validate_config():
            raise RuntimeError("配置验证失败，请检查配置文件")
        
        # 打印配置摘要
        Config.print_config_summary()
        
        # 初始化ASR客户端
        asr_config = Config.get_asr_config()
        self.asr = SenseVoiceASRDirect(
            model_dir=asr_config["model_dir"],
            device=asr_config["device"],
            vad_model_dir=asr_config["vad_model_dir"]
        )
        
        # 初始化LLM客户端
        llm_config = Config.get_llm_config()
        self.llm_client = LLMClient(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model_name=llm_config["model_name"]
        )
        
        # 初始化对话管理器
        chat_config = Config.get_chat_config()
        system_prompt = Config.load_system_prompt()
        self.chat_manager = ChatManager(system_prompt, max_history=chat_config["max_history"])
        
        # 初始化音频录制器
        audio_config = Config.get_audio_config()
        self.audio_recorder = AudioRecorder(
            chunk=audio_config["chunk"],
            format=audio_config["format"],
            channels=audio_config["channels"],
            rate=audio_config["rate"],
            min_duration=audio_config["min_duration"]
        )
        
        # 设置音频录制器回调
        self._setup_audio_callbacks()
        
        # 获取UI配置
        self.ui_config = Config.get_ui_config()
        
    def _setup_audio_callbacks(self):
        """设置音频录制器回调函数"""
        def on_recording_start():
            print("🎤 开始录音... (松开z键停止)")
        
        def on_recording_stop():
            print("⏹️ 录音结束")
        
        def on_audio_processed(audio_data: np.ndarray):
            self._process_audio(audio_data)
        
        self.audio_recorder.set_callbacks(
            on_start=on_recording_start,
            on_stop=on_recording_stop,
            on_processed=on_audio_processed
        )
    
    def _process_audio(self, audio_data: np.ndarray):
        """处理录音数据"""
        try:
            # 语音转文字
            print("🔄 正在转录音频...")
            asr_start_time = time.time()
            
            asr_result = self.asr.transcribe_audio_data(
                audio_data, 
                sample_rate=self.audio_recorder.RATE, 
                language="auto"
            )
            
            asr_end_time = time.time()
            asr_duration = asr_end_time - asr_start_time
            
            if "error" in asr_result:
                print(f"❌ 语音识别失败: {asr_result['error']}")
                return
            
            transcribed_text = asr_result["clean_text"]
            print(f"✅ 识别结果: {transcribed_text}")
            print(f"⏱️ ASR耗时: {format_duration(asr_duration)}")
            
            # 发送给LLM
            self._chat_with_llm(transcribed_text)
            
        except Exception as e:
            print(f"❌ 处理音频失败: {e}")
    
    def _chat_with_llm(self, user_message: str):
        """与LLM对话（支持多轮对话）"""
        # 添加用户消息到对话历史
        self.chat_manager.add_user_message(user_message)
        
        # 调用LLM客户端
        result = self.llm_client.chat_completion(
            messages=self.chat_manager.get_messages(),
            stream=True
        )
        
        if result["success"]:
            # 添加助手回复到对话历史
            self.chat_manager.add_assistant_message(result["content"])
            
            # 显示对话轮次信息
            if self.ui_config["show_stats"]:
                print(f"对话轮次: {self.chat_manager.get_conversation_rounds()}")
        else:
            print(f"❌ LLM对话失败: {result.get('error', '未知错误')}")
    
    def run(self):
        """运行语音对话系统（支持多轮对话）"""
        print_section("🎤 语音对话系统 - 多轮对话版本", "=", 60)
        
        keys = self.ui_config["keys"]
        print(f"🎤 按 '{keys['record']}' 键开始录音，松开停止")
        print(f"⌨️  按 '{keys['text_input']}' 键输入文字对话")
        print(f"📜 按 '{keys['show_history']}' 键查看对话历史")
        print(f"🗑️  按 '{keys['clear_history']}' 键清空对话历史")
        print(f"❌ 按 '{keys['quit']}' 键退出程序")
        print_section("", "=", 60)
        print()
        
        try:
            while True:
                # 检测按键
                if keyboard.is_pressed(keys['record']) and not self.audio_recorder.is_recording_active():
                    self.audio_recorder.start_recording()
                elif not keyboard.is_pressed(keys['record']) and self.audio_recorder.is_recording_active():
                    self.audio_recorder.stop_recording()
                elif keyboard.is_pressed(keys['text_input']):
                    self._handle_text_input()
                    time.sleep(0.5)  # 防止重复触发
                elif keyboard.is_pressed(keys['show_history']):
                    self.chat_manager.display_history()
                    time.sleep(0.5)  # 防止重复触发
                elif keyboard.is_pressed(keys['clear_history']):
                    self.chat_manager.clear_history()
                    print("\n✅ 对话历史已清空")
                    time.sleep(0.5)  # 防止重复触发
                elif keyboard.is_pressed(keys['quit']):
                    print("\n👋 退出程序")
                    break
                
                time.sleep(0.01)  # 避免CPU占用过高
                
        except KeyboardInterrupt:
            print("\n👋 程序被中断")
        finally:
            if self.audio_recorder.is_recording_active():
                self.audio_recorder.stop_recording()
    
    def _handle_text_input(self):
        """处理文字输入"""
        print_section("📝 文字输入模式", "=", 50)
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
        self._chat_with_llm(user_input)

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
        print("4. GPU可用或修改config.py中的device参数为'cpu'")
        print("5. System_Content.txt文件存在且可读")
        print("6. 检查config.py中的API配置是否正确")


if __name__ == "__main__":
    main()
