#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
本地MCP计算器服务器
提供两个数字相加的工具，用于测试MCP集成
"""

import sys
import os

# 解决导入冲突：确保导入的是安装的 mcp 包，而不是本地的 mcp_tool 目录
# 方法：从 sys.modules 中移除本地 mcp 模块（如果存在），并确保 mcp_tool 目录不在 sys.path 中
current_dir = os.path.dirname(os.path.abspath(__file__))

# 移除 sys.path 中的 mcp_tool 目录（如果存在），避免优先导入本地包
if current_dir in sys.path:
    sys.path.remove(current_dir)

# 如果本地 mcp 模块已被导入，移除它及其子模块
if 'mcp' in sys.modules:
    mcp_module = sys.modules['mcp']
    if hasattr(mcp_module, '__file__') and mcp_module.__file__:
        mcp_file = os.path.abspath(mcp_module.__file__)
        # 如果是本地的 mcp 模块，移除它
        if mcp_file.startswith(current_dir):
            # 移除所有 mcp 相关的模块
            keys_to_remove = [k for k in list(sys.modules.keys()) if k == 'mcp' or k.startswith('mcp.')]
            for key in keys_to_remove:
                del sys.modules[key]

# 现在导入安装的 mcp 包
from mcp.server.fastmcp import FastMCP

# 创建MCP服务器
mcp = FastMCP("本地计算器服务器")


@mcp.tool()
def add(a: int, b: int) -> int:
    """
    计算两个数字的和
    
    Args:
        a: 第一个数字
        b: 第二个数字
    
    Returns:
        两个数字的和
    """
    return a + b


# 如果直接运行此文件，启动服务器
if __name__ == "__main__":
    # 使用stdio传输方式（适合本地测试）
    mcp.run(transport="stdio")

