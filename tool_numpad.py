import keyboard
from collections import deque

# 全局按键队列
key_queue = deque()
key_name_queue = deque()


def on_key_event(e):
    """按键事件回调函数"""
    if e.event_type == keyboard.KEY_DOWN:
        key_queue.append(e.scan_code)
        key_name_queue.append(e.name)


# 注册全局钩子
keyboard.hook(on_key_event)


def get_scan_code_hook():
    """从队列中获取扫描码"""
    if key_queue:
        return key_queue.popleft()
    return None

def get_event_name_hook():
    """从队列中获取按键事件名称"""
    if key_name_queue:
        return key_name_queue.popleft()
    return None


def is_digit_key(key_name):
    """判断按键名称是否为数字

    Args:
        key_name (str): 按键名称

    Returns:
        bool: 如果是数字键返回True，否则返回False
    """
    if key_name is None:
        return False
    return key_name.isdigit() or key_name in ['numpad 0', 'numpad 1', 'numpad 2', 'numpad 3', 'numpad 4', 
                                              'numpad 5', 'numpad 6', 'numpad 7', 'numpad 8', 'numpad 9']
