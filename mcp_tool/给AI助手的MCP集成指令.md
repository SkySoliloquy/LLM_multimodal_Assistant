# 给AI助手的MCP集成指令

## 项目背景

我正在将MCP（Model Context Protocol）协议集成到SenseVoice语音对话系统项目中。SenseVoice是一个完整的语音对话系统，包含语音识别(ASR)、大语言模型(LLM)、文本转语音(TTS)和记忆管理等功能。

## 已完成的工作

### 1. 核心模块已创建并复制到项目

以下文件已经复制到SenseVoice项目目录：

- ✅ **mcp_client.py** - MCP客户端模块
  - 支持HTTP和stdio两种传输方式
  - HTTP模式使用requests库（不依赖MCP库）
  - stdio模式需要MCP库
  - 提供统一的MCP客户端接口

- ✅ **mcp_manager.py** - MCP管理器模块
  - 管理多个MCP服务器连接
  - 统一工具列表管理
  - 工具调用路由
  - 工具格式转换（MCP -> OpenAI格式）

- ✅ **mcp_config_example.py** - MCP配置示例文件

- ✅ **三个集成文档**：
  - MCP集成方案.md
  - MCP集成使用指南.md
  - MCP集成总结.md

### 2. 项目结构

SenseVoice项目采用模块化设计，主要模块包括：

- `voice_chat.py` - 主系统模块，协调各个子模块
- `llm_client.py` - 语言模型客户端，负责与LLM API交互
- `config.py` - 配置管理模块
- `chat_manager.py` - 对话管理模块
- `asr_client.py` - 语音识别模块
- `gpt_sovits_client.py` - 语音合成模块
- 等其他模块...

## 需要完成的任务

### 任务1: 在config.py中添加MCP配置

**目标**: 添加MCP配置，使其可以从配置文件加载

**步骤**:
1. 打开`config.py`文件
2. 参考`mcp_config_example.py`，添加MCP配置
3. 配置应该包括：
   - `enabled`: 是否启用MCP功能
   - `servers`: MCP服务器列表（HTTP和stdio）

**示例配置**:
```python
# MCP配置
MCP_CONFIG = {
    "enabled": True,
    "servers": [
        {
            "name": "bing-search",
            "type": "http",
            "url": "https://mcp.api-inference.modelscope.net/bd586c64cbff4c/mcp",
            "headers": {}
        }
        # 可以添加更多服务器
        # {
        #     "name": "local-tools",
        #     "type": "stdio",
        #     "command": "python",
        #     "args": ["local_mcp_server.py"]
        # }
    ]
}
```

**注意事项**:
- 如果项目使用类方式管理配置（如`Config`类），请在类中添加MCP配置
- 确保配置可以被其他模块导入
- 考虑添加配置验证方法

### 任务2: 修改llm_client.py支持MCP工具调用

**目标**: 在LLM客户端中集成MCP工具调用功能

**需要修改的内容**:

1. **在`__init__`方法中添加mcp_manager参数**:
```python
def __init__(self, api_key, base_url, model_name, mcp_manager=None):
    # ... 现有初始化代码 ...
    self.mcp_manager = mcp_manager
```

2. **修改`chat_completion`方法支持工具调用**:
   - 检查是否有MCP管理器
   - 如果有，获取工具列表并传递给LLM
   - 处理LLM返回的tool_calls
   - 执行工具调用
   - 将工具结果添加到对话历史
   - 继续生成最终回复

**关键代码结构**:
```python
async def chat_completion(self, messages, stream, on_content, on_complete):
    # 获取工具列表（如果MCP管理器可用）
    tools = None
    if self.mcp_manager:
        tools = self.mcp_manager.get_tools_openai_format()
    
    # 第一次调用：检查是否需要工具调用
    response = self.client.chat.completions.create(
        model=self.model_name,
        messages=messages,
        tools=tools,  # 如果有工具，传递给LLM
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
    
    # 继续处理响应（流式或非流式）
    # ... 现有的响应处理代码 ...
```

**注意事项**:
- 保持现有的流式响应功能
- 保持现有的性能统计功能
- 确保工具调用不会破坏现有功能
- 处理工具调用错误
- 如果`chat_completion`不是async方法，可能需要改为async

### 任务3: 修改voice_chat.py初始化MCP管理器

**目标**: 在VoiceChatSystem中初始化MCP管理器并传递给LLMClient

**需要修改的内容**:

1. **导入MCP模块**:
```python
from mcp_manager import MCPManager
from config import MCP_CONFIG  # 或 Config.MCP_CONFIG，取决于config.py的结构
```

2. **在`__init__`方法中初始化MCP管理器**:
```python
def __init__(self):
    # ... 现有初始化代码 ...
    
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
```

