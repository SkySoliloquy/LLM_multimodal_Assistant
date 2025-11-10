#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
LLM客户端模块
负责与大语言模型的交互和流式输出处理
"""

import time
import asyncio
import json
from typing import List, Dict, Any, Optional, Callable
from openai import OpenAI
from AddWindows import NewWindowPrinter

class LLMClient:
    """LLM客户端"""
    
    def __init__(self, api_key: str, base_url: str, model_name: str = "DeepSeek-V3.2-Exp", mcp_manager=None):
        """
        初始化LLM客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
            mcp_manager: MCP管理器实例（可选）
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model_name = model_name
        self.mcp_manager = mcp_manager
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "avg_ttft": 0.0,
            "avg_generation_speed": 0.0
        }

        # 创建新窗口
        self.llm_printer = NewWindowPrinter(window_name="LLM数据窗口")
    
    def _run_async(self, coro):
        """运行异步代码的辅助方法"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，需要在新线程中运行
                import concurrent.futures
                import threading
                import queue
                
                result_queue = queue.Queue()
                exception_queue = queue.Queue()
                
                def run_in_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(coro)
                        result_queue.put(result)
                        new_loop.close()
                    except Exception as e:
                        exception_queue.put(e)
                
                thread = threading.Thread(target=run_in_thread, daemon=True)
                thread.start()
                thread.join(timeout=60)  # 最多等待60秒
                
                if not exception_queue.empty():
                    raise exception_queue.get()
                if not result_queue.empty():
                    return result_queue.get()
                raise RuntimeError("异步操作超时")
            else:
                return loop.run_until_complete(coro)
        except RuntimeError as e:
            # 没有事件循环，创建新的
            if "no current event loop" in str(e).lower():
                return asyncio.run(coro)
            else:
                raise
    
    async def _handle_tool_calls(self, tool_calls, messages):
        """处理工具调用（异步）"""
        if not self.mcp_manager:
            return
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}
            
            print(f"[MCP] 调用工具: {tool_name}")
            print(f"[MCP] 参数: {tool_args}")
            
            try:
                # 调用工具
                result = await self.mcp_manager.call_tool(tool_name, tool_args)
                
                # 调试：打印原始结果
                print(f"[MCP] 工具 {tool_name} 原始结果类型: {type(result)}")
                print(f"[MCP] 工具 {tool_name} 结果 isError: {getattr(result, 'isError', 'N/A')}")
                print(f"[MCP] 工具 {tool_name} 结果 content: {getattr(result, 'content', 'N/A')}")
                
                # 提取工具结果文本
                tool_result_text = ""
                if hasattr(result, 'content') and result.content:
                    for content_item in result.content:
                        # 处理不同类型的content_item
                        if hasattr(content_item, 'text'):
                            # 对象有text属性
                            text = content_item.text
                            if text:
                                tool_result_text += text + "\n"
                        elif isinstance(content_item, dict):
                            # 字典类型
                            if 'text' in content_item:
                                text = content_item['text']
                                if text:
                                    tool_result_text += text + "\n"
                            elif 'content' in content_item:
                                # 嵌套的content
                                text = content_item['content']
                                if text:
                                    tool_result_text += text + "\n"
                        elif isinstance(content_item, str):
                            # 直接是字符串
                            tool_result_text += content_item + "\n"
                
                # 去除末尾的换行符
                tool_result_text = tool_result_text.strip()
                
                if not tool_result_text:
                    tool_result_text = "执行完成" if not getattr(result, 'isError', False) else "执行失败"
                    print(f"[MCP] 警告: 工具 {tool_name} 返回内容为空，使用默认消息")
                
                # 打印提取的结果（限制长度，避免输出过长）
                result_preview = tool_result_text[:200] + "..." if len(tool_result_text) > 200 else tool_result_text
                print(f"[MCP] 工具 {tool_name} 提取结果预览: {result_preview}")
                print(f"[MCP] 工具 {tool_name} 结果长度: {len(tool_result_text)} 字符")
                
                # 添加工具结果到消息历史
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_result_text
                }
                messages.append(tool_message)
                
                print(f"[MCP] 工具 {tool_name} 执行成功，结果已添加到消息历史")
                
            except Exception as e:
                import traceback
                print(f"[MCP] 工具 {tool_name} 执行失败: {e}")
                traceback.print_exc()
                # 添加错误消息到对话历史
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": f"工具执行失败: {str(e)}"
                }
                messages.append(tool_message)
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       stream: bool = True,
                       on_content: Optional[Callable[[str], None]] = None,
                       on_complete: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        发送聊天完成请求（支持MCP工具调用）
        
        Args:
            messages: 消息列表
            stream: 是否使用流式输出
            on_content: 内容回调函数
            on_complete: 完成回调函数
            
        Returns:
            包含响应和统计信息的字典
        """
        # 获取用户发送的最新消息
        self.user_message = messages[-1].get("content")

        self.llm_printer.print_to_window("\n我: "+self.user_message)
        self.llm_printer.print_to_window("\n正在生成回复...")
        # 记录开始时间
        start_time = time.time()
        first_token_time = None
        token_count = 0
        full_content = ""
        
        try:
            # 获取工具列表（如果MCP管理器可用）
            tools = None
            if self.mcp_manager:
                try:
                    tools = self.mcp_manager.get_tools_openai_format()
                    if tools:
                        print(f"[MCP] 提供 {len(tools)} 个工具给LLM")
                except Exception as e:
                    print(f"[MCP] 获取工具列表失败: {e}")
                    tools = None
            
            # 创建消息副本，避免修改原始消息
            messages_copy = messages.copy()
            
            # 决定是否使用流式（如果有工具，第一次调用必须非流式以检查工具调用）
            use_stream_for_first_call = stream if not tools else False
            
            # 第一次调用：检查是否需要工具调用
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages_copy,
                tools=tools,  # 如果有工具，传递给LLM
                tool_choice="auto" if tools else None,
                stream=use_stream_for_first_call
            )
            
            # 记录响应是否为流式
            is_first_response_stream = use_stream_for_first_call
            response_to_process = response
            needs_second_call = False
            
            # 检查是否有工具调用（只有非流式响应才能检查工具调用）
            if tools and not is_first_response_stream:
                # 非流式响应，可以检查工具调用
                try:
                    message = response.choices[0].message
                    tool_calls = getattr(message, 'tool_calls', None) if hasattr(message, 'tool_calls') else None
                    
                    if tool_calls:
                        print(f"[MCP] LLM请求使用 {len(tool_calls)} 个工具")
                        # 添加助手消息（包含工具调用）到消息历史
                        assistant_message = {
                            "role": "assistant",
                            "content": message.content if message.content else None,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": tc.type,
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                } for tc in tool_calls
                            ]
                        }
                        messages_copy.append(assistant_message)
                        
                        # 处理工具调用（异步）
                        if self.mcp_manager:
                            try:
                                self._run_async(self._handle_tool_calls(tool_calls, messages_copy))
                                # 调试：打印消息历史，确认工具结果已添加
                                print(f"[MCP] 工具调用后，消息历史长度: {len(messages_copy)}")
                                print(f"[MCP] 最后几条消息:")
                                for i, msg in enumerate(messages_copy[-3:], start=len(messages_copy)-2):
                                    role = msg.get("role", "unknown")
                                    if role == "tool":
                                        content_preview = msg.get("content", "")[:100]
                                        print(f"  [{i}] role={role}, tool_call_id={msg.get('tool_call_id')}, name={msg.get('name')}, content_preview={content_preview}")
                                    else:
                                        content_preview = str(msg.get("content", ""))[:100] if msg.get("content") else "None"
                                        print(f"  [{i}] role={role}, content_preview={content_preview}")
                            except Exception as e:
                                print(f"[MCP] 处理工具调用失败: {e}")
                                import traceback
                                traceback.print_exc()
                        
                        # 需要第二次调用
                        needs_second_call = True
                except (AttributeError, IndexError, KeyError) as e:
                    print(f"[MCP] 解析工具调用时出错: {e}")
                    # 如果解析失败，使用第一次响应
            
            # 如果需要第二次调用（工具调用后），进行第二次调用
            if needs_second_call:
                # 调试：打印第二次调用前的消息历史
                print(f"[MCP] 第二次调用前，消息历史长度: {len(messages_copy)}")
                print(f"[MCP] 第二次调用前的消息角色序列: {[msg.get('role') for msg in messages_copy[-5:]]}")
                
                # 第二次调用时，不再传递tools参数，让LLM基于工具结果生成回复
                response_to_process = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages_copy,
                    stream=stream,
                    # 注意：第二次调用不传递tools参数，避免LLM再次调用工具
                )
                is_first_response_stream = stream
                
                # 调试：打印第二次调用的响应类型
                print(f"[MCP] 第二次调用完成，响应类型: {type(response_to_process)}")
                if not is_first_response_stream:
                    if hasattr(response_to_process, 'choices') and response_to_process.choices:
                        second_content = response_to_process.choices[0].message.content
                        print(f"[MCP] 第二次调用响应内容预览: {second_content[:100] if second_content else 'None'}...")
            else:
                # 使用第一次响应，但需要根据实际的stream参数判断
                if not tools:
                    # 没有工具，使用原始的stream参数
                    is_first_response_stream = stream
                # 如果有工具但LLM决定不使用，response_to_process已经是非流式的，is_first_response_stream保持False
            
            # 统一处理响应（流式或非流式）
            self.llm_printer.print_to_window("\nMory: ")
            
            if is_first_response_stream:
                # 流式响应
                try:
                    for chunk in response_to_process:
                        # 检查chunk是否有choices属性
                        if not hasattr(chunk, 'choices'):
                            continue
                        if not chunk.choices or len(chunk.choices) == 0:
                            continue
                        
                        # 获取delta内容
                        delta = getattr(chunk.choices[0], 'delta', None)
                        if delta is None:
                            continue
                        
                        content = getattr(delta, 'content', None)
                        if content is not None:
                            # 记录首个token时间
                            if first_token_time is None:
                                first_token_time = time.time()
                            
                            # 输出内容
                            self.llm_printer.print_to_window(content)
                            full_content += content
                            token_count += 1
                            
                            # 调用内容回调
                            if on_content:
                                on_content(content)
                except (AttributeError, TypeError) as e:
                    print(f"[错误] 处理流式响应时出错: {e}")
                    # 如果流式处理失败，尝试作为非流式处理
                    if hasattr(response_to_process, 'choices') and response_to_process.choices:
                        content = response_to_process.choices[0].message.content
                        if content:
                            full_content = content
                            self.llm_printer.print_to_window(content)
                            if first_token_time is None:
                                first_token_time = time.time()
                            if on_content:
                                for char in content:
                                    on_content(char)
            else:
                # 非流式响应
                try:
                    if hasattr(response_to_process, 'choices') and response_to_process.choices:
                        content = response_to_process.choices[0].message.content
                        if content:
                            full_content = content
                            # 输出内容
                            self.llm_printer.print_to_window(content)
                            
                            # 记录首个token时间
                            if first_token_time is None:
                                first_token_time = time.time()
                            
                            # 调用内容回调（模拟流式）
                            if on_content:
                                for char in content:
                                    on_content(char)
                except (AttributeError, IndexError, KeyError) as e:
                    print(f"[错误] 处理非流式响应时出错: {e}")
                    import traceback
                    traceback.print_exc()
            
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
            import traceback
            traceback.print_exc()
            
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
