# MCP集成使用指南

## 概述

本指南说明如何将MCP协议集成到SenseVoice项目中，使LLM能够使用外部工具。

## 文件说明

### 核心模块

1. **mcp_client.py** - MCP客户端模块
   - `MCPClient`: MCP客户端类，支持HTTP和stdio两种传输方式
   - `HTTPMCPSession`: HTTP传输实现

2. **mcp_manager.py** - MCP管理器模块
   - `MCPManager`: 管理多个MCP服务器，统一工具管理

3. **mcp_config_example.py** - MCP配置示例
   - 展示如何配置MCP服务器

## 集成步骤

### 步骤1: 在config.py中添加MCP配置

```python
# config.py

# MCP配置
MCP_CONFIG = {
    "enabled": True,  # 是否启用MCP功能
    "servers": [
        {
            "name": "bing-search",
            "type": "http",
            "url": "https://mcp.api-inference.modelscope.net/bd586c64cbff4c/mcp",
            "headers": {}
        },
        # {
        #     "name": "local-tools",
        #     "type": "stdio",
        #     "command": "python",
        #     "args": ["simple_mcp_server.py"]
        # }
    ]
}
```

### 步骤2: 在voice_chat.py中初始化MCPManager

```python
# voice_chat.py

from mcp_manager import MCPManager
from config import MCP_CONFIG

class VoiceChatSystem:
    def __init__(self):
        # ... 现有初始化代码 ...
        
        # 初始化MCP管理器
        self.mcp_manager = None
        if MCP_CONFIG.get("enabled"):
            servers_config = MCP_CONFIG.get("servers", [])
            if servers_config:
                self.mcp_manager = MCPManager(servers_config)
                # 异步连接（需要在异步环境中调用）
                # await self.mcp_manager.connect_all()
        
        # ... 其他初始化代码 ...
```

### 步骤3: 修改llm_client.py支持工具调用

```python
# llm_client.py

class LLMClient:
    def __init__(self, api_key, base_url, model_name, mcp_manager=None):
        # ... 现有初始化代码 ...
        self.mcp_manager = mcp_manager
    
    async def chat_completion(self, messages, stream, on_content, on_complete):
        """发送聊天请求并处理响应（支持工具调用）"""
        
        # 获取工具列表（如果MCP管理器可用）
        tools = None
        if self.mcp_manager:
            tools = self.mcp_manager.get_tools_openai_format()
        
        # 第一次调用：检查是否需要工具调用
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=stream,
        )
        
        # 处理工具调用
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            # 有工具调用，执行工具
            tool_calls = response.choices[0].message.tool_calls
            messages.append(response.choices[0].message)
            
            # 执行每个工具调用
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # 调用工具
                if self.mcp_manager:
                    result = await self.mcp_manager.call_tool(tool_name, tool_args)
                    
                    # 添加工具结果到消息历史
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": result.content[0].text if result.content else "执行完成"
                    }
                    messages.append(tool_message)
            
            # 第二次调用：基于工具结果生成回复
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=stream,
            )
        
        # 处理响应（流式或非流式）
        # ... 现有响应处理代码 ...
```

### 步骤4: 在voice_chat.py中传递MCPManager给LLMClient

```python
# voice_chat.py

class VoiceChatSystem:
    def __init__(self):
        # ... 现有代码 ...
        
        # 初始化MCP管理器
        self.mcp_manager = None
        if MCP_CONFIG.get("enabled"):
            servers_config = MCP_CONFIG.get("servers", [])
            if servers_config:
                self.mcp_manager = MCPManager(servers_config)
        
        # 初始化LLM客户端（传递MCP管理器）
        self.llm_client = LLMClient(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            model_name=Config.LLM_MODEL_NAME,
            mcp_manager=self.mcp_manager  # 传递MCP管理器
        )
        
        # ... 其他代码 ...
    
    async def _initialize_mcp(self):
        """初始化MCP连接（异步）"""
        if self.mcp_manager:
            await self.mcp_manager.connect_all()
    
    async def run(self):
        """运行主循环"""
        # 初始化MCP连接
        await self._initialize_mcp()
        
        # ... 现有运行逻辑 ...
```

## 配置示例

### HTTP MCP服务器

```python
{
    "name": "bing-search",
    "type": "http",
    "url": "https://mcp.api-inference.modelscope.net/bd586c64cbff4c/mcp",
    "headers": {
        # 可选：添加认证头等
        # "Authorization": "Bearer your-token"
    }
}
```

### stdio MCP服务器

```python
{
    "name": "local-tools",
    "type": "stdio",
    "command": "python",
    "args": ["simple_mcp_server.py"]
}
```

## 测试

运行测试脚本验证集成：

```bash
python test_mcp_integration.py
```

## 注意事项

1. **异步初始化**: MCP管理器需要在异步环境中初始化连接
2. **错误处理**: 工具调用可能失败，需要适当的错误处理
3. **性能**: 工具调用会增加延迟，考虑用户体验
4. **配置管理**: MCP配置可以通过配置文件或环境变量管理
5. **向后兼容**: MCP功能是可选的，不影响现有功能

## 工作流程

1. **初始化阶段**:
   - 加载MCP配置
   - 创建MCPManager
   - 连接所有MCP服务器
   - 获取工具列表
   - 将MCPManager传递给LLMClient

2. **对话阶段**:
   - 用户输入 -> LLMClient
   - LLMClient检查是否有可用工具
   - 如果有工具，将工具列表发送给LLM
   - LLM决定是否调用工具
   - 如果调用工具，MCPManager执行工具调用
   - 将工具结果返回给LLM
   - LLM生成最终回复

## 扩展

- 添加更多MCP服务器
- 支持工具调用链
- 添加工具调用缓存
- 支持工具调用重试
- 添加工具调用统计

