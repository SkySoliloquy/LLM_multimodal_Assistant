#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
测试多轮对话功能
"""

import os
import sys

def test_chat_manager():
    """测试ChatManager类"""
    print("🧪 测试ChatManager类...")
    
    try:
        from voice_chat import ChatManager
        
        # 创建ChatManager实例
        system_prompt = "你是一个有用的助手。"
        chat_manager = ChatManager(system_prompt, max_history=3)
        
        # 测试添加消息
        chat_manager.add_user_message("你好")
        chat_manager.add_assistant_message("你好！有什么我可以帮助你的吗？")
        
        chat_manager.add_user_message("今天天气怎么样？")
        chat_manager.add_assistant_message("我无法获取实时天气信息，建议你查看天气预报应用。")
        
        chat_manager.add_user_message("谢谢")
        chat_manager.add_assistant_message("不客气！还有其他问题吗？")
        
        # 测试获取消息
        messages = chat_manager.get_messages()
        print(f"   消息总数: {len(messages)}")
        print(f"   历史轮次: {chat_manager.get_history_count() // 2}")
        
        # 测试历史修剪
        print("   测试历史修剪...")
        for i in range(5):
            chat_manager.add_user_message(f"消息{i}")
            chat_manager.add_assistant_message(f"回复{i}")
        
        print(f"   修剪后历史轮次: {chat_manager.get_history_count() // 2}")
        
        # 测试清空历史
        chat_manager.clear_history()
        print(f"   清空后历史轮次: {chat_manager.get_history_count()}")
        
        print("   ✅ ChatManager测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ ChatManager测试失败: {e}")
        return False

def test_voice_chat_system_init():
    """测试VoiceChatSystem初始化"""
    print("\n🧪 测试VoiceChatSystem初始化...")
    
    try:
        # 检查system_content.txt是否存在
        if not os.path.exists("system_content.txt"):
            print("   ❌ system_content.txt文件不存在")
            return False
        
        from voice_chat import VoiceChatSystem
        
        # 测试初始化（可能需要一些时间）
        print("   正在初始化VoiceChatSystem...")
        voice_chat = VoiceChatSystem()
        
        # 检查组件是否正确初始化
        if hasattr(voice_chat, 'chat_manager'):
            print("   ✅ ChatManager已初始化")
        else:
            print("   ❌ ChatManager未初始化")
            return False
        
        if hasattr(voice_chat, 'asr'):
            print("   ✅ ASR已初始化")
        else:
            print("   ❌ ASR未初始化")
            return False
        
        if hasattr(voice_chat, 'client'):
            print("   ✅ LLM客户端已初始化")
        else:
            print("   ❌ LLM客户端未初始化")
            return False
        
        print("   ✅ VoiceChatSystem初始化测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ VoiceChatSystem初始化失败: {e}")
        return False

def test_text_input_functionality():
    """测试文字输入功能"""
    print("\n🧪 测试文字输入功能...")
    
    try:
        from voice_chat import VoiceChatSystem
        
        # 初始化系统
        voice_chat = VoiceChatSystem()
        
        # 测试handle_text_input方法存在
        if hasattr(voice_chat, 'handle_text_input'):
            print("   ✅ handle_text_input方法存在")
        else:
            print("   ❌ handle_text_input方法不存在")
            return False
        
        # 测试ChatManager集成
        initial_count = voice_chat.chat_manager.get_history_count()
        
        # 模拟添加消息
        voice_chat.chat_manager.add_user_message("测试消息")
        voice_chat.chat_manager.add_assistant_message("测试回复")
        
        new_count = voice_chat.chat_manager.get_history_count()
        if new_count == initial_count + 2:
            print("   ✅ 消息添加功能正常")
        else:
            print("   ❌ 消息添加功能异常")
            return False
        
        print("   ✅ 文字输入功能测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 文字输入功能测试失败: {e}")
        return False

def test_multi_turn_integration():
    """测试多轮对话集成"""
    print("\n🧪 测试多轮对话集成...")
    
    try:
        from voice_chat import VoiceChatSystem
        
        # 初始化系统
        voice_chat = VoiceChatSystem()
        
        # 模拟多轮对话
        test_messages = [
            ("你好", "你好！有什么我可以帮助你的吗？"),
            ("请介绍一下Python", "Python是一种高级编程语言..."),
            ("能给我一个代码示例吗？", "当然！这里是一个简单的示例..."),
            ("谢谢", "不客气！还有其他问题吗？")
        ]
        
        print("   模拟多轮对话...")
        for user_msg, assistant_msg in test_messages:
            voice_chat.chat_manager.add_user_message(user_msg)
            voice_chat.chat_manager.add_assistant_message(assistant_msg)
        
        # 验证历史记录
        history_count = voice_chat.chat_manager.get_history_count()
        expected_count = len(test_messages) * 2
        
        if history_count == expected_count:
            print(f"   ✅ 对话历史记录正确: {history_count}条消息")
        else:
            print(f"   ❌ 对话历史记录异常: 期望{expected_count}条，实际{history_count}条")
            return False
        
        # 验证消息格式
        messages = voice_chat.chat_manager.get_messages()
        if len(messages) == expected_count + 1:  # +1 for system prompt
            print("   ✅ 消息格式正确")
        else:
            print("   ❌ 消息格式异常")
            return False
        
        # 测试历史修剪
        print("   测试历史修剪...")
        for i in range(10):
            voice_chat.chat_manager.add_user_message(f"额外消息{i}")
            voice_chat.chat_manager.add_assistant_message(f"额外回复{i}")
        
        final_count = voice_chat.chat_manager.get_history_count()
        max_expected = voice_chat.chat_manager.max_history * 2
        
        if final_count <= max_expected:
            print(f"   ✅ 历史修剪正常: {final_count}条消息")
        else:
            print(f"   ❌ 历史修剪异常: {final_count}条消息超过限制{max_expected}")
            return False
        
        print("   ✅ 多轮对话集成测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 多轮对话集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 多轮对话功能测试")
    print("=" * 60)
    
    tests = [
        test_chat_manager,
        test_voice_chat_system_init,
        test_text_input_functionality,
        test_multi_turn_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！多轮对话功能已成功集成")
        print("\n💡 使用说明:")
        print("1. 运行: python voice_chat.py")
        print("2. 语音对话: 按 'z' 键录音")
        print("3. 文字对话: 按 't' 键输入")
        print("4. 查看历史: 按 'h' 键")
        print("5. 清空历史: 按 'c' 键")
        print("6. 退出程序: 按 'q' 键")
    else:
        print("❌ 部分测试失败，请检查配置")

if __name__ == "__main__":
    main()
