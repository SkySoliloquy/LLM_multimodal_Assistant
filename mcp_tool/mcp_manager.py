# mcp_manager.py
# MCP管理器模块 - 管理多个MCP服务器和工具
"""
MCP管理器，负责管理多个MCP服务器连接，统一工具管理和调用。
"""

import asyncio
from typing import Dict, List, Optional, Any

try:
    from .mcp_client import MCPClient
    try:
        from mcp.types import Tool, CallToolResult
    except ImportError:
        # 如果mcp库未安装，使用占位类型
        class Tool:
            def __init__(self, name="", description="", inputSchema=None):
                self.name = name
                self.description = description
                self.inputSchema = inputSchema or {}
        class CallToolResult:
            def __init__(self, content=None, isError=False):
                self.content = content or []
                self.isError = isError
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # 定义占位类型
    class Tool:
        def __init__(self, name="", description="", inputSchema=None):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema or {}
    class CallToolResult:
        def __init__(self, content=None, isError=False):
            self.content = content or []
            self.isError = isError
    class MCPClient:
        pass


class MCPManager:
    """MCP管理器，管理多个MCP服务器"""
    
    def __init__(self, servers_config: List[Dict[str, Any]]):
        """
        初始化MCP管理器
        
        Args:
            servers_config: MCP服务器配置列表
                [
                    {
                        "name": "server1",
                        "type": "http",
                        "url": "https://...",
                        "headers": {}
                    },
                    {
                        "name": "server2",
                        "type": "stdio",
                        "command": "python",
                        "args": ["server.py"]
                    }
                ]
        """
        # 检查是否需要MCP库（只有stdio模式需要）
        has_stdio = any(server.get("type") == "stdio" for server in servers_config)
        if has_stdio and not MCP_AVAILABLE:
            raise ImportError("MCP库未安装，无法使用stdio传输。请安装: pip install 'mcp[cli]'")
        
        self.servers_config = servers_config
        self.clients: Dict[str, MCPClient] = {}
        self.all_tools: Dict[str, Tool] = {}  # tool_name -> Tool
        self.tool_to_server: Dict[str, str] = {}  # tool_name -> server_name
        self.connected = False
    
    async def connect_all(self):
        """连接所有MCP服务器"""
        if self.connected:
            return
        
        print(f"[MCP Manager] 正在连接 {len(self.servers_config)} 个MCP服务器...")
        
        for server_config in self.servers_config:
            name = server_config.get("name")
            if not name:
                print(f"[MCP Manager] 警告: 跳过未命名的服务器配置")
                continue
            
            try:
                client = MCPClient(name, server_config)
                await client.connect()
                self.clients[name] = client
                
                # 收集工具
                tools = await client.list_tools()
                for tool in tools:
                    if tool.name in self.all_tools:
                        print(f"[MCP Manager] 警告: 工具 {tool.name} 在多个服务器中存在，使用 {name} 服务器的版本")
                    self.all_tools[tool.name] = tool
                    self.tool_to_server[tool.name] = name
                
                print(f"[MCP Manager] 服务器 {name} 连接成功，提供 {len(tools)} 个工具")
                
            except Exception as e:
                print(f"[MCP Manager] 错误: 连接服务器 {name} 失败: {e}")
                continue
        
        self.connected = True
        total_tools = len(self.all_tools)
        print(f"[MCP Manager] 连接完成，共 {total_tools} 个可用工具")
    
    async def disconnect_all(self):
        """断开所有MCP服务器连接"""
        if not self.connected:
            return
        
        for name, client in self.clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                print(f"[MCP Manager] 错误: 断开服务器 {name} 失败: {e}")
        
        self.clients.clear()
        self.all_tools.clear()
        self.tool_to_server.clear()
        self.connected = False
    
    def get_all_tools(self) -> List[Tool]:
        """获取所有工具列表"""
        return list(self.all_tools.values())
    
    def get_tools_openai_format(self) -> List[Dict[str, Any]]:
        """获取所有工具的OpenAI格式"""
        openai_tools = []
        for tool in self.all_tools.values():
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
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            CallToolResult: 工具调用结果
        """
        if not self.connected:
            await self.connect_all()
        
        if tool_name not in self.tool_to_server:
            raise ValueError(f"工具 {tool_name} 不存在")
        
        server_name = self.tool_to_server[tool_name]
        client = self.clients.get(server_name)
        
        if not client:
            raise ValueError(f"服务器 {server_name} 未连接")
        
        return await client.call_tool(tool_name, arguments)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect_all()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.disconnect_all()

