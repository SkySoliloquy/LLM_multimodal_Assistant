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
    
    def _detect_tool_call_trigger(self, content: str, delta, chunk) -> bool:
        """
        检测工具调用触发标识符
        
        Args:
            content: 当前累积的文本内容
            delta: 当前chunk的delta对象
            chunk: 当前chunk对象
            
        Returns:
            True如果检测到工具调用标识符
        """
        # 方法1: 检测OpenAI流式响应中的tool_calls
        if delta and hasattr(delta, 'tool_calls') and delta.tool_calls:
            return True
        
        # 方法2: 检测finish_reason为tool_calls
        if chunk and hasattr(chunk.choices[0], 'finish_reason'):
            finish_reason = chunk.choices[0].finish_reason
            if finish_reason == 'tool_calls':
                return True
        
        # 方法3: 检测文本中的工具调用标识符（示例：检测"<function_calls>"等）
        # 可以根据实际情况调整标识符
        tool_call_markers = ["<function_calls>", "<tool_call", "<invoke", "```function_call"]
        content_lower = content.lower()
        for marker in tool_call_markers:
            if marker.lower() in content_lower:
                return True
        
        return False
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       stream: bool = True,
                       on_content: Optional[Callable[[str], None]] = None,
                       on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
                       on_tool_call_detected: Optional[Callable[[], None]] = None) -> Dict[str, Any]:
        """
        发送聊天完成请求（支持流式MCP工具调用检测）
        
        Args:
            messages: 消息列表
            stream: 是否使用流式输出（总是使用流式）
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
            
            # 总是使用流式输出
            if not stream:
                print("[警告] 已强制启用流式输出以支持工具调用检测")
            
            # 第一阶段：流式检测工具调用标识符
            # 累积的内容（用于检测工具调用）
            accumulated_content = ""
            # 传递给TTS的内容（检测到工具调用前的部分）
            tts_content_before_tool = ""
            # 是否已检测到工具调用
            tool_call_detected = False
            # 是否进入MCP循环（进入后不再向TTS传递内容）
            in_mcp_loop = False
            # 工具调用的响应对象
            tool_call_response = None
            
            # 第一次流式调用：检测工具调用
            self.llm_printer.print_to_window("\nMory: ")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages_copy,
                tools=tools,  # 如果有工具，传递给LLM
                tool_choice="auto" if tools else None,
                stream=True  # 总是使用流式
            )
            
            # 处理流式响应
            last_chunk = None
            try:
                for chunk in response:
                    # 检查chunk是否有choices属性
                    if not hasattr(chunk, 'choices'):
                        continue
                    if not chunk.choices or len(chunk.choices) == 0:
                        continue
                    
                    last_chunk = chunk  # 保存最后一个chunk用于检测finish_reason
                    
                    # 获取delta内容
                    delta = getattr(chunk.choices[0], 'delta', None)
                    if delta is None:
                        # 检查finish_reason
                        finish_reason = getattr(chunk.choices[0], 'finish_reason', None)
                        if finish_reason == 'tool_calls' and not tool_call_detected:
                            tool_call_detected = True
                            in_mcp_loop = True
                            print(f"[MCP] 流式响应结束，检测到工具调用（finish_reason），已传递内容: {tts_content_before_tool[:100]}...")
                        continue
                    
                    # 检测工具调用标识符（在delta中）
                    if not tool_call_detected:
                        # 检查delta中是否有tool_calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            tool_call_detected = True
                            in_mcp_loop = True
                            print(f"[MCP] 检测到工具调用标识符（delta.tool_calls），已传递内容: {tts_content_before_tool[:100]}...")
                            # 确保工具调用前的内容被完整传递给TTS
                            # 如果还有缓冲内容未传递，先传递完
                            if tts_content_before_tool and on_content:
                                # 触发一个额外的回调，确保内容被完整处理
                                print(f"[MCP] 确保工具调用前的内容被完整传递: {len(tts_content_before_tool)} 字符")
                            # 继续处理剩余的chunk，但不传递给TTS
                        # 检查文本中的工具调用标识符
                        elif self._detect_tool_call_trigger(accumulated_content, delta, chunk):
                            tool_call_detected = True
                            in_mcp_loop = True
                            print(f"[MCP] 检测到工具调用标识符（文本），已传递内容: {tts_content_before_tool[:100]}...")
                            # 确保工具调用前的内容被完整传递给TTS
                            if tts_content_before_tool and on_content:
                                print(f"[MCP] 确保工具调用前的内容被完整传递: {len(tts_content_before_tool)} 字符")
                            # 不break，继续处理流式响应以获取完整的tool_calls
                    
                    content = getattr(delta, 'content', None)
                    if content is not None:
                        # 记录首个token时间
                        if first_token_time is None:
                            first_token_time = time.time()
                        
                        accumulated_content += content
                        full_content += content
                        token_count += 1
                        
                        # 如果还没检测到工具调用，继续向TTS传递内容
                        if not tool_call_detected:
                            tts_content_before_tool += content
                            # 输出内容
                            self.llm_printer.print_to_window(content)
                            # 调用内容回调
                            if on_content:
                                on_content(content)
                        else:
                            # 已检测到工具调用，只输出不传递给TTS
                            self.llm_printer.print_to_window(content)
                
                # 检查最后一个chunk的finish_reason
                if last_chunk and hasattr(last_chunk.choices[0], 'finish_reason'):
                    finish_reason = last_chunk.choices[0].finish_reason
                    if finish_reason == 'tool_calls' and not tool_call_detected:
                        tool_call_detected = True
                        in_mcp_loop = True
                        print(f"[MCP] 流式响应结束，检测到工具调用（finish_reason），已传递内容: {tts_content_before_tool[:100]}...")
                        # 确保工具调用前的内容被完整传递给TTS
                        if tts_content_before_tool and on_content:
                            print(f"[MCP] 确保工具调用前的内容被完整传递: {len(tts_content_before_tool)} 字符")
                            
            except (AttributeError, TypeError) as e:
                print(f"[错误] 处理流式响应时出错: {e}")
                import traceback
                traceback.print_exc()
            
            # 如果检测到工具调用，工具调用前的内容已经通过on_content流式传递给TTS了
            # 通过回调通知强制刷新TTS缓冲区，确保工具调用前的内容被立即处理
            if tool_call_detected and tts_content_before_tool:
                print(f"[MCP] 工具调用前的内容已流式传递给TTS: {len(tts_content_before_tool)} 字符，触发强制刷新")
                # 触发工具调用检测回调，用于强制刷新TTS缓冲区
                if on_tool_call_detected:
                    try:
                        on_tool_call_detected()
                    except Exception as e:
                        print(f"[MCP] 触发工具调用检测回调失败: {e}")
            
            # 第二阶段：MCP工具调用循环（最多3次）
            max_tool_call_iterations = 3
            tool_call_iteration = 0
            
            # 如果检测到工具调用，需要先获取完整的tool_calls
            first_tool_calls = None
            if tool_call_detected and tool_call_iteration == 0:
                # 重新进行非流式调用来获取完整的tool_calls
                tool_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages_copy,
                    tools=tools,
                    tool_choice="auto",
                    stream=False
                )
                
                if hasattr(tool_response, 'choices') and tool_response.choices:
                    message = tool_response.choices[0].message
                    first_tool_calls = getattr(message, 'tool_calls', None) if hasattr(message, 'tool_calls') else None
                    
                    # 更新工具调用前的内容
                    if message.content and not tts_content_before_tool:
                        tts_content_before_tool = message.content
                        print(f"[MCP] 工具调用前的内容: {tts_content_before_tool[:100]}...")
                    
                    if not first_tool_calls:
                        # 如果没有工具调用，说明检测有误
                        tool_call_detected = False
                        in_mcp_loop = False
            
            while tool_call_detected and tool_call_iteration < max_tool_call_iterations:
                tool_call_iteration += 1
                print(f"[MCP] 第 {tool_call_iteration} 次工具调用循环")
                
                # 如果是第3次，提醒LLM这是最后一次（在第3次之前添加）
                if tool_call_iteration == max_tool_call_iterations:
                    reminder_message = {
                        "role": "system",
                        "content": "重要提示：这是最后一次工具调用机会。如果此次调用后仍然没有获得合适的答案，请直接返回最终回复，不要再使用工具调用语法。"
                    }
                    # 将提醒消息添加到消息历史（插入到system消息之后，其他消息之前）
                    # 查找第一个system消息的位置，在其后插入
                    system_index = -1
                    for i, msg in enumerate(messages_copy):
                        if msg.get("role") == "system":
                            system_index = i
                            break
                    if system_index >= 0:
                        messages_copy.insert(system_index + 1, reminder_message)
                    else:
                        messages_copy.insert(0, reminder_message)
                
                # 获取当前循环的工具调用
                if tool_call_iteration == 1:
                    # 第1次迭代，使用第一次检测到的工具调用
                    tool_calls = first_tool_calls
                else:
                    # 第2次和第3次迭代，使用上一次循环中更新的first_tool_calls
                    # first_tool_calls在循环外部定义，在循环内部可以直接访问和更新
                    tool_calls = first_tool_calls
                
                # 如果仍然没有工具调用，跳出循环
                if not tool_calls:
                    print(f"[MCP] 未检测到工具调用，跳出循环")
                    break
                
                print(f"[MCP] LLM请求使用 {len(tool_calls)} 个工具")
                
                # 添加助手消息（包含工具调用）到消息历史
                assistant_message = {
                    "role": "assistant",
                    "content": None,  # 工具调用时content通常为None
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
                    except Exception as e:
                        print(f"[MCP] 处理工具调用失败: {e}")
                        import traceback
                        traceback.print_exc()
                
                # 如果已经达到最大迭代次数，强制返回回复
                if tool_call_iteration >= max_tool_call_iterations:
                    # 最后一次调用，不传递tools，强制LLM返回回复
                    # 使用流式响应来获取最终回复，保持流式传递给TTS
                    final_response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages_copy,
                        tools=None,  # 不传递tools，让LLM直接返回回复
                        stream=True  # 使用流式，保持与工具调用前的内容一致的流式处理
                    )
                    
                    final_content = ""
                    if hasattr(final_response, '__iter__'):
                        # 处理流式响应
                        self.llm_printer.print_to_window("\n[MCP循环结束] ")
                        for chunk in final_response:
                            if not hasattr(chunk, 'choices') or not chunk.choices:
                                continue
                            
                            delta = getattr(chunk.choices[0], 'delta', None)
                            if delta is None:
                                continue
                            
                            content = getattr(delta, 'content', None)
                            if content:
                                final_content += content
                                # 输出内容
                                self.llm_printer.print_to_window(content)
                                # 流式传递给TTS
                                if on_content:
                                    on_content(content)
                                
                                # 记录首个token时间（如果还没有）
                                if first_token_time is None:
                                    first_token_time = time.time()
                    
                    # 如果流式响应没有返回内容，使用非流式作为备用
                    if not final_content:
                        fallback_response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages_copy,
                            tools=None,
                            stream=False
                        )
                        if hasattr(fallback_response, 'choices') and fallback_response.choices:
                            final_message = fallback_response.choices[0].message
                            if final_message.content:
                                final_content = final_message.content
                                # 输出最终回复
                                self.llm_printer.print_to_window("\n[MCP循环结束] ")
                                self.llm_printer.print_to_window(final_content)
                                
                                # 记录首个token时间（如果还没有）
                                if first_token_time is None:
                                    first_token_time = time.time()
                                
                                # 模拟流式传递给TTS
                                if on_content:
                                    for char in final_content:
                                        on_content(char)
                    
                    full_content = final_content
                    break
                
                # 进行下一次LLM调用（检查是否还需要工具调用）
                next_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages_copy,
                    tools=tools,  # 仍然传递tools，让LLM决定是否继续使用
                    tool_choice="auto",
                    stream=True  # 使用流式检测
                )
                
                # 处理流式响应，检测是否还有工具调用
                tool_call_detected_next = False
                accumulated_content_next = ""
                temp_content_for_check = ""
                last_chunk_next = None
                
                for chunk in next_response:
                    if not hasattr(chunk, 'choices') or not chunk.choices:
                        continue
                    
                    last_chunk_next = chunk
                    delta = getattr(chunk.choices[0], 'delta', None)
                    if delta is None:
                        # 检查finish_reason
                        finish_reason = getattr(chunk.choices[0], 'finish_reason', None)
                        if finish_reason == 'tool_calls':
                            tool_call_detected_next = True
                        continue
                    
                    # 检测工具调用
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        tool_call_detected_next = True
                    elif self._detect_tool_call_trigger(temp_content_for_check, delta, chunk):
                        tool_call_detected_next = True
                    
                    content = getattr(delta, 'content', None)
                    if content:
                        temp_content_for_check += content
                        accumulated_content_next += content
                        # 在MCP循环中，只输出不传递给TTS
                        self.llm_printer.print_to_window(content)
                
                # 检查最后一个chunk的finish_reason
                if last_chunk_next and hasattr(last_chunk_next.choices[0], 'finish_reason'):
                    finish_reason = last_chunk_next.choices[0].finish_reason
                    if finish_reason == 'tool_calls':
                        tool_call_detected_next = True
                
                # 如果没有检测到工具调用，获取完整内容并退出循环
                if not tool_call_detected_next:
                    # 使用流式响应来获取最终回复，保持流式传递给TTS
                    final_response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages_copy,
                        tools=None,  # 不传递tools，让LLM直接返回回复
                        stream=True  # 使用流式，保持与工具调用前的内容一致的流式处理
                    )
                    
                    final_content = ""
                    if hasattr(final_response, '__iter__'):
                        # 处理流式响应
                        self.llm_printer.print_to_window("\n[MCP循环结束] ")
                        for chunk in final_response:
                            if not hasattr(chunk, 'choices') or not chunk.choices:
                                continue
                            
                            delta = getattr(chunk.choices[0], 'delta', None)
                            if delta is None:
                                continue
                            
                            content = getattr(delta, 'content', None)
                            if content:
                                final_content += content
                                # 输出内容
                                self.llm_printer.print_to_window(content)
                                # 流式传递给TTS
                                if on_content:
                                    on_content(content)
                                
                                # 记录首个token时间（如果还没有）
                                if first_token_time is None:
                                    first_token_time = time.time()
                    
                    # 如果流式响应没有返回内容，使用非流式作为备用
                    if not final_content:
                        fallback_response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages_copy,
                            tools=None,
                            stream=False
                        )
                        if hasattr(fallback_response, 'choices') and fallback_response.choices:
                            final_message = fallback_response.choices[0].message
                            if final_message.content:
                                final_content = final_message.content
                                # 输出最终回复
                                self.llm_printer.print_to_window("\n[MCP循环结束] ")
                                self.llm_printer.print_to_window(final_content)
                                
                                # 记录首个token时间（如果还没有）
                                if first_token_time is None:
                                    first_token_time = time.time()
                                
                                # 模拟流式传递给TTS
                                if on_content:
                                    for char in final_content:
                                        on_content(char)
                    
                    full_content = final_content
                    break
                else:
                    # 还有工具调用，准备下一次循环
                    # 获取完整的tool_calls
                    tool_response_next = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages_copy,
                        tools=tools,
                        tool_choice="auto",
                        stream=False
                    )
                    
                    if hasattr(tool_response_next, 'choices') and tool_response_next.choices:
                        message_next = tool_response_next.choices[0].message
                        first_tool_calls = getattr(message_next, 'tool_calls', None) if hasattr(message_next, 'tool_calls') else None
                        if first_tool_calls:
                            tool_call_detected = True
                        else:
                            # 如果没有工具调用，说明LLM决定返回回复
                            # 使用流式响应来获取最终回复，保持流式传递给TTS
                            final_stream_response = self.client.chat.completions.create(
                                model=self.model_name,
                                messages=messages_copy,
                                tools=None,
                                stream=True  # 使用流式，保持与工具调用前的内容一致的流式处理
                            )
                            
                            final_stream_content = ""
                            if hasattr(final_stream_response, '__iter__'):
                                # 处理流式响应
                                self.llm_printer.print_to_window("\n[MCP循环结束] ")
                                for chunk in final_stream_response:
                                    if not hasattr(chunk, 'choices') or not chunk.choices:
                                        continue
                                    
                                    delta = getattr(chunk.choices[0], 'delta', None)
                                    if delta is None:
                                        continue
                                    
                                    content = getattr(delta, 'content', None)
                                    if content:
                                        final_stream_content += content
                                        # 输出内容
                                        self.llm_printer.print_to_window(content)
                                        # 流式传递给TTS
                                        if on_content:
                                            on_content(content)
                                        
                                        # 记录首个token时间（如果还没有）
                                        if first_token_time is None:
                                            first_token_time = time.time()
                            
                            # 如果流式响应没有返回内容，使用非流式作为备用
                            if not final_stream_content and message_next.content:
                                final_stream_content = message_next.content
                                # 输出最终回复
                                self.llm_printer.print_to_window("\n[MCP循环结束] ")
                                self.llm_printer.print_to_window(final_stream_content)
                                
                                # 记录首个token时间（如果还没有）
                                if first_token_time is None:
                                    first_token_time = time.time()
                                
                                # 模拟流式传递给TTS
                                if on_content:
                                    for char in final_stream_content:
                                        on_content(char)
                            
                            full_content = final_stream_content
                            tool_call_detected = False
            
            # 如果之前没有进入MCP循环，说明没有工具调用，直接使用第一次流式响应的内容
            if not in_mcp_loop:
                full_content = tts_content_before_tool if tts_content_before_tool else accumulated_content
            else:
                # 如果进入了MCP循环，需要将工具调用前的内容和最终回复组合
                # 工具调用前的内容 + 最终回复
                if tts_content_before_tool:
                    if full_content:
                        # 如果最终回复不为空，组合它们
                        full_content = tts_content_before_tool + "\n" + full_content
                    else:
                        # 如果最终回复为空，只使用工具调用前的内容
                        full_content = tts_content_before_tool
                    print(f"[MCP] 组合后的完整回复: {len(tts_content_before_tool)} (工具调用前) + {len(full_content) - len(tts_content_before_tool)} (最终回复) = {len(full_content)} 字符")
            
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
