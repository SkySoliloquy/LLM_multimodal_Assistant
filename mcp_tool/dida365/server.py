#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滴答清单 MCP 服务器 - Python 版本
Model Context Protocol server for Dida365 (TickTick) API
"""

import os
import sys
import io
import json
from typing import Any, Dict, List, Optional
import dotenv
import httpx

# Windows 系统上强制使用 UTF-8 编码
if sys.platform == "win32":
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    # 只设置 stderr 为 UTF-8（用于日志输出）
    if sys.stderr.encoding != 'utf-8':
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except AttributeError:
            pass
    # 尝试设置标准输出编码（但不重定向，只设置编码）
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# 加载环境变量
dotenv.load_dotenv()

# 滴答清单API基础配置
DIDA365_BASE_URL = "https://api.dida365.com/open/v1"
DIDA365_TOKEN = os.getenv("DIDA365_TOKEN")

if not DIDA365_TOKEN:
    print("Error: DIDA365_TOKEN not found in environment variables", file=sys.stderr)
    sys.exit(1)

# 创建HTTP客户端
dida365_client = httpx.Client(
    base_url=DIDA365_BASE_URL,
    headers={
        "Content-Type": "application/json",
        "Authorization": DIDA365_TOKEN,
    },
    timeout=30.0,
)


def throw_valid_error(project_id: Optional[str] = None, task_id: Optional[str] = None) -> None:
    """验证参数并抛出错误"""
    if not project_id and not task_id:
        raise ValueError("projectId 和 taskId 为空")
    if not project_id:
        raise ValueError("projectId 为空")
    if not task_id:
        raise ValueError("taskId 为空")


def list_tools() -> List[Dict[str, Any]]:
    """列出所有可用工具"""
    return [
        {
            "name": "create_task",
            "description": "Create a new task in Dida365 with specified details including title, project ID, content, due date and priority. The task will be created under the specified project. Requires at least title and projectId. Returns the created task details.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title/name of the task (required)",
                    },
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project where this task belongs (required)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Detailed description/content of the task",
                    },
                    "dueDate": {
                        "type": "string",
                        "description": 'Due date and time in "yyyy-MM-dd\'T\'HH:mm:ssZ" format\nExample : "2019-11-13T03:00:00+0000"',
                    },
                    "priority": {
                        "type": "number",
                        "description": "Task priority\nValue : None:0, Low:1, Medium:3, High5",
                    },
                },
                "required": ["title", "projectId"],
            },
        },
        {
            "name": "get_task_by_projectId_and_taskId",
            "description": "Retrieve a specific task's details by providing both the project ID and task ID. Returns complete task information including title, content, status, due date, priority, and subtasks if any.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project containing the task (required)",
                    },
                    "taskId": {
                        "type": "string",
                        "description": "The ID of the task to retrieve (required)",
                    },
                },
                "required": ["projectId", "taskId"],
            },
        },
        {
            "name": "get_tasks_by_projectId",
            "description": "Get all tasks belonging to a specific project by project ID. Returns a list of tasks with their basic information. Useful for viewing all tasks in a project.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project whose tasks you want to list (required)",
                    },
                },
                "required": ["projectId"],
            },
        },
        {
            "name": "update_task",
            "description": "Modify an existing task's properties. Can update title, content, due date, priority or status. At least taskId is required. Returns the updated task details.Note: Before calling this method, you may need to first call the get_projects method to retrieve all project IDs. Then, based on the projectId, repeatedly call the get_tasks_by_projectId method to locate the specific task you want to modify.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "taskId": {
                        "type": "string",
                        "description": "The ID of the task to update (required)",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the task",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content/description for the task",
                    },
                    "dueDate": {
                        "type": "string",
                        "description": 'Due date and time in "yyyy-MM-dd\'T\'HH:mm:ssZ" format\nExample : "2019-11-13T03:00:00+0000"',
                    },
                    "priority": {
                        "type": "number",
                        "description": "Task priority\nValue : None:0, Low:1, Medium:3, High5",
                    },
                    "status": {
                        "type": "number",
                        "description": "Task completion status (0: incomplete, 1: complete)",
                    },
                },
                "required": ["taskId"],
            },
        },
        {
            "name": "delete_task",
            "description": "Permanently delete a task from a project. Requires both task ID and project ID for confirmation. Returns success message upon deletion.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "taskId": {
                        "type": "string",
                        "description": "The ID of the task to delete (required)",
                    },
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project containing the task (required)",
                    },
                },
                "required": ["taskId", "projectId"],
            },
        },
        {
            "name": "complete_task",
            "description": "Mark a task as completed. Requires both task ID and project ID. Updates the task's status to completed and sets completion timestamp.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "taskId": {
                        "type": "string",
                        "description": "The ID of the task to mark as complete (required)",
                    },
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project containing the task (required)",
                    },
                },
                "required": ["taskId", "projectId"],
            },
        },
        {
            "name": "get_projects",
            "description": "Retrieve a list of all projects in the Dida365 account. Returns project details including ID, name, color, view mode and sort order. No parameters required.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "get_project_by_projectId",
            "description": "Get detailed information about a specific project by its ID. Returns project metadata including name, color, view mode, kind and sort order.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project to retrieve (required)",
                    },
                },
                "required": ["projectId"],
            },
        },
        {
            "name": "create_project",
            "description": "Create a new project in Dida365. Requires at least a project name. Can specify color, view mode, kind and sort order. Returns the created project details.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the new project (required)",
                    },
                    "color": {
                        "type": "string",
                        "description": 'Hex color code for the project (e.g., "#F18181")',
                    },
                    "sortOrder": {
                        "type": "integer",
                        "description": "Numerical sort order value (default 0)",
                    },
                    "viewMode": {
                        "type": "string",
                        "description": 'View mode: "list", "kanban", or "timeline"',
                    },
                    "kind": {
                        "type": "string",
                        "description": 'Project type: "TASK" or "NOTE"',
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "update_project_by_projectID",
            "description": "Update an existing project's properties. Requires project ID. Can modify name, color, view mode, kind and sort order. Returns updated project details.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project to update (required)",
                    },
                    "name": {
                        "type": "string",
                        "description": "New name for the project",
                    },
                    "color": {
                        "type": "string",
                        "description": "New hex color code for the project",
                    },
                    "sortOrder": {
                        "type": "integer",
                        "description": "Updated sort order value",
                    },
                    "viewMode": {
                        "type": "string",
                        "description": 'Updated view mode: "list", "kanban", or "timeline"',
                    },
                    "kind": {
                        "type": "string",
                        "description": 'Updated project kind: "TASK" or "NOTE"',
                    },
                },
                "required": ["projectId"],
            },
        },
        {
            "name": "delete_project_by_projectID",
            "description": "Permanently delete a project by its ID. This will also delete all tasks within the project. Returns success message upon deletion.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "projectId": {
                        "type": "string",
                        "description": "The ID of the project to delete (required)",
                    },
                },
                "required": ["projectId"],
            },
        },
    ]


def call_tool(name: str, arguments: Dict[str, Any]) -> List[Dict[str, str]]:
    """处理工具调用"""
    # arguments 可以为空（某些工具不需要参数，如 get_projects）
    if arguments is None:
        arguments = {}
    
    try:
        if name == "create_task":
            task = {
                "title": arguments["title"],
                "projectId": arguments["projectId"],
            }
            if "content" in arguments:
                task["content"] = arguments["content"]
            if "dueDate" in arguments:
                task["dueDate"] = arguments["dueDate"]
            if "priority" in arguments:
                task["priority"] = arguments["priority"]

            response = dida365_client.post("/task", json=task)
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"任务创建成功: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "get_task_by_projectId_and_taskId":
            project_id = arguments.get("projectId")
            task_id = arguments.get("taskId")
            if not project_id or not task_id:
                raise ValueError("项目ID或任务ID为空")

            response = dida365_client.get(f"/project/{project_id}/task/{task_id}")
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"任务: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "get_tasks_by_projectId":
            project_id = arguments.get("projectId")
            if not project_id:
                raise ValueError("项目ID为空")

            response = dida365_client.get(f"/project/{project_id}/data")
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"任务列表: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "update_task":
            task_id = arguments["taskId"]
            update_data = {}
            if "title" in arguments:
                update_data["title"] = arguments["title"]
            if "content" in arguments:
                update_data["content"] = arguments["content"]
            if "dueDate" in arguments:
                update_data["dueDate"] = arguments["dueDate"]
            if "priority" in arguments:
                update_data["priority"] = arguments["priority"]
            if "status" in arguments:
                update_data["status"] = arguments["status"]

            response = dida365_client.put(f"/task/{task_id}", json=update_data)
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"任务更新成功: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "delete_task":
            task_id = arguments["taskId"]
            project_id = arguments["projectId"]
            throw_valid_error(project_id, task_id)

            response = dida365_client.delete(f"/project/{project_id}/task/{task_id}")
            response.raise_for_status()
            
            # 检查响应内容
            try:
                response_text = response.text.strip()
                if response_text:
                    # 尝试解析 JSON
                    try:
                        response_data = response.json()
                        return [
                            {
                                "type": "text",
                                "text": f"任务删除成功: {json.dumps(response_data, indent=2, ensure_ascii=False)}",
                            }
                        ]
                    except json.JSONDecodeError:
                        # 如果不是 JSON，返回原始文本
                        return [
                            {
                                "type": "text",
                                "text": f"任务删除成功（响应: {response_text[:200]}）",
                            }
                        ]
                else:
                    # 响应为空，说明操作成功但没有返回数据
                    return [
                        {
                            "type": "text",
                            "text": f"任务 {task_id} 已成功删除",
                        }
                    ]
            except Exception as e:
                # 如果处理响应时出错，至少返回成功消息
                return [
                    {
                        "type": "text",
                        "text": f"任务删除成功（状态码: {response.status_code}）",
                    }
                ]

        elif name == "complete_task":
            task_id = arguments["taskId"]
            project_id = arguments["projectId"]
            throw_valid_error(project_id, task_id)

            response = dida365_client.post(f"/project/{project_id}/task/{task_id}/complete")
            response.raise_for_status()
            
            # 检查响应内容
            try:
                response_text = response.text.strip()
                if response_text:
                    # 尝试解析 JSON
                    try:
                        response_data = response.json()
                        return [
                            {
                                "type": "text",
                                "text": f"任务标记为已完成: {json.dumps(response_data, indent=2, ensure_ascii=False)}",
                            }
                        ]
                    except json.JSONDecodeError:
                        # 如果不是 JSON，返回原始文本
                        return [
                            {
                                "type": "text",
                                "text": f"任务标记为已完成（响应: {response_text[:200]}）",
                            }
                        ]
                else:
                    # 响应为空，说明操作成功但没有返回数据
                    return [
                        {
                            "type": "text",
                            "text": f"任务 {task_id} 已成功标记为已完成",
                        }
                    ]
            except Exception as e:
                # 如果处理响应时出错，至少返回成功消息
                return [
                    {
                        "type": "text",
                        "text": f"任务标记为已完成（状态码: {response.status_code}）",
                    }
                ]

        elif name == "get_projects":
            response = dida365_client.get("/project")
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"项目列表: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "get_project_by_projectId":
            project_id = arguments["projectId"]
            if not project_id:
                raise ValueError("项目ID为空")

            response = dida365_client.get(f"/project/{project_id}")
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"获取project成功: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "create_project":
            project = {"name": arguments["name"]}
            if "color" in arguments:
                project["color"] = arguments["color"]
            if "sortOrder" in arguments:
                project["sortOrder"] = arguments["sortOrder"]
            if "viewMode" in arguments:
                project["viewMode"] = arguments["viewMode"]
            if "kind" in arguments:
                project["kind"] = arguments["kind"]

            response = dida365_client.post("/project", json=project)
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"项目创建成功: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "update_project_by_projectID":
            project_id = arguments["projectId"]
            if not project_id:
                raise ValueError("项目ID为空")

            project = {"id": project_id}
            if "name" in arguments:
                project["name"] = arguments["name"]
            if "color" in arguments:
                project["color"] = arguments["color"]
            if "sortOrder" in arguments:
                project["sortOrder"] = arguments["sortOrder"]
            if "viewMode" in arguments:
                project["viewMode"] = arguments["viewMode"]
            if "kind" in arguments:
                project["kind"] = arguments["kind"]

            response = dida365_client.post("/project", json=project)
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"项目更新成功: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        elif name == "delete_project_by_projectID":
            project_id = arguments["projectId"]
            if not project_id:
                raise ValueError("项目ID为空")

            response = dida365_client.delete(f"/project/{project_id}")
            response.raise_for_status()
            return [
                {
                    "type": "text",
                    "text": f"删除项目成功: {json.dumps(response.json(), indent=2, ensure_ascii=False)}",
                }
            ]

        else:
            raise ValueError(f"未知工具: {name}")

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        try:
            response_text = e.response.text.strip()
            if response_text:
                try:
                    error_data = e.response.json()
                    message = error_data.get("message", str(e))
                except json.JSONDecodeError:
                    message = response_text[:200] if len(response_text) > 200 else response_text
            else:
                message = f"HTTP {status} 错误"
        except Exception:
            message = str(e)
        raise Exception(f"滴答清单API调用失败 ({status}): {message}")
    except Exception as e:
        raise Exception(f"工具执行失败: {str(e)}")


def list_resources() -> List[Dict[str, str]]:
    """列出所有可用资源"""
    return [
        {
            "uri": "dida365://tasks",
            "name": "滴答清单任务",
            "description": "获取所有任务的概览",
            "mimeType": "application/json",
        },
        {
            "uri": "dida365://projects",
            "name": "滴答清单项目",
            "description": "获取所有项目的概览",
            "mimeType": "application/json",
        },
    ]


def read_resource(uri: str) -> str:
    """读取资源内容"""
    try:
        if uri == "dida365://tasks":
            response = dida365_client.get("/task")
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, ensure_ascii=False)

        elif uri == "dida365://projects":
            response = dida365_client.get("/project")
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, ensure_ascii=False)

        else:
            raise ValueError(f"未知资源URI: {uri}")

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        try:
            response_text = e.response.text.strip()
            if response_text:
                try:
                    error_data = e.response.json()
                    message = error_data.get("message", str(e))
                except json.JSONDecodeError:
                    message = response_text[:200] if len(response_text) > 200 else response_text
            else:
                message = f"HTTP {status} 错误"
        except Exception:
            message = str(e)
        raise Exception(f"滴答清单API调用失败 ({status}): {message}")
    except Exception as e:
        raise Exception(f"资源获取失败: {str(e)}")


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """处理 MCP 请求"""
    method = request.get("method")
    params = request.get("params", {})
    
    if method == "initialize":
        # MCP 协议要求的初始化方法
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {}
            },
            "serverInfo": {
                "name": "dida365-mcp-server",
                "version": "1.0.0"
            }
        }
    
    elif method == "tools/list":
        return {"tools": list_tools()}
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        results = call_tool(tool_name, arguments)
        return {"content": results}
    
    elif method == "resources/list":
        return {"resources": list_resources()}
    
    elif method == "resources/read":
        uri = params.get("uri")
        content = read_resource(uri)
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": content,
                }
            ]
        }
    
    elif method == "notifications/initialized":
        # 客户端发送的初始化通知，不需要响应
        return {}
    
    else:
        raise ValueError(f"未知方法: {method}")


def main():
    """主函数 - 使用标准输入输出与 MCP 客户端通信"""
    print("滴答清单 MCP 服务已启动", file=sys.stderr)
    sys.stderr.flush()
    
    # 读取标准输入，处理 JSON-RPC 请求
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line.strip())
            request_id = request.get("id")
            method = request.get("method")
            
            # 处理请求
            try:
                response = handle_request(request)
                
                # 如果是通知（没有 id），不需要发送响应
                if request_id is None and method and method.startswith("notifications/"):
                    continue
                
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": response,
                }
            except ValueError as e:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": str(e),
                    },
                }
            except Exception as e:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"内部错误: {str(e)}",
                    },
                }
            
            # 发送响应（确保 UTF-8 编码）
            try:
                json_str = json.dumps(response_data, ensure_ascii=False)
                # 确保是有效的 UTF-8
                json_str = json_str.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                print(json_str, flush=True)
            except Exception as e:
                # 如果编码失败，发送错误响应
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"编码错误: {str(e)}",
                    },
                }
                print(json.dumps(error_response, ensure_ascii=False), flush=True)
            
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"解析错误: {str(e)}",
                },
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()