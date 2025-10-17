#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
LLM客户端模块
负责与大语言模型的交互和流式输出处理
"""

import time
from typing import List, Dict, Any, Optional, Callable
from openai import OpenAI


class LLMClient:
    """LLM客户端"""
    
    def __init__(self, api_key: str, base_url: str, model_name: str = "DeepSeek-V3.2-Exp"):
        """
        初始化LLM客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model_name = model_name
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "avg_ttft": 0.0,
            "avg_generation_speed": 0.0
        }
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       stream: bool = True,
                       on_content: Optional[Callable[[str], None]] = None,
                       on_complete: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        发送聊天完成请求
        
        Args:
            messages: 消息列表
            stream: 是否使用流式输出
            on_content: 内容回调函数
            on_complete: 完成回调函数
            
        Returns:
            包含响应和统计信息的字典
        """
        print("\n🤖 正在生成回复...")
        
        # 记录开始时间
        start_time = time.time()
        first_token_time = None
        token_count = 0
        full_content = ""
        
        try:
            # 调用API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=stream
            )
            
            print("\n助手: ", end="", flush=True)
            
            # 处理流式响应
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    
                    # 记录首个token时间
                    if first_token_time is None:
                        first_token_time = time.time()
                    
                    # 输出内容
                    print(content, end="", flush=True)
                    full_content += content
                    token_count += 1
                    
                    # 调用内容回调
                    if on_content:
                        on_content(content)
            
            # 计算统计信息
            end_time = time.time()
            total_time = end_time - start_time
            ttft = (first_token_time - start_time) if first_token_time else 0
            generation_time = end_time - (first_token_time if first_token_time else start_time)
            generation_speed = len(full_content) / generation_time if generation_time > 0 else 0
            
            # 更新统计信息
            self._update_stats(total_time, ttft, generation_speed, len(full_content))
            
            # 打印统计信息
            self._print_stats(ttft, len(full_content), generation_speed, total_time)
            
            result = {
                "success": True,
                "content": full_content,
                "stats": {
                    "ttft": ttft,
                    "total_time": total_time,
                    "generation_speed": generation_speed,
                    "content_length": len(full_content)
                }
            }
            
            # 调用完成回调
            if on_complete:
                on_complete(result)
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "content": ""
            }
            print(f"\n❌ LLM请求失败: {e}")
            
            if on_complete:
                on_complete(error_result)
            
            return error_result
    
    def _update_stats(self, total_time: float, ttft: float, generation_speed: float, content_length: int):
        """更新统计信息"""
        self.stats["total_requests"] += 1
        self.stats["total_tokens"] += content_length
        self.stats["total_time"] += total_time
        
        # 计算平均值
        if self.stats["total_requests"] > 0:
            self.stats["avg_ttft"] = (self.stats["avg_ttft"] * (self.stats["total_requests"] - 1) + ttft) / self.stats["total_requests"]
            self.stats["avg_generation_speed"] = (self.stats["avg_generation_speed"] * (self.stats["total_requests"] - 1) + generation_speed) / self.stats["total_requests"]
    
    def _print_stats(self, ttft: float, content_length: int, generation_speed: float, total_time: float):
        """打印统计信息"""
        print("\n")
        print("-" * 50)
        print(f"首Token时间 (TTFT): {ttft:.3f}秒" if ttft > 0 else "未检测到token")
        print(f"总字符数: {content_length}")
        if generation_speed > 0:
            print(f"字符速度: {generation_speed:.2f} chars/秒")
        print(f"LLM总耗时: {total_time:.3f}秒")
        print("-" * 50)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "avg_ttft": 0.0,
            "avg_generation_speed": 0.0
        }
    
    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "base_url": self.client.base_url,
            "api_key": self.client.api_key[:10] + "..." if self.client.api_key else "None"
        }