3. **添加异步初始化方法**:
```python
async def _initialize_mcp(self):
    """初始化MCP连接（异步）"""
    if self.mcp_manager:
        try:
            await self.mcp_manager.connect_all()
            print("[MCP] MCP服务器连接成功")
        except Exception as e:
            print(f"[MCP] 错误: MCP服务器连接失败: {e}")
            self.mcp_manager = None  # 如果连接失败，禁用MCP
```

4. **在`run`方法中调用异步初始化**:
```python
async def run(self):
    # 初始化MCP连接
    await self._initialize_mcp()
    
    # ... 现有的运行逻辑 ...
```

**注意事项**:
- 确保在异步环境中初始化MCP连接
- 处理MCP连接失败的情况
- 如果MCP连接失败，应该降级到不使用工具的模式
- 考虑在系统启动时显示MCP连接状态

## 文件说明

### mcp_client.py
- **功能**: MCP客户端，负责连接MCP服务器
- **主要类**: `MCPClient`, `HTTPMCPSession`
- **使用方式**: 通过`MCPManager`间接使用，不需要直接调用

### mcp_manager.py
- **功能**: MCP管理器，管理多个MCP服务器
- **主要类**: `MCPManager`
- **关键方法**:
  - `connect_all()`: 连接所有MCP服务器
  - `get_tools_openai_format()`: 获取OpenAI格式的工具列表
  - `call_tool(name, arguments)`: 调用工具
  - `disconnect_all()`: 断开所有连接

### mcp_config_example.py
- **功能**: MCP配置示例
- **用途**: 参考配置格式

## 集成步骤总结

1. ✅ **复制文件** (已完成)
   - mcp_client.py
   - mcp_manager.py
   - mcp_config_example.py

2. ⏳ **在config.py中添加MCP配置**
   - 添加MCP_CONFIG配置
   - 确保配置可以被导入

3. ⏳ **修改llm_client.py**
   - 添加mcp_manager参数
   - 修改chat_completion方法支持工具调用
   - 处理工具调用流程

4. ⏳ **修改voice_chat.py**
   - 导入MCP模块
   - 初始化MCP管理器
   - 传递给LLMClient
   - 异步初始化MCP连接

5. ⏳ **测试验证**
   - 测试MCP服务器连接
   - 测试工具调用
   - 测试与LLM的集成

## 关键注意事项

### 1. 异步处理
- MCP管理器需要在异步环境中使用
- 确保`chat_completion`方法支持异步（如果需要）
- 在异步环境中初始化MCP连接

### 2. 错误处理
- 处理MCP连接失败的情况
- 处理工具调用失败的情况
- 如果MCP不可用，应该降级到不使用工具的模式

### 3. 向后兼容
- MCP功能应该是可选的
- 如果MCP未启用或连接失败，不应该影响现有功能
- 保持现有的API接口不变

### 4. 依赖库
- HTTP模式：仅需`requests`库（通常已安装）
- stdio模式：需要`mcp`库（`pip install mcp`）
- 确保项目中有这些依赖

### 5. 配置管理
- 如果项目使用类方式管理配置，请在Config类中添加MCP配置
- 考虑添加配置验证
- 考虑从环境变量读取配置

## 测试建议

### 1. 单元测试
- 测试MCP管理器连接
- 测试工具列表获取
- 测试工具调用

### 2. 集成测试
- 测试LLM客户端与MCP的集成
- 测试完整的对话流程
- 测试工具调用流程

### 3. 错误测试
- 测试MCP连接失败的情况
- 测试工具调用失败的情况
- 测试MCP未启用的情况

## 预期结果

集成完成后，系统应该能够：

1. ✅ 连接MCP服务器（HTTP或stdio）
2. ✅ 获取可用工具列表
3. ✅ LLM可以自动决定是否使用工具
4. ✅ 执行工具调用
5. ✅ 基于工具结果生成回复
6. ✅ 保持现有的所有功能

## 如果遇到问题

### 问题1: MCP连接失败
- 检查MCP服务器URL是否正确
- 检查网络连接
- 检查MCP服务器是否可用
- 查看错误日志

### 问题2: 工具调用失败
- 检查工具名称是否正确
- 检查工具参数是否正确
- 查看工具调用错误信息
- 检查MCP服务器日志

### 问题3: LLM不使用工具
- 检查工具列表是否正确传递
- 检查LLM是否支持工具调用
- 检查用户请求是否适合使用工具
- 查看LLM的响应

### 问题4: 异步问题
- 确保在异步环境中使用MCP
- 检查方法是否为async
- 检查事件循环是否正确

## 参考文档

- `MCP集成方案.md` - 详细的集成方案
- `MCP集成使用指南.md` - 使用指南和代码示例
- `MCP集成总结.md` - 项目总结

## 下一步

1. 先完成config.py的配置
2. 然后修改llm_client.py
3. 最后修改voice_chat.py
4. 进行测试验证

祝集成顺利！如有问题，请参考文档或检查错误日志。

