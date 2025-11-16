# mcp_client.py
# MCP客户端模块 - 负责管理MCP服务器连接
"""
MCP客户端模块，提供统一的接口连接和管理MCP服务器。
支持HTTP和stdio两种传输方式。
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import InitializeResult, ListToolsResult, CallToolResult, Tool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # 定义占位类型，避免导入错误
    class ClientSession:
        pass
    class StdioServerParameters:
        pass
    class InitializeResult:
        pass
    class ListToolsResult:
        pass
    class CallToolResult:
        pass
    class Tool:
        pass

import requests


class HTTPMCPSession:
    """HTTP MCP会话实现，提供与ClientSession兼容的接口"""
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.session = requests.Session()
        self.session_id: Optional[str] = None
        self.request_id = 0
        self.initialized = False
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **(headers or {})
        }
    
    def _get_next_id(self) -> int:
        self.request_id += 1
        return self.request_id
    
    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None, include_empty_params: bool = False) -> Dict[str, Any]:
        """发送JSON-RPC请求"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._get_next_id(),
        }
        if params is not None or include_empty_params:
            request["params"] = params if params is not None else {}
        
        headers = self.headers.copy()
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        try:
            response = self.session.post(
                self.url,
                json=request,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # 检查是否有session ID
            if "Mcp-Session-Id" in response.headers:
                self.session_id = response.headers["Mcp-Session-Id"]
            
            if "error" in result:
                raise Exception(f"MCP Error: {result['error']}")
            
            return result.get("result", {})
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP Error: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON Decode Error: {e}")
    
    async def initialize(self):
        """初始化MCP连接"""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "mcp_tool-http-client",
                "version": "1.0.0"
            }
        }
        
        result = self._send_request("initialize", params)
        self.initialized = True
        
        # 发送initialized通知（通知不需要id和响应）
        try:
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            headers = self.headers.copy()
            if self.session_id:
                headers["Mcp-Session-Id"] = self.session_id
            
            self.session.post(
                self.url,
                json=notification,
                headers=headers,
                timeout=5
            )
        except:
            pass  # 通知发送失败不影响主流程
        
        # 如果没有mcp库，返回一个简单的对象
        try:
            from mcp.types import InitializeResult
            return InitializeResult(
                protocolVersion=result.get("protocolVersion", "2024-11-05"),
                capabilities=result.get("capabilities", {}),
                serverInfo=result.get("serverInfo", {})
            )
        except ImportError:
            # 创建一个简单的命名空间对象
            class SimpleResult:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)
            return SimpleResult(
                protocolVersion=result.get("protocolVersion", "2024-11-05"),
                capabilities=result.get("capabilities", {}),
                serverInfo=result.get("serverInfo", {})
            )
    
    async def list_tools(self):
        """列出可用工具"""
        if not self.initialized:
            await self.initialize()
        
        result = self._send_request("tools/list", {}, include_empty_params=True)
        
        try:
            from mcp.types import Tool, ListToolsResult
            tools = [
                Tool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    inputSchema=tool.get("inputSchema", {})
                )
                for tool in result.get("tools", [])
            ]
            return ListToolsResult(tools=tools)
        except ImportError:
            # 如果没有mcp库，创建简单的对象
            class SimpleTool:
                def __init__(self, name, description, inputSchema):
                    self.name = name
                    self.description = description
                    self.inputSchema = inputSchema
            
            class SimpleListToolsResult:
                def __init__(self, tools):
                    self.tools = tools
            
            tools = [
                SimpleTool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    inputSchema=tool.get("inputSchema", {})
                )
                for tool in result.get("tools", [])
            ]
            return SimpleListToolsResult(tools=tools)
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """调用工具"""
        if not self.initialized:
            await self.initialize()
        
        params = {
            "name": name,
            "arguments": arguments
        }
        
        result = self._send_request("tools/call", params)
        
        # 调试：打印原始响应
        print(f"[MCP HTTP] 工具调用原始响应: {result}")
        
        # 动态导入类型，避免在没有mcp库时出错
        try:
            from mcp.types import TextContent, CallToolResult
        except ImportError:
            # 如果没有mcp库，创建简单的类
            class TextContent:
                def __init__(self, type, text):
                    self.type = type
                    self.text = text
            
            class CallToolResult:
                def __init__(self, content, isError):
                    self.content = content
                    self.isError = isError
        
        content = []
        if "content" in result:
            content_list = result["content"]
            print(f"[MCP HTTP] 内容列表类型: {type(content_list)}, 长度: {len(content_list) if isinstance(content_list, list) else 'N/A'}")
            
            for item in content_list:
                print(f"[MCP HTTP] 处理内容项: {type(item)}, 内容: {item}")
                if isinstance(item, dict):
                    item_type = item.get("type", "")
                    if item_type == "text":
                        text = item.get("text", "")
                        print(f"[MCP HTTP] 提取文本内容: {text[:100]}...")
                        content.append(TextContent(type="text", text=text))
                    else:
                        # 如果不是text类型，也尝试提取文本
                        print(f"[MCP HTTP] 未知内容类型: {item_type}, 尝试提取文本")
                        if "text" in item:
                            content.append(TextContent(type="text", text=item.get("text", "")))
                        elif "content" in item:
                            # 嵌套内容
                            nested_content = item.get("content", "")
                            if isinstance(nested_content, str):
                                content.append(TextContent(type="text", text=nested_content))
                elif isinstance(item, str):
                    # 直接是字符串
                    print(f"[MCP HTTP] 内容项是字符串: {item[:100]}...")
                    content.append(TextContent(type="text", text=item))
        
        is_error = result.get("isError", False)
        print(f"[MCP HTTP] 工具调用结果: isError={is_error}, content数量={len(content)}")
        
        return CallToolResult(
            content=content,
            isError=is_error
        )
    
    async def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class MCPClient:
    """MCP客户端，提供统一的接口连接MCP服务器"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化MCP客户端
        
        Args:
            name: MCP服务器名称
            config: MCP服务器配置
                - type: "http" 或 "stdio"
                - 对于HTTP: url, headers (可选)
                - 对于stdio: command, args
        """
        self.name = name
        self.config = config
        self.session = None
        self.available_tools = []
        self._exit_stack = AsyncExitStack()
        self._stdio_ctx = None  # 保存 stdio 上下文，用于正确关闭
        transport_type = config.get("type", "stdio") or "stdio"
        self.original_transport_type = transport_type
        # 兼容 streamable_http 配置，将其视为 HTTP 传输但标记支持流式
        self.is_streamable_http = False
        if transport_type.lower() == "streamable_http":
            self.transport_type = "http"
            self.is_streamable_http = True
        else:
            self.transport_type = transport_type.lower()
        
        if not MCP_AVAILABLE and self.transport_type == "stdio":
            raise ImportError("MCP库未安装，无法使用stdio传输。请安装: pip install 'mcp[cli]'")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.disconnect()
    
    async def connect(self):
        """连接到MCP服务器"""
        if self.transport_type == "http":
            # HTTP传输
            url = self.config.get("url")
            if not url:
                raise ValueError(f"MCP服务器 {self.name} 缺少url配置")
            
            headers = self.config.get("headers", {})
            self.session = HTTPMCPSession(url, headers)
            await self._exit_stack.enter_async_context(self.session)
            
        elif self.transport_type == "stdio":
            # stdio传输
            if not MCP_AVAILABLE:
                raise ImportError("MCP库未安装，无法使用stdio传输")
            
            command = self.config.get("command", "python")
            args = self.config.get("args", [])
            if not args:
                raise ValueError(f"MCP服务器 {self.name} 缺少args配置")
            
            # 准备环境变量
            env = os.environ.copy()
            if "env" in self.config:
                env.update(self.config["env"])
            # 确保 UTF-8 环境变量
            if sys.platform == "win32":
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
            
            # 创建服务器参数，如果支持 env 参数则传递
            try:
                # 尝试使用 env 参数（如果 StdioServerParameters 支持）
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env
                )
            except TypeError:
                # 如果不支持 env 参数，使用默认方式
                # 注意：环境变量应该已经通过 os.environ 设置
                server_params = StdioServerParameters(
                    command=command,
                    args=args
                )
            
            # 创建 stdio 客户端上下文
            self._stdio_ctx = stdio_client(server_params)
            # 进入 stdio 上下文，获取流
            read_stream, write_stream = await self._exit_stack.enter_async_context(self._stdio_ctx)
            
            # 创建客户端会话上下文
            session_ctx = ClientSession(read_stream, write_stream)
            self.session = await self._exit_stack.enter_async_context(session_ctx)
        else:
            raise ValueError(f"不支持的传输类型: {self.original_transport_type}")
        
        # 初始化会话
        await self.session.initialize()
        
        # 获取可用工具
        tools_result = await self.session.list_tools()
        self.available_tools = tools_result.tools
        
        transport_desc = "streamable_http" if self.is_streamable_http else self.transport_type
        print(f"[MCP] 连接到服务器 {self.name} (transport={transport_desc}): 发现 {len(self.available_tools)} 个工具")
    
    async def disconnect(self):
        """断开MCP服务器连接"""
        if not self.session:
            # 如果没有会话，尝试清理可能存在的上下文
            try:
                await self._exit_stack.aclose()
            except Exception:
                pass  # 忽略错误
            finally:
                self._exit_stack = AsyncExitStack()
                self._stdio_ctx = None
            return
        
        try:
            # 先关闭会话（如果存在）
            if self.session:
                try:
                    # ClientSession 有 close 方法，先调用它
                    if hasattr(self.session, 'close'):
                        await self.session.close()
                except Exception:
                    pass  # 忽略关闭时的错误
            
            # 然后关闭所有上下文管理器
            # AsyncExitStack 会按照相反的顺序关闭所有上下文
            # 这应该先关闭 ClientSession，然后关闭 stdio_client
            await self._exit_stack.aclose()
        except (GeneratorExit, RuntimeError) as e:
            # 捕获 GeneratorExit 和 RuntimeError
            # 这些错误通常发生在异步生成器在不同任务中关闭时
            # 这是已知的 anyio/mcp 库的限制，不影响功能
            error_msg = str(e).lower()
            if "cancel scope" in error_msg or "generatorexit" in error_msg:
                # 这是预期的错误，可以安全忽略
                pass
            else:
                # 其他 RuntimeError 可能需要关注
                print(f"[MCP] 警告: 断开连接时出错: {e}")
        except Exception as e:
            # 捕获其他异常，但不中断流程
            print(f"[MCP] 警告: 断开连接时出错: {e}")
        finally:
            # 确保清理状态
            self.session = None
            self.available_tools = []
            self._stdio_ctx = None
            # 创建新的 exit stack 以备下次连接使用
            self._exit_stack = AsyncExitStack()
    
    async def list_tools(self) -> List[Tool]:
        """列出可用工具"""
        if not self.session:
            await self.connect()
        return self.available_tools
    
    def _is_connection_alive(self) -> bool:
        """检查连接是否仍然有效（仅用于 stdio 传输）"""
        if self.transport_type != "stdio" or not self.session:
            return self.session is not None
        
        try:
            # 检查 write_stream 是否关闭
            if hasattr(self.session, '_write_stream'):
                write_stream = self.session._write_stream
                if hasattr(write_stream, 'closed'):
                    is_closed = write_stream.closed
                    if is_closed:
                        return False
                # 检查 read_stream 是否关闭
                if hasattr(self.session, '_read_stream'):
                    read_stream = self.session._read_stream
                    if hasattr(read_stream, 'closed'):
                        if read_stream.closed:
                            return False
            # 如果无法检查，假设连接有效（让实际调用来验证）
            return True
        except Exception:
            # 检查失败，假设连接无效，需要重新连接
            return False
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """调用工具"""
        # 检查连接状态，如果未连接或连接已断开，重新连接
        needs_reconnect = False
        if not self.session:
            needs_reconnect = True
        elif self.transport_type == "stdio":
            # 对于 stdio 传输，检查连接是否仍然有效
            if not self._is_connection_alive():
                needs_reconnect = True
        
        if needs_reconnect:
            if self.session:
                print(f"[MCP] 检测到连接已断开，重新连接服务器 {self.name}")
                try:
                    await self.disconnect()
                except Exception:
                    pass  # 忽略断开时的错误
            await self.connect()
        
        # 尝试调用工具，如果失败则重新连接
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return await self.session.call_tool(name, arguments)
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__
                
                # 检查是否是连接相关的错误
                is_connection_error = (
                    "closed" in error_str or 
                    "disconnect" in error_str or 
                    "broken" in error_str or
                    "ClosedResourceError" in error_type or
                    "ConnectionError" in error_type or
                    "GeneratorExit" in error_type or
                    error_str == ""  # 空错误信息也可能是连接问题
                )
                
                if is_connection_error and attempt < max_retries - 1:
                    print(f"[MCP] 工具调用失败（尝试 {attempt + 1}/{max_retries}），检测到连接问题，重新连接: {e if str(e) else '连接已断开'}")
                    try:
                        await self.disconnect()
                    except Exception as disconnect_error:
                        print(f"[MCP] 断开连接时出错（可忽略）: {disconnect_error}")
                    
                    # 重新连接
                    try:
                        await self.connect()
                        print(f"[MCP] 重新连接成功，重试工具调用")
                    except Exception as connect_error:
                        print(f"[MCP] 重新连接失败: {connect_error}")
                        raise
                else:
                    # 最后一次尝试或非连接错误，直接抛出
                    raise
    
    def get_tools_openai_format(self) -> List[Dict[str, Any]]:
        """将工具转换为OpenAI格式"""
        openai_tools = []
        for tool in self.available_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

