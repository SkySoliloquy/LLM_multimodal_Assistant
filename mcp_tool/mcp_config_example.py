# mcp_config_example.py
# MCP配置示例 - 展示如何在config.py中添加MCP配置

"""
MCP配置示例
在您的config.py中添加类似以下配置：
"""

# MCP服务器配置
MCP_CONFIG = {
    # 是否启用MCP功能
    "enabled": True,
    
    # MCP服务器列表
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

"""
配置说明：

1. enabled: 是否启用MCP功能
   - True: 启用MCP，LLM可以使用工具
   - False: 禁用MCP，LLM正常工作但不使用工具

2. servers: MCP服务器配置列表
   每个服务器配置包含：
   - name: 服务器名称（唯一标识）
   - type: 传输类型 ("http" 或 "stdio")
   
   HTTP服务器配置：
   - url: MCP服务器URL
   - headers: 可选，HTTP请求头（如认证信息）
   
   stdio服务器配置：
   - command: 启动命令（如 "python"）
   - args: 命令参数列表（如 ["server.py"]）

使用示例：

在config.py中：
```python
# 导入MCP配置
from mcp_config_example import MCP_CONFIG

# 或者在config.py中直接定义
MCP_CONFIG = {
    "enabled": True,
    "servers": [
        {
            "name": "bing-search",
            "type": "http",
            "url": "https://mcp.api-inference.modelscope.net/bd586c64cbff4c/mcp",
            "headers": {}
        }
    ]
}
```
"""

