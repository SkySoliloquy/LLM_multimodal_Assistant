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
from gpt_sovits_client import GPTSoVITSClient
from realtime_voice_recorder import RealtimeVoiceRecorder
from streaming_tts_manager import StreamingTTSManager
from common_utils import print_section, format_duration, print_file_info
from TimeToplevel import Stopwatch, show_time_popup


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
            vad_model_dir=asr_config["vad_model_dir"],
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

        # 初始化TTS客户端
        tts_config = Config.get_tts_config()
        self.tts_client = GPTSoVITSClient(api_url=tts_config["api_url"])
        self.tts_enabled = tts_config["enabled"]
        self.tts_auto_play = tts_config["auto_play"]
        self.tts_config = tts_config

        # 初始化实时语音录制器
        realtime_config = Config.get_realtime_voice_config()
        self.realtime_voice_enabled = realtime_config["enabled"]
        self.realtime_voice_recorder = RealtimeVoiceRecorder(
            sample_rate=16000,
            silence_threshold=realtime_config["silence_threshold"],
            min_speech_length=realtime_config["min_speech_length"],
            max_speech_length=realtime_config["max_speech_length"]
        )

        # 初始化流式TTS管理器
        streaming_config = Config.get_streaming_tts_config()
        self.streaming_tts_enabled = streaming_config["enabled"]
        self.streaming_tts_manager = StreamingTTSManager(
            tts_client=self.tts_client,
            chunk_size=streaming_config["chunk_size"],
            min_chunk_size=streaming_config["min_chunk_size"],
            max_chunk_size=streaming_config["max_chunk_size"],
            split_punctuation=streaming_config["split_punctuation"],
            overlap_chars=streaming_config["overlap_chars"]
        )

        # 设置实时语音回调
        self._setup_realtime_voice_callbacks()

        # 设置流式TTS回调
        self._setup_streaming_tts_callbacks()

        # 设置音频录制器回调
        self._setup_audio_callbacks()

        # 获取UI配置
        self.ui_config = Config.get_ui_config()

        # 流式TTS状态
        self.is_streaming_response = False
        self.should_include_interrupt_context = False  # 是否需要在下次对话中包含中断信息
        
        # 临时延迟计时器（按键说话结束 -> 首次TTS播放）
        self._latency_stopwatch = Stopwatch()
        self._awaiting_first_tts = False

    def _setup_audio_callbacks(self):
        """设置音频录制器回调函数"""
        def on_recording_start():
            print("🎤 开始录音... (松开z键停止)")

        def on_recording_stop():
            print("⏹️ 录音结束")
            # 录音结束即开始计时
            try:
                self._latency_stopwatch.start()
                self._awaiting_first_tts = True
            except Exception:
                pass

        def on_audio_processed(audio_data: np.ndarray):
            self._process_audio(audio_data)

        self.audio_recorder.set_callbacks(
            on_start=on_recording_start,
            on_stop=on_recording_stop,
            on_processed=on_audio_processed
        )

    def _setup_realtime_voice_callbacks(self):
        """设置实时语音回调函数"""
        def on_speech_start():
            print("🗣️ 检测到语音开始...")
            # 显示当前语音检测状态
            status = self.realtime_voice_recorder.get_status()
            print(f"   语音检测状态: 能量阈值={status.get('energy_threshold', 'N/A')}")

        def on_speech_end(audio_data: np.ndarray):
            print("⏹️ 语音结束，开始识别...")
            # 显示语音段信息
            duration = len(audio_data) / 16000
            print(f"   语音段长度: {duration:.2f}秒")
            self._process_realtime_audio(audio_data)

        def on_audio_data(audio_data: np.ndarray):
            # 可以在这里进行实时音频处理
            pass

        self.realtime_voice_recorder.set_callbacks(
            on_speech_start=on_speech_start,
            on_speech_end=on_speech_end,
            on_audio_data=on_audio_data
        )

    def _setup_streaming_tts_callbacks(self):
        """设置流式TTS回调函数"""
        def on_text_chunk(chunk: str):
            print(f"📝 流式文本块: {chunk}")

        def on_audio_ready(audio_path: str):
            print(f"🎵 音频就绪: {audio_path}")

        def on_playback_complete():
            print("✅ 流式播放完成")
            self.is_streaming_response = False

        def on_first_audio_playback():
            # 首次播放开始，结束计时并弹窗
            if self._awaiting_first_tts:
                self._awaiting_first_tts = False
                try:
                    result = self._latency_stopwatch.stop()
                    if result:
                        show_time_popup(result)
                except Exception:
                    pass

        self.streaming_tts_manager.set_callbacks(
            #打印信息
            #on_text_chunk=on_text_chunk,
            #on_audio_ready=on_audio_ready,
            on_playback_complete=on_playback_complete,
            on_first_audio_playback=on_first_audio_playback
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

    def _process_realtime_audio(self, audio_data: np.ndarray):
        """处理实时语音数据"""
        try:
            # 语音转文字
            print("🔄 正在转录音频...")
            asr_start_time = time.time()

            asr_result = self.asr.transcribe_audio_data(
                audio_data,
                sample_rate=16000,
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


            # 发送给LLM,添加过滤器
            import filtered_input as fi

            if fi.filter_symbol(transcribed_text):
                self._chat_with_llm(transcribed_text)


        except Exception as e:
            print(f"❌ 处理实时音频失败: {e}")

    def _chat_with_llm(self, user_message: str):
        """与LLM对话（支持多轮对话和流式TTS）"""
        # 如果有中断信息，添加到用户消息中
        if self.should_include_interrupt_context:
            interrupted_context = self.chat_manager.get_interrupted_context()
            if interrupted_context:
                user_message = interrupted_context + "\n" + user_message
            self.should_include_interrupt_context = False
        
        # 添加用户消息到对话历史
        self.chat_manager.add_user_message(user_message)

        # 在后台线程中调用LLM，避免阻塞主线程
        def call_llm():
            result = self.llm_client.chat_completion(
                messages=self.chat_manager.get_messages(),
                stream=True,
                on_content=self._on_llm_content if self.streaming_tts_enabled and self.tts_enabled else None,
                on_complete=self._on_llm_complete
            )

            if result["success"]:
                # 注意：助手回复会在_on_llm_complete中添加到历史
                # 这里不添加，避免中断时历史被污染
                
                # 如果启用了TTS但未使用流式模式，进行传统语音合成
                if self.tts_enabled and not self.streaming_tts_enabled:
                    self._synthesize_speech(result["content"])
            else:
                print(f"❌ LLM对话失败: {result.get('error', '未知错误')}")
        
        # 启动后台线程执行LLM调用
        import threading
        llm_thread = threading.Thread(target=call_llm, daemon=True)
        llm_thread.start()
        
        # 不等待线程完成，让主线程继续响应按键

    def _on_llm_content(self, content: str):
        """LLM流式内容回调"""
        # 检查是否被中断
        if self.streaming_tts_manager.interrupted:
            return  # 忽略后续输出
            
        if self.streaming_tts_enabled and self.tts_enabled:
            # 如果还没开始流式处理，启动它
            if not self.is_streaming_response:
                self.is_streaming_response = True
                self.streaming_tts_manager.start_streaming()

            # 将内容添加到流式TTS管理器
            self.streaming_tts_manager.add_text(content)

    def _on_llm_complete(self, result: dict):
        """LLM完成回调"""
        # 如果被中断，不更新对话历史
        if self.streaming_tts_manager.interrupted:
            print("⚠️ 对话被中断，不更新对话历史")
            return
            
        if result["success"] and self.streaming_tts_enabled and self.tts_enabled:
            # 正常停止流式TTS处理
            self.streaming_tts_manager.stop_streaming()
        
        # 更新对话历史（完整回复）
        if result["success"] and not self.streaming_tts_manager.interrupted:
            self.chat_manager.add_assistant_message(result["content"])
            
            # 显示对话轮次信息
            if self.ui_config["show_stats"]:
                print(f"对话轮次: {self.chat_manager.get_conversation_rounds()}")

    def _handle_stop_voice(self):
        """处理停止语音播放"""
        if not self.is_streaming_response:
            print("⚠️ 当前没有正在播放的语音")
            return

        print("\n⏹️ 停止语音播放...")

        # 1. 立即标记流式TTS为中断状态（这会立即停止播放）
        self.streaming_tts_manager.interrupt_streaming()

        # 2. 更新状态
        self.is_streaming_response = False
        
        # 3. 获取中断状态并保存
        interrupted_state = self.streaming_tts_manager.get_interrupted_state()

        # 4. 保存中断的对话内容（如果有）
        if interrupted_state["text_so_far"]:
            self.chat_manager.save_interrupted_message(interrupted_state["text_so_far"])
            print(f"📝 中断时的内容：{interrupted_state['text_so_far'][:50]}...")

        # 5. 标记下一次对话需要包含中断信息
        self.should_include_interrupt_context = True
        
        # 注意：不在这里重置中断状态，让中断标志保持
        # 直到下次开始新的流式处理时，start_streaming()会自动重置
        
        print("✅ 语音播放已停止")
    def run(self):
        """运行语音对话系统（支持多轮对话）"""
        print_section("🎤 语音对话系统 - 多轮对话版本", "=", 60)

        keys = self.ui_config["keys"]

        print(f"🎤 按 '{keys['record']}' 键开始录音，松开停止")
        print(f"🗣️ 按 '{keys['toggle_realtime']}' 键切换实时语音模式 (当前: {'开启' if self.realtime_voice_enabled else '关闭'})")
        print(f"⌨️  按 '{keys['text_input']}' 键输入文字对话")
        print(f"📜 按 '{keys['show_history']}' 键查看对话历史")
        print(f"🗑️  按 '{keys['clear_history']}' 键清空对话历史")
        print(f"⏹️  按 '{keys['stop_voice']}' 键停止语音播放")
        print(f"🔊 按 '{keys['toggle_tts']}' 键切换TTS开关 (当前: {'开启' if self.tts_enabled else '关闭'})")
        print(f"📡 流式TTS: {'开启' if self.streaming_tts_enabled else '关闭'}")
        print(f"❌ 按 '{keys['quit']}' 键退出程序")
        print_section("", "=", 60)
        print()

        # 注意：实时语音不会在启动时自动开启，需要用户手动按r键开启
        print("💡 提示：按 'r' 键可开启实时语音模式")

        import tool_numpad as numpad

        try:
            while True:
                #获取按键扫描码进行小键盘约束，小键盘编码一般在70+
                scan_code=numpad.get_scan_code_hook()
                if scan_code is not None and scan_code>70:

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
                    elif keyboard.is_pressed(keys['clear_history']) :
                        self.chat_manager.clear_history()
                        print("\n✅ 对话历史已清空")
                        time.sleep(0.5)  # 防止重复触发
                    elif keyboard.is_pressed(keys['toggle_tts']):
                        self._toggle_tts()
                        time.sleep(0.5)  # 防止重复触发
                    elif keyboard.is_pressed(keys['toggle_realtime']):
                        self._toggle_realtime_voice()
                        time.sleep(0.5)  # 防止重复触发
                    elif keyboard.is_pressed(keys['stop_voice']):
                        self._handle_stop_voice()
                        time.sleep(0.5)  # 防止重复触发
                    elif keyboard.is_pressed(keys['quit']):
                        print("\n👋 退出程序")
                        break

                time.sleep(0.01)  # 避免CPU占用过高

        except KeyboardInterrupt:
            print("\n👋 程序被中断")
        finally:
            # 清理资源
            if self.audio_recorder.is_recording_active():
                self.audio_recorder.stop_recording()

            if self.realtime_voice_recorder.is_active():
                self.realtime_voice_recorder.stop_recording()

            if self.streaming_tts_manager.is_processing:
                self.streaming_tts_manager.stop_streaming()

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

    def _synthesize_speech(self, text: str):
        """合成语音"""
        if not self.tts_enabled:
            return

        try:
            print("\n🎙️ 正在合成语音...")
            tts_start_time = time.time()

            # 生成唯一的输出文件名，避免文件冲突
            timestamp = int(time.time())
            output_path = f"tts_output_{timestamp}.wav"


            # 调用TTS客户端（带重试机制）
            success = self._tts_with_retry(
                text=text,
                output_path=output_path,
                max_retries=self.tts_config["retry_count"]
            )

            tts_end_time = time.time()
            tts_duration = tts_end_time - tts_start_time

            if success:
                print(f"✅ 语音合成成功! 耗时: {format_duration(tts_duration)}")

                # 如果启用自动播放，播放合成的语音
                if self.tts_auto_play:
                    self._play_audio(output_path)
            else:
                print(f"❌ 语音合成失败")
                # 清理可能创建的文件
                self._cleanup_file(output_path)

        except Exception as e:
            print(f"❌ TTS合成异常: {e}")
            # 清理可能创建的文件
            if 'output_path' in locals():
                self._cleanup_file(output_path)

    def _play_audio(self, audio_path: str):
        """播放音频文件"""
        try:
            import pygame
            import threading

            def play_audio_thread():
                try:
                    pygame.mixer.init()
                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()

                    # 等待播放完成
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                    # 播放完成后清理文件
                    pygame.mixer.music.unload()
                    self._cleanup_file(audio_path)

                except Exception as e:
                    print(f"❌ 音频播放线程异常: {e}")
                    self._cleanup_file(audio_path)

            # 在后台线程中播放音频，避免阻塞主程序
            audio_thread = threading.Thread(target=play_audio_thread, daemon=True)
            audio_thread.start()

        except ImportError:
            print("⚠️ 未安装pygame，无法自动播放音频")
            print(f"   音频文件已保存到: {audio_path}")
        except Exception as e:
            print(f"❌ 播放音频失败: {e}")
            print(f"   音频文件已保存到: {audio_path}")


    def _tts_with_retry(self, text: str, output_path: str, max_retries: int = 2) -> bool:
        """带重试机制的TTS合成"""
        for attempt in range(max_retries + 1):
            try:
                # 如果文本过长，在重试时进一步缩短
                if attempt > 0 and len(text) > 100:
                    print(f"🔄 重试第{attempt}次，缩短文本长度")
                    text = text[:100] + "..."

                success = self.tts_client.text_to_speech(
                    text=text,
                    ref_audio_path=self.tts_config["ref_audio_path"],
                    output_path=output_path,
                    text_lang=self.tts_config["text_lang"],
                    prompt_lang=self.tts_config["prompt_lang"],
                    prompt_text=self.tts_config["prompt_text"],
                    top_k=5,
                    top_p=0.8,
                    temperature=0.8,
                    speed_factor=1.0,
                    text_split_method="cut4",
                    batch_size=1,
                    sample_steps=4
                )

                if success:
                    return True
                else:
                    print(f"⚠️ 第{attempt + 1}次尝试失败")
                    if attempt < max_retries:
                        time.sleep(1)  # 等待1秒后重试

            except Exception as e:
                print(f"⚠️ 第{attempt + 1}次尝试异常: {e}")
                if attempt < max_retries:
                    time.sleep(1)  # 等待1秒后重试

        return False

    def _cleanup_file(self, file_path: str):
        """清理临时文件"""
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"⚠️ 清理文件失败: {e}")

    def _toggle_tts(self):
        """切换TTS开关"""
        self.tts_enabled = not self.tts_enabled
        status = "开启" if self.tts_enabled else "关闭"
        print(f"\n🔊 TTS功能已{status}")

        if self.tts_enabled:
            print("   下次LLM回复时将自动进行语音合成")
        else:
            print("   LLM回复将不再进行语音合成")

    def _toggle_realtime_voice(self):
        """切换实时语音模式"""
        try:
            self.realtime_voice_enabled = not self.realtime_voice_enabled
            status = "开启" if self.realtime_voice_enabled else "关闭"
            print(f"\n🗣️ 实时语音模式已{status}")

            if self.realtime_voice_enabled:
                # 确保按键录音已停止
                if self.audio_recorder.is_recording_active():
                    self.audio_recorder.stop_recording()

                # 启动实时语音录制
                self.realtime_voice_recorder.start_recording()
                print("   开始监听语音输入，检测到语音会自动识别")
                print("   💡 提示：请确保环境相对安静，说话清晰")
            else:
                # 停止实时语音录制
                self.realtime_voice_recorder.stop_recording()
                print("   停止监听语音输入，请使用按键录音或文字输入")

        except Exception as e:
            print(f"❌ 切换实时语音模式失败: {e}")
            # 重置状态
            self.realtime_voice_enabled = False

    def _cleanup_streaming_resources(self):
        """清理流式资源"""
        try:
            # 重置流式TTS管理器的中断状态
            self.streaming_tts_manager.reset_interrupt_state()
        except Exception as e:
            print(f"⚠️ 清理流式资源时出错: {e}")

def main():
    """主函数"""
    try:
        voice_chat = VoiceChatSystem()
        voice_chat.run()
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        print("请确保:")
        print("1. SenseVoice模型已正确下载到指定路径")
        print("2. 已安装所需依赖: pip install pyaudio keyboard torch torchaudio funasr openai numpy pygame requests")
        print("3. 麦克风权限已开启")
        print("4. GPU可用或修改config.py中的device参数为'cpu'")
        print("5. System_Content.txt文件存在且可读")
        print("6. 检查config.py中的API配置是否正确")
        print("7. GPT-SoVITS API服务已启动 (如使用TTS功能)")
        print("8. 参考音频文件路径正确 (如使用TTS功能)")


if __name__ == "__main__":
    main()
