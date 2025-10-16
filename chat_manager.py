"""
多轮对话管理器
维护对话历史，支持上下文管理
"""

class ChatManager:
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

