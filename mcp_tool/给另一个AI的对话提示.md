# 给另一个AI助手的对话提示

## 开场白

你好！我正在将MCP（Model Context Protocol）协议集成到SenseVoice语音对话系统项目中。我已经完成了MCP核心模块的创建和文件复制，现在需要你的帮助来完成集成工作。

## 项目情况

### 已完成的工作
1. ✅ 创建了 `mcp_client.py` - MCP客户端模块（支持HTTP和stdio）
2. ✅ 创建了 `mcp_manager.py` - MCP管理器模块
3. ✅ 复制了相关文件到SenseVoice项目目录
4. ✅ 创建了配置示例和文档

### 需要完成的工作
1. ⏳ 在 `config.py` 中添加MCP配置
2. ⏳ 修改 `llm_client.py` 支持MCP工具调用
3. ⏳ 修改 `voice_chat.py` 初始化MCP管理器

## 关键信息

### 项目结构
- SenseVoice是一个模块化的语音对话系统
- 主要模块：`voice_chat.py`（主系统）、`llm_client.py`（LLM客户端）、`config.py`（配置管理）
- 项目使用异步编程（asyncio）

### MCP模块
- `mcp_client.py`: MCP客户端，负责连接MCP服务器
- `mcp_manager.py`: MCP管理器，管理多个MCP服务器和工具
- 支持HTTP和stdio两种传输方式

### 集成目标
- 让LLM能够使用MCP工具
- 保持现有功能不变
- 支持工具调用和流式响应

## 你可以这样开始

1. **首先了解项目结构**：
   ```
   请帮我查看SenseVoice项目的结构，特别是：
   - config.py 的配置管理方式（类方式还是模块方式）
   - llm_client.py 的 LLMClient 类结构
   - voice_chat.py 的 VoiceChatSystem 类结构
   ```

2. **然后查看MCP模块**：
   ```
   请帮我查看以下文件，了解MCP模块的使用方式：
   - mcp_client.py
   - mcp_manager.py
   - mcp_config_example.py
   ```

3. **开始集成**：
   ```
   根据"给AI助手的MCP集成指令.md"文档，帮我完成MCP集成：
   1. 在config.py中添加MCP配置
   2. 修改llm_client.py支持工具调用
   3. 修改voice_chat.py初始化MCP管理器
   ```

## 参考文档

项目中已有以下文档，请参考：
1. **给AI助手的MCP集成指令.md** - 详细的集成指令和代码示例
2. **快速集成检查清单.md** - 集成步骤检查清单
3. **MCP集成方案.md** - 集成方案设计
4. **MCP集成使用指南.md** - 使用指南
5. **MCP集成总结.md** - 项目总结

## 注意事项

1. **保持向后兼容**：MCP功能应该是可选的，不影响现有功能
2. **错误处理**：需要处理MCP连接失败、工具调用失败等情况
3. **异步处理**：MCP管理器需要在异步环境中使用
4. **测试验证**：完成集成后需要进行测试

## 如果遇到问题

- 查看错误日志
- 检查配置文件
- 检查异步调用
- 参考文档中的常见问题部分

## 预期结果

集成完成后，系统应该能够：
- 连接MCP服务器
- 获取工具列表
- LLM自动决定是否使用工具
- 执行工具调用
- 基于工具结果生成回复

---

**请从查看项目结构开始，然后按照集成指令完成集成工作。谢谢！**

