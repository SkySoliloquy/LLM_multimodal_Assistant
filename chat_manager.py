#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
对话管理器模块
负责管理多轮对话的历史记录和消息处理
"""

from typing import List, Dict, Any


class ChatManager:
    """多轮对话管理器"""
    
    def __init__(self, system_prompt: str, max_history: int = 10):
        """
        初始化对话管理器
        
        Args:
            system_prompt: 系统提示词
            max_history: 最大保留的对话轮数（不包括system消息）
        """
        self.system_prompt = system_prompt
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []
    
    def add_user_message(self, content: str) -> None:
        """添加用户消息到历史"""
        self.history.append({"role": "user", "content": content})
        self._trim_history()
    
    def add_assistant_message(self, content: str) -> None:
        """添加助手消息到历史"""
        self.history.append({"role": "assistant", "content": content})
        self._trim_history()
    
    def _trim_history(self) -> None:
        """修剪历史记录，保持在最大长度内"""
        if len(self.history) > self.max_history * 2:  # 每轮对话有user和assistant两条消息
            # 保留最近的对话
            self.history = self.history[-(self.max_history * 2):]
    
    def get_messages(self) -> List[Dict[str, str]]:
        """获取完整的消息列表（包括system prompt）"""
        return [{"role": "system", "content": self.system_prompt}] + self.history
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.history = []
    
    def get_history_count(self) -> int:
        """获取当前历史记录条数"""
        return len(self.history)
    
    def get_conversation_rounds(self) -> int:
        """获取对话轮次数"""
        return self.get_history_count() // 2
    
    def display_history(self) -> None:
        """显示对话历史"""
        print("\n" + "="*50)
        print("对话历史:")
        print("="*50)
        for i, msg in enumerate(self.history, 1):
            role = "用户" if msg["role"] == "user" else "助手"
            content_preview = msg['content'][:50] + ('...' if len(msg['content']) > 50 else '')
            print(f"{i}. [{role}]: {content_preview}")
        print("="*50 + "\n")
    
    def get_last_user_message(self) -> str:
        """获取最后一条用户消息"""
        for msg in reversed(self.history):
            if msg["role"] == "user":
                return msg["content"]
        return ""
    
    def get_last_assistant_message(self) -> str:
        """获取最后一条助手消息"""
        for msg in reversed(self.history):
            if msg["role"] == "assistant":
                return msg["content"]
        return ""