# MCP模块
"""MCP (Model Context Protocol) 集成模块"""

# 使用延迟导入，避免循环导入问题
def __getattr__(name):
    if name == 'MCPClient':
        from .mcp_client import MCPClient
        return MCPClient
    elif name == 'MCPManager':
        from .mcp_manager import MCPManager
        return MCPManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['MCPClient', 'MCPManager']

