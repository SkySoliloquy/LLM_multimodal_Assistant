#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import sys
import io
import re
from typing import List, Dict
from mcp.server.fastmcp import FastMCP, Context
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai import CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# Windows 系统上强制使用 UTF-8 编码
# 注意：不要重定向 stdout，因为 MCP 使用 stdio 进行通信
if sys.platform == "win32":
    # 只设置 stderr 为 UTF-8（用于日志输出）
    if sys.stderr.encoding != 'utf-8':
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except AttributeError:
            # 如果 stderr 没有 buffer 属性，跳过
            pass
    # 设置环境变量，确保子进程也使用 UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # 尝试设置标准输出编码（但不重定向，只设置编码）
    # 这不会影响 MCP 的 stdio 通信，但可以确保其他输出使用 UTF-8
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass  # 如果无法重新配置，忽略

# 确保可以导入 search 模块
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from search import SearchManager

mcp = FastMCP("Crawl4AI")

crawler = None
search_manager = None

async def initialize_search_manager():
    global search_manager
    if search_manager is None:
        search_manager = SearchManager()
        # 使用 sys.stderr 输出，避免干扰 stdio 通信
        engine_names = [type(e).__name__ for e in search_manager.engines]
        sys.stderr.write(f"Search manager initialized with engines: {engine_names}\n")
        sys.stderr.flush()

async def initialize_crawler():
    global crawler
    # 确保环境变量设置正确
    if sys.platform == "win32":
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'
    
    browser_config = BrowserConfig(headless=True)
    md_generator = DefaultMarkdownGenerator(
        options={"citations": True}
    )

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header"],
        markdown_generator=md_generator
    )
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()

async def close_crawler():
    global crawler
    if crawler:
        await crawler.__aexit__(None, None, None)

@mcp.tool()
async def read_url(url: str, format: str = "markdown_with_citations") -> str:
    """Crawl a webpage and return its content in a specified format.
    
    Args:
        url: The URL to crawl
        format: The format of the content to return. Options:
            - raw_markdown: The basic HTML→Markdown conversion
            - markdown_with_citations: Markdown including inline citations that reference links at the end
            - references_markdown: The references/citations themselves (if citations=True)
            - fit_markdown: The filtered/"fit" markdown if a content filter was used
            - fit_html: The filtered HTML that generated fit_markdown
            - markdown: The default markdown format
    """
    global crawler
    if not crawler:
        await initialize_crawler()
    
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header"],
        markdown_generator=DefaultMarkdownGenerator(
            options={"citations": True}
        )
    )

    try:
        result = await crawler.arun(url=url, config=run_config)
        
        content = None
        if format == "raw_markdown":
            content = result.markdown_v2.raw_markdown
        elif format == "markdown_with_citations":
            content = result.markdown_v2.markdown_with_citations
        elif format == "references_markdown":
            content = result.markdown_v2.references_markdown
        elif format == "fit_markdown":
            content = result.markdown_v2.fit_markdown
        elif format == "fit_html":
            content = result.markdown_v2.fit_html
        else:
            content = result.markdown_v2.markdown_with_citations
        
        # 确保内容是UTF-8编码的字符串
        if content is not None:
            # 如果内容已经是字符串，确保它是UTF-8编码的
            if isinstance(content, str):
                # 在Windows系统上，处理可能的编码问题
                try:
                    # 先尝试清理字符串中的无效字符
                    # 使用 'replace' 模式替换无法编码的字符
                    content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    # 移除控制字符（除了换行和制表符）
                    import re
                    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
                except Exception as e:
                    # 使用 stderr 输出错误，避免干扰 stdio 通信
                    sys.stderr.write(f"Warning: Error handling content encoding: {str(e)}\n")
                    sys.stderr.flush()
                    content = ""
            else:
                # 如果内容不是字符串，尝试将其转换为字符串
                try:
                    content = str(content)
                    content = content.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    import re
                    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
                except Exception as e:
                    sys.stderr.write(f"Warning: Error converting content to string: {str(e)}\n")
                    sys.stderr.flush()
                    content = f"Error: Could not convert content to string: {str(e)}"
            
            # 限制内容长度，避免 stdio 传输问题（限制为 50000 字符）
            MAX_CONTENT_LENGTH = 50000
            if len(content) > MAX_CONTENT_LENGTH:
                content = content[:MAX_CONTENT_LENGTH] + f"\n\n[内容已截断，原始长度: {len(content)} 字符]"
        
        return content
    except Exception as e:
        error_msg = f"Error crawling URL: {str(e)}"
        sys.stderr.write(f"{error_msg}\n")
        sys.stderr.flush()
        return json.dumps({"error": error_msg}, ensure_ascii=False)

@mcp.tool()
async def search(query: str, num_results: int = 10) -> str:
    """执行网络搜索并返回结果。

    Args:
        query: 搜索查询字符串
        num_results: 返回结果的数量,默认为10
    """
    global search_manager
    try:
        await initialize_search_manager()
        if not search_manager or not search_manager.engines:
            return json.dumps({"error": "No search engines available"}, ensure_ascii=False)
            
        results = await search_manager.search(query, num_results)
        
        # 确保JSON字符串是UTF-8编码的
        try:
            # 清理结果中的特殊字符，确保可以正确序列化
            import re
            cleaned_results = []
            for result in results:
                cleaned_result = {}
                for key, value in result.items():
                    if isinstance(value, str):
                        # 确保字符串是有效的 UTF-8
                        try:
                            # 尝试编码和解码，移除无法编码的字符
                            value = value.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                            # 移除控制字符（除了换行和制表符）
                            value = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', value)
                        except Exception:
                            value = str(value).encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                            value = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', value)
                    cleaned_result[key] = value
                cleaned_results.append(cleaned_result)
            
            json_str = json.dumps(cleaned_results, ensure_ascii=False, indent=2)
            # 再次确保是有效的 UTF-8，并移除控制字符
            json_str = json_str.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            json_str = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
            
            # 限制 JSON 字符串长度（限制为 100000 字符）
            MAX_JSON_LENGTH = 100000
            if len(json_str) > MAX_JSON_LENGTH:
                # 截断结果，保留前面的结果
                truncated = json_str[:MAX_JSON_LENGTH]
                # 尝试找到最后一个完整的结果
                last_complete = truncated.rfind('}')
                if last_complete > 0:
                    truncated = truncated[:last_complete + 1] + '\n]'
                else:
                    truncated = '[]'
                json_str = truncated + f'\n// [内容已截断，原始长度: {len(json_str)} 字符]'
            
            return json_str
        except Exception as e:
            error_msg = f"Error encoding search results: {str(e)}"
            sys.stderr.write(f"{error_msg}\n")
            sys.stderr.flush()
            return json.dumps({"error": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        sys.stderr.write(f"{error_msg}\n")
        sys.stderr.flush()
        try:
            return json.dumps({"error": error_msg}, ensure_ascii=False)
        except Exception as json_e:
            # 如果JSON序列化失败，返回简单的错误消息
            return f"Error: {error_msg}. JSON encoding failed: {str(json_e)}"

async def cleanup():
    await close_crawler()

if __name__ == "__main__":
    # 在启动时确保环境变量设置正确
    if sys.platform == "win32":
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'
    
    try:
        # 使用 stdio 传输（默认）
        mcp.run()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            asyncio.run(cleanup())
        except Exception:
            pass  # 忽略清理时的错误