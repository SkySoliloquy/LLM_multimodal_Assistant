from typing import List, Dict
import logging
import asyncio
import sys
import os
from abc import ABC, abstractmethod

# Windows 系统上强制使用 UTF-8 编码
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 尝试导入新包名，如果失败则使用旧包名
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        raise ImportError("请安装 ddgs 包: pip install ddgs")

# 配置日志，确保使用 UTF-8 编码
logger = logging.getLogger(__name__)
# 如果还没有配置 handler，添加一个
if not logger.handlers:
    # 创建一个安全的 handler，确保所有输出都是 UTF-8
    class SafeUTF8Handler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                # 确保消息是 UTF-8 编码
                if isinstance(msg, str):
                    msg = msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                stream = self.stream
                stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                # 忽略所有日志错误，避免干扰 stdio
                pass
    
    handler = SafeUTF8Handler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)  # 降低日志级别，减少输出

class SearchResult:
    def __init__(self, title: str, link: str, snippet: str, source: str):
        self.title = title
        self.link = link
        self.snippet = snippet
        self.source = source

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "link": self.link,
            "snippet": self.snippet,
            "source": self.source
        }

class SearchEngine(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        pass

class DuckDuckGoSearch(SearchEngine):
    def __init__(self):
        # 不在初始化时创建DDGS实例，每次搜索时创建新实例以避免状态问题
        pass
        
    def _search_sync(self, query: str, num_results: int) -> List[Dict]:
        """同步搜索方法，在后台线程中运行"""
        try:
            # 每次搜索创建新的DDGS实例
            ddgs = DDGS()
            
            # 使用ddgs库进行搜索
            # 注意：对于中文查询，DuckDuckGo可能返回不相关的结果
            # 优先尝试us-en区域（通常对中文查询也能返回相关结果）
            raw_results = None
            regions_to_try = ["us-en", "wt-wt", "cn-zh"]
            
            for region in regions_to_try:
                try:
                    # 尝试使用 keywords 参数（新版本可能支持）
                    try:
                        raw_results = list(ddgs.text(
                            keywords=query,
                            region=region,
                            safesearch="moderate",
                            max_results=num_results
                        ))
                    except TypeError:
                        # 如果 keywords 参数不支持，尝试位置参数
                        raw_results = list(ddgs.text(
                            query,
                            region=region,
                            safesearch="moderate",
                            max_results=num_results
                        ))
                    
                    # 验证结果相关性（简单检查：至少有一个结果包含查询中的关键词）
                    if raw_results:
                        # 检查结果是否相关（至少检查前几个结果）
                        relevant_count = 0
                        query_keywords = set(query.lower().split())
                        
                        for result in raw_results[:3]:  # 只检查前3个结果
                            title = result.get('title', '').lower()
                            body = result.get('body', '').lower()
                            combined = title + ' ' + body
                            
                            # 如果结果中包含查询中的任何关键词，认为可能相关
                            if any(keyword in combined for keyword in query_keywords if len(keyword) > 1):
                                relevant_count += 1
                        
                        # 如果至少有一个结果看起来相关，或者所有区域都试过了，使用这些结果
                        if relevant_count > 0 or region == regions_to_try[-1]:
                            logger.info(f"DuckDuckGo search successful with region {region} for query: {query}, relevant results: {relevant_count}/{min(3, len(raw_results))}")
                            break
                        else:
                            logger.debug(f"Region {region} returned {len(raw_results)} results but none seem relevant, trying next region")
                            raw_results = None
                            continue
                            
                except Exception as e:
                    logger.debug(f"Region {region} failed: {str(e)}, trying next region")
                    continue
            
            if not raw_results:
                logger.warning(f"No results from DuckDuckGo for query: {query}")
                return []
            
            # 转换结果，尝试多种可能的字段名
            results = []
            for item in raw_results:
                # duckduckgo_search库不同版本可能使用不同的字段名
                # 尝试多种可能的字段名组合
                title = item.get('title') or item.get('Title') or ''
                # 链接字段可能是 'href', 'link', 'url' 等
                link = (item.get('href') or item.get('link') or 
                       item.get('url') or item.get('Link') or '')
                # 摘要字段可能是 'body', 'snippet', 'description' 等
                snippet = (item.get('body') or item.get('snippet') or 
                          item.get('description') or item.get('Body') or '')
                
                # 如果所有字段都为空，跳过这个结果
                if not title and not link:
                    logger.debug(f"Skipping empty result: {item}")
                    continue
                
                results.append({
                    'title': title,
                    'link': link,
                    'snippet': snippet,
                    'source': 'duckduckgo'
                })
            
            logger.info(f"Converted {len(results)} results from DuckDuckGo")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}", exc_info=True)
            return []
        
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """异步搜索方法"""
        try:
            # 在后台线程中运行同步搜索
            raw_results = await asyncio.to_thread(self._search_sync, query, num_results)
            
            # 转换为SearchResult对象
            results = []
            for item in raw_results:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    link=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    source=item.get('source', 'duckduckgo')
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo async search failed: {str(e)}", exc_info=True)
            return []

class SearchManager:
    def __init__(self):
        self.engines: List[SearchEngine] = []
        self._initialize_engines()
        
    def _initialize_engines(self):
        # 添加DuckDuckGo搜索
        self.engines.append(DuckDuckGoSearch())
                
    async def search(self, query: str, num_results: int = 10) -> List[Dict]:
        all_results = []
        
        if not self.engines:
            logger.warning("No search engines available")
            return []

        logger.info(f"Starting search with query: {query}, num_results: {num_results}")
        
        for search_engine in self.engines:
            engine_name = search_engine.__class__.__name__.lower()
                
            try:
                results = await search_engine.search(query, num_results)
                logger.info(f"Got {len(results)} results from {engine_name}")
                
                # 检查结果类型
                if results:
                    logger.debug(f"First result type: {type(results[0])}")
                    
                # 转换结果并清理编码问题
                converted_results = []
                for r in results:
                    try:
                        result_dict = r.to_dict()
                        # 确保所有字符串字段都是有效的 UTF-8
                        for key, value in result_dict.items():
                            if isinstance(value, str):
                                # 清理无法编码的字符
                                result_dict[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                        converted_results.append(result_dict)
                    except Exception as e:
                        logger.warning(f"Failed to convert result: {str(e)}")
                        continue
                
                logger.debug(f"Converted {len(converted_results)} results from {engine_name}")
                all_results.extend(converted_results)
            except Exception as e:
                logger.error(f"Search failed for {engine_name}: {str(e)}", exc_info=True)
                
        final_results = all_results[:num_results]
        logger.info(f"Returning {len(final_results)} total results")
        return final_results