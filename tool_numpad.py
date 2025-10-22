import keyboard
from collections import deque

# 全局按键队列
key_queue = deque()


def on_key_event(e):
    """按键事件回调函数"""
    if e.event_type == keyboard.KEY_DOWN:
        key_queue.append(e.scan_code)


# 注册全局钩子
keyboard.hook(on_key_event)


def get_scan_code_hook():
    """从队列中获取扫描码"""
    if key_queue:
        return key_queue.popleft()
    return None

