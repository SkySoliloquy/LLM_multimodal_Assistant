# 本地MCP计算器服务器使用说明

## 概述

这是一个简单的本地MCP服务器示例，提供了一个计算两个数字相加的工具，用于测试MCP集成功能。

## 文件说明

- `local_calculator_server.py` - 本地MCP服务器实现
- 使用FastMCP框架创建
- 提供 `add` 工具，可以计算两个整数的和

## 安装依赖

确保已安装MCP Python SDK：

```bash
pip install "mcp[cli]"
```

或者如果使用uv：

```bash
uv add "mcp[cli]"
```

## 配置

服务器已在 `config.py` 中配置：

```python
{
    "name": "local-calculator",
    "type": "stdio",
    "command": "python",
    "args": ["mcp_tool/local_calculator_server.py"]
}
```

## 测试服务器

### 方法1：使用MCP Inspector（推荐）

```bash
# 在项目根目录运行
uv run mcp_tool dev mcp_tool/local_calculator_server.py

# 或者如果使用python
python -m mcp_tool dev mcp_tool/local_calculator_server.py
```

这会打开MCP Inspector，你可以在其中：
- 查看可用工具
- 测试工具调用
- 查看工具结果

### 方法2：直接运行服务器

```bash
# 在项目根目录运行
python mcp_tool/local_calculator_server.py
```

服务器会以stdio模式运行，等待客户端连接。

### 方法3：在SenseVoice系统中使用

1. 确保 `config.py` 中已配置本地服务器（已配置）
2. 启动SenseVoice系统
3. 系统会自动连接本地服务器
4. 在对话中，LLM可以自动使用 `add` 工具

## 使用示例

在SenseVoice系统中，你可以这样测试：

**用户输入：**
```
帮我计算 15 加 27 等于多少
```

**系统流程：**
1. LLM识别到需要计算
2. 调用 `add` 工具，参数：`{"a": 15, "b": 27}`
3. 工具返回结果：`42`
4. LLM基于结果生成回复："15加27等于42"

## 工具说明

### add 工具

- **名称**: `add`
- **描述**: 计算两个数字的和
- **参数**:
  - `a` (int): 第一个数字
  - `b` (int): 第二个数字
- **返回**: 两个数字的和 (int)

## 扩展服务器

你可以参考这个示例添加更多工具：

```python
@mcp.tool()
def subtract(a: int, b: int) -> int:
    """计算两个数字的差"""
    return a - b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """计算两个数字的积"""
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> float:
    """计算两个数字的商"""
    if b == 0:
        raise ValueError("除数不能为零")
    return a / b
```

## 故障排除

### 问题1：找不到mcp模块

**解决方案**：
```bash
pip install "mcp[cli]"
```

### 问题2：服务器连接失败

**检查**：
1. 确保Python路径正确
2. 确保 `mcp_tool/local_calculator_server.py` 文件存在
3. 检查文件权限

### 问题3：工具调用失败

**检查**：
1. 查看系统日志中的MCP错误信息
2. 确保参数类型正确（必须是整数）
3. 检查MCP管理器是否正确连接

## 参考文档

- [MCP Python SDK文档](https://modelcontextprotocol.github.io/python-sdk/)
- [MCP协议规范](https://modelcontextprotocol.io/)

