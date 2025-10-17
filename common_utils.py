#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
工具函数模块
包含通用的工具函数和辅助方法
"""

import time
import os
from typing import Any, Dict, List, Optional


def format_duration(seconds: float) -> str:
    """
    格式化时间长度为可读字符串
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串
    """
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为可读字符串
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化的文件大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f}KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f}MB"
    else:
        return f"{size_bytes/(1024**3):.1f}GB"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀字符串
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-len(suffix)] + suffix


def print_separator(char: str = "=", length: int = 50) -> None:
    """
    打印分隔线
    
    Args:
        char: 分隔字符
        length: 分隔线长度
    """
    print(char * length)


def print_section(title: str, char: str = "=", length: int = 50) -> None:
    """
    打印带标题的分隔线
    
    Args:
        title: 标题
        char: 分隔字符
        length: 分隔线长度
    """
    print_separator(char, length)
    print(title)
    print_separator(char, length)


def safe_input(prompt: str, default: str = "", validator: Optional[callable] = None) -> str:
    """
    安全的输入函数，支持默认值和验证
    
    Args:
        prompt: 提示信息
        default: 默认值
        validator: 验证函数
        
    Returns:
        用户输入或默认值
    """
    while True:
        try:
            user_input = input(f"{prompt} (默认: {default}): ").strip()
            if not user_input:
                user_input = default
            
            if validator and not validator(user_input):
                print("❌ 输入无效，请重新输入")
                continue
            
            return user_input
        except KeyboardInterrupt:
            print("\n👋 输入被取消")
            return default
        except Exception as e:
            print(f"❌ 输入错误: {e}")
            continue


def ensure_directory(directory: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        是否成功创建或目录已存在
    """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ 创建目录: {directory}")
        return True
    except Exception as e:
        print(f"❌ 创建目录失败: {e}")
        return False


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    获取文件信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含文件信息的字典
    """
    try:
        if not os.path.exists(file_path):
            return {"exists": False}
        
        stat = os.stat(file_path)
        return {
            "exists": True,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "modified_time": time.ctime(stat.st_mtime),
            "is_file": os.path.isfile(file_path),
            "is_directory": os.path.isdir(file_path)
        }
    except Exception as e:
        return {"exists": False, "error": str(e)}


def print_file_info(file_path: str) -> None:
    """
    打印文件信息
    
    Args:
        file_path: 文件路径
    """
    info = get_file_info(file_path)
    if not info["exists"]:
        print(f"❌ 文件不存在: {file_path}")
        return
    
    print(f"📁 文件信息: {file_path}")
    print(f"   大小: {info['size_formatted']}")
    print(f"   修改时间: {info['modified_time']}")
    print(f"   类型: {'文件' if info['is_file'] else '目录' if info['is_directory'] else '未知'}")


def validate_audio_file(file_path: str) -> bool:
    """
    验证音频文件是否有效
    
    Args:
        file_path: 音频文件路径
        
    Returns:
        是否为有效的音频文件
    """
    if not os.path.exists(file_path):
        return False
    
    # 检查文件扩展名
    valid_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
    _, ext = os.path.splitext(file_path.lower())
    if ext not in valid_extensions:
        return False
    
    # 检查文件大小（至少1KB）
    try:
        size = os.path.getsize(file_path)
        return size > 1024
    except:
        return False


def print_progress_bar(current: int, total: int, width: int = 50, prefix: str = "进度") -> None:
    """
    打印进度条
    
    Args:
        current: 当前进度
        total: 总数
        width: 进度条宽度
        prefix: 前缀文本
    """
    if total == 0:
        return
    
    percent = current / total
    filled_width = int(width * percent)
    bar = "█" * filled_width + "░" * (width - filled_width)
    print(f"\r{prefix}: |{bar}| {percent:.1%} ({current}/{total})", end="", flush=True)
    
    if current == total:
        print()  # 完成后换行


def format_performance_stats(stats: Dict[str, Any]) -> str:
    """
    格式化性能统计信息
    
    Args:
        stats: 统计信息字典
        
    Returns:
        格式化的统计信息字符串
    """
    lines = []
    lines.append("📊 性能统计:")
    lines.append(f"   总请求数: {stats.get('total_requests', 0)}")
    lines.append(f"   总字符数: {stats.get('total_tokens', 0)}")
    lines.append(f"   总耗时: {format_duration(stats.get('total_time', 0))}")
    lines.append(f"   平均TTFT: {format_duration(stats.get('avg_ttft', 0))}")
    lines.append(f"   平均生成速度: {stats.get('avg_generation_speed', 0):.2f} chars/s")
    
    return "\n".join(lines)


def create_backup_filename(original_path: str, suffix: str = "backup") -> str:
    """
    创建备份文件名
    
    Args:
        original_path: 原始文件路径
        suffix: 备份后缀
        
    Returns:
        备份文件路径
    """
    import datetime
    
    base, ext = os.path.splitext(original_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{suffix}_{timestamp}{ext}"


def safe_remove_file(file_path: str, create_backup: bool = True) -> bool:
    """
    安全删除文件，可选择创建备份
    
    Args:
        file_path: 文件路径
        create_backup: 是否创建备份
        
    Returns:
        是否成功删除
    """
    if not os.path.exists(file_path):
        return True
    
    try:
        if create_backup:
            backup_path = create_backup_filename(file_path)
            import shutil
            shutil.copy2(file_path, backup_path)
            print(f"✅ 已创建备份: {backup_path}")
        
        os.remove(file_path)
        print(f"✅ 已删除文件: {file_path}")
        return True
    except Exception as e:
        print(f"❌ 删除文件失败: {e}")
        return False
