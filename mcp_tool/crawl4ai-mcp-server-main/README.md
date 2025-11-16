# Crawl4AI MCP Server

基于 MCP (Model Context Protocol) 的智能信息获取服务器，提供网络搜索和网页内容提取功能。

## 核心功能

1. **网络搜索** (`search`): 使用 DuckDuckGo 进行网络搜索
2. **网页内容提取** (`read_url`): 提取网页内容并转换为 LLM 友好的格式

## 文件结构

```
crawl4ai-mcp-server-main/
├── src/
│   ├── index.py      # MCP服务器主实现
│   └── search.py     # DuckDuckGo搜索功能
├── requirements.txt  # 依赖列表
└── pyproject.toml    # 项目配置
```

## 安装依赖

```bash
pip install -r requirements.txt
playwright install
```

## 使用方法

作为 MCP 服务器运行：

```bash
python src/index.py
```

## 工具说明

### search
执行网络搜索并返回结果。

参数：
- `query`: 搜索查询字符串
- `num_results`: 返回结果数量（默认10）

### read_url
提取网页内容。

参数：
- `url`: 要爬取的网页URL
- `format`: 输出格式（默认 `markdown_with_citations`）
  - `markdown_with_citations`: 包含引用的Markdown
  - `fit_markdown`: 优化的精简内容
  - `raw_markdown`: 基础Markdown
  - `references_markdown`: 引用部分
  - `fit_html`: 过滤后的HTML
  - `markdown`: 默认Markdown

