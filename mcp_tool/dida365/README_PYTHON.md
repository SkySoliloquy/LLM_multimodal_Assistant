# 滴答清单 MCP 服务 - Python 版本

这是滴答清单（TickTick/Dida365）的 Model Context Protocol (MCP) 服务器 Python 实现版本，使用纯 Python 编写。该服务允许 AI 助手通过标准化接口与滴答清单 API 进行交互。

## 功能特性

- ✅ 创建、读取、更新、删除任务
- ✅ 管理项目和项目列表
- ✅ 支持任务优先级和截止日期
- ✅ 通过环境变量安全配置 API Token
- ✅ 完整的错误处理和API响应验证
- ✅ 使用标准输入输出进行 JSON-RPC 通信

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Access Token

在 MCP 客户端配置中，通过环境变量传入 `DIDA365_TOKEN`：

```json
{
  "dida365": {
    "command": "python",
    "args": ["path/to/server.py"],
    "env": {
      "DIDA365_TOKEN": "Bearer your_access_token_here"
    }
  }
}
```

**获取 Access Token：**
1. 访问 [滴答清单开放平台](https://developer.dida365.com/)
2. 登录并创建应用
3. 使用 OAuth2 流程获取 Access Token
4. 格式：`Bearer <your_access_token>`

### 3. 运行服务器

服务器通过标准输入输出与 MCP 客户端通信，无需手动启动。

## MCP 客户端配置示例

### 配置文件位置
- macOS/Linux: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Windows: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

### 配置示例

```json
{
  "mcpServers": {
    "dida365": {
      "command": "python",
      "args": [
        "C:\\Users\\Administrator\\node_modules\\dida365-mcp-servers\\server.py"
      ],
      "env": {
        "DIDA365_TOKEN": "Bearer your_access_token_here"
      }
    }
  }
}
```

**注意：**
- 修改 `args` 中的路径为你的实际路径
- 确保 `DIDA365_TOKEN` 包含正确的 Bearer Token
- Token 可以通过 OAuth2 流程获取

## 可用工具

### 任务管理

#### `create_task` - 创建新任务
- **参数**:
  - `title` (string, 必需): 任务标题
  - `projectId` (string, 必需): 项目ID
  - `content` (string): 任务内容描述
  - `dueDate` (string): 截止日期 (ISO 8601格式)
  - `priority` (number): 优先级 (0-5)

#### `get_task_by_projectId_and_taskId` - 通过项目ID和任务ID获取任务
- **参数**:
  - `projectId` (string, 必需): 项目ID
  - `taskId` (string, 必需): 任务ID

#### `get_tasks_by_projectId` - 通过项目ID获取项目中的任务列表
- **参数**:
  - `projectId` (string, 必需): 项目ID

#### `update_task` - 更新任务
- **参数**:
  - `taskId` (string, 必需): 任务ID
  - `title` (string): 任务标题
  - `content` (string): 任务内容
  - `dueDate` (string): 截止日期
  - `priority` (number): 优先级
  - `status` (number): 任务状态 (0: 未完成, 1: 已完成)

#### `delete_task` - 删除任务
- **参数**:
  - `taskId` (string, 必需): 任务ID
  - `projectId` (string, 必需): 项目ID

#### `complete_task` - 完成任务
- **参数**:
  - `taskId` (string, 必需): 任务ID
  - `projectId` (string, 必需): 项目ID

### 项目管理

#### `get_projects` - 获取项目列表
- **参数**: 无

#### `get_project_by_projectId` - 根据项目ID获取项目
- **参数**:
  - `projectId` (string, 必需): 项目ID

#### `create_project` - 创建新项目
- **参数**:
  - `name` (string, 必需): 项目名称
  - `color` (string): 项目颜色, 例如 "#F18181"
  - `sortOrder` (integer): 排序值, 默认为0
  - `viewMode` (string): 视图模式 ("list", "kanban", "timeline")
  - `kind` (string): 项目类型 ("TASK", "NOTE")

#### `update_project_by_projectID` - 根据projectId更新项目
- **参数**:
  - `projectId` (string, 必需): 项目ID
  - `name` (string): 项目名称
  - `color` (string): 项目颜色
  - `sortOrder` (integer): 排序值, 默认为0
  - `viewMode` (string): 视图模式 ("list", "kanban", "timeline")
  - `kind` (string): 项目类型 ("TASK", "NOTE")

#### `delete_project_by_projectID` - 根据projectId删除项目
- **参数**:
  - `projectId` (string, 必需): 项目ID

## 可用资源

### `dida365://tasks`

获取所有任务的JSON格式概览

### `dida365://projects`

获取所有项目的JSON格式概览

## 项目结构

```
├── server.py              # Python MCP 服务器主文件
├── requirements.txt       # Python 依赖包
└── README_PYTHON.md       # 使用文档
```

## API 接口说明

本服务使用滴答清单官方 API：

- 基础URL: `https://api.dida365.com/open/v1`
- 认证方式: Bearer Token
- 请求格式: JSON
- 官方文档: https://developer.dida365.com/api#/openapi

## 错误处理

服务包含完整的错误处理机制：

- API 调用失败时返回详细错误信息
- 网络错误和超时处理
- 参数验证和类型检查
- Token 验证

## 技术实现

- 使用 `httpx` 进行 HTTP 请求
- 使用 `python-dotenv` 加载环境变量
- 通过标准输入输出实现 JSON-RPC 协议通信
- 支持同步操作，简单高效

## 开发说明

如果需要修改代码，直接编辑 `server.py` 文件即可，无需编译步骤。

## 与 TypeScript 版本的对比

- Python 版本更简洁，无需编译
- 直接运行，启动更快
- 使用标准库实现 MCP 协议，无额外依赖
- 功能完全一致，API 兼容

## 贡献

欢迎提交 Issue 和 Pull Request！
