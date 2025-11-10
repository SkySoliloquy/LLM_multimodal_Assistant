# MCP协议集成到SenseVoice项目方案

## 集成目标

1. 支持HTTP和stdio两种MCP传输方式
2. 遵循项目现有的模块化设计原则
3. 无缝集成到现有的LLM客户端中
4. 支持工具调用和流式响应
5. 配置化管理，易于扩展

## 模块设计

### 1. mcp_client.py - MCP客户端模块
**职责**：管理MCP服务器连接（HTTP/stdio）

**主要类**：
- `MCPClient`: MCP客户端基类/统一接口
- `HTTPMCPSession`: HTTP传输实现
- `StdioMCPSession`: stdio传输实现（包装现有的）

**功能**：
- 连接MCP服务器（HTTP或stdio）
- 初始化会话
- 列出可用工具
- 调用工具
- 管理连接生命周期

### 2. mcp_manager.py - MCP管理器模块
**职责**：管理多个MCP服务器和工具

**主要类**：
- `MCPManager`: MCP管理器，管理多个MCP客户端

**功能**：
- 管理多个MCP服务器连接
- 统一工具列表管理
- 工具调用路由
- 工具格式转换（MCP -> OpenAI格式）

### 3. 修改 llm_client.py
**职责**：在LLM客户端中集成MCP工具调用

**修改内容**：
- 添加MCPManager依赖
- 在chat_completion中支持工具调用
- 处理工具调用结果并继续对话
- 保持现有的流式响应功能

### 4. 修改 config.py
**职责**：添加MCP配置

**添加配置**：
- MCP服务器列表（HTTP和stdio）
- MCP启用/禁用开关
- MCP连接参数

### 5. 修改 voice_chat.py
**职责**：初始化MCP管理器

**修改内容**：
- 在初始化时创建MCPManager
- 将MCPManager传递给LLMClient

## 文件结构

```
SenseVoice/
├── mcp_client.py          # MCP客户端模块（新建）
├── mcp_manager.py         # MCP管理器模块（新建）
├── llm_client.py          # LLM客户端（修改，集成MCP）
├── config.py              # 配置管理（修改，添加MCP配置）
├── voice_chat.py          # 主系统（修改，初始化MCP）
└── ...
```

## 工作流程

1. **初始化阶段**：
   - 从config加载MCP配置
   - 创建MCPManager
   - 连接所有配置的MCP服务器
   - 获取所有可用工具
   - 将MCPManager传递给LLMClient

2. **对话阶段**：
   - 用户输入 -> LLMClient
   - LLMClient检查是否有可用工具
   - 如果有工具，将工具列表发送给LLM
   - LLM决定是否调用工具
   - 如果调用工具，MCPManager执行工具调用
   - 将工具结果返回给LLM
   - LLM生成最终回复

3. **工具调用流程**：
   - LLM返回tool_calls
   - LLMClient解析tool_calls
   - MCPManager调用相应工具
   - 工具结果添加到对话历史
   - LLM继续生成回复

## 配置示例

```python
# config.py
MCP_CONFIG = {
    "enabled": True,
    "servers": [
        {
            "name": "bing-search",
            "type": "http",
            "url": "https://mcp.api-inference.modelscope.net/bd586c64cbff4c/mcp",
            "headers": {}
        },
        {
            "name": "local-tools",
            "type": "stdio",
            "command": "python",
            "args": ["local_mcp_server.py"]
        }
    ]
}
```

## 优势

1. **模块化**：MCP功能独立成模块，不影响现有代码
2. **可扩展**：支持多个MCP服务器
3. **灵活**：支持HTTP和stdio两种传输方式
4. **配置化**：通过配置文件管理，易于部署
5. **向后兼容**：MCP功能可选，不影响现有功能

## 实现步骤

1. 创建mcp_client.py - MCP客户端模块
2. 创建mcp_manager.py - MCP管理器模块
3. 修改config.py - 添加MCP配置
4. 修改llm_client.py - 集成MCP工具调用
5. 修改voice_chat.py - 初始化MCP管理器
6. 测试验证

