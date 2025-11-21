#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Flask Web应用 - 语音对话系统前端接入
支持WebSocket实时通信和RESTful API
"""
import sys
import os
import uuid
import time
import base64
import io
import tempfile
from pathlib import Path
from typing import Dict, Optional
import numpy as np
from scipy.io import wavfile

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 切换到项目根目录，确保相对路径能正确找到文件
os.chdir(project_root)

from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from flask_socketio import SocketIO, emit, disconnect
import eventlet
import json

# 导入项目模块
from voice_chat import VoiceChatSystem
from config import Config

BASE_DIR = Path(__file__).resolve().parent

# 创建Flask应用
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 创建SocketIO实例
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 会话管理: session_id -> VoiceChatSystem实例
sessions: Dict[str, VoiceChatSystem] = {}

# 全局系统实例（用于单会话模式或默认会话）
default_session_id = "default"
global_system: Optional[VoiceChatSystem] = None

# 加载状态
loading_status = {
    "is_loading": False,
    "progress": 0,
    "current_step": "",
    "steps": [
        "验证配置",
        "加载ASR模型",
        "初始化LLM客户端",
        "初始化记忆系统",
        "初始化TTS客户端",
        "初始化MCP管理器",
        "完成"
    ]
}


def emit_loading_progress(step_name: str, progress: float, room=None):
    """发送加载进度事件"""
    global loading_status
    loading_status["current_step"] = step_name
    loading_status["progress"] = progress
    
    try:
        payload = {
            'step': step_name,
            'progress': progress,
            'is_complete': progress >= 100
        }
        if room:
            socketio.emit('loading_progress', payload, room=room)
        else:
            socketio.emit('loading_progress', payload)
        print(f"[进度] {step_name}: {progress}% (房间: {room})")
    except Exception as e:
        print(f"[进度] 发送失败: {e}")


def get_or_create_session(session_id: Optional[str] = None, emit_to_room=None) -> tuple[str, VoiceChatSystem]:
    """
    获取或创建会话（支持加载进度通知）
    
    Args:
        session_id: 会话ID，如果为None则使用默认会话
        emit_to_room: WebSocket房间ID，用于发送加载进度
        
    Returns:
        (session_id, VoiceChatSystem实例)
    """
    global loading_status
    
    if session_id is None:
        session_id = default_session_id
    
    if session_id not in sessions:
        try:
            # 开始加载
            loading_status["is_loading"] = True
            loading_status["progress"] = 0
            
            emit_loading_progress("验证配置", 10, room=emit_to_room)
            
            # 初始化系统（带进度通知）
            emit_loading_progress("验证配置", 10, room=emit_to_room)
            
            # 验证配置
            from config import Config
            if not Config.validate_config():
                raise RuntimeError("配置验证失败，请检查配置文件")
            
            emit_loading_progress("加载ASR模型", 20, room=emit_to_room)
            
            # 初始化系统（这里会加载所有组件）
            # 注意：ASR模型加载可能需要30-60秒，这是正常的
            # 我们会在加载完成后立即发送所有后续进度
            
            # 使用一个包装器来监控加载进度
            import threading
            import time
            
            loading_monitor_active = True
            
            def progress_monitor():
                """监控加载进度，定期发送心跳"""
                progress = 20
                iteration = 0
                while loading_monitor_active and progress < 95:
                    time.sleep(2)  # 每2秒更新一次
                    iteration += 1
                    
                    # 在前40%范围内逐渐增加进度
                    if progress < 38:
                        progress += 2
                        emit_loading_progress(f"加载ASR模型中... ({iteration * 2}秒)", progress, room=emit_to_room)
                    elif progress < 95:
                        # 如果加载时间较长，保持在38%左右
                        emit_loading_progress(f"加载ASR模型中... ({iteration * 2}秒，可能需要30-60秒）", 38, room=emit_to_room)
            
            # 启动进度监控线程
            monitor_thread = threading.Thread(target=progress_monitor, daemon=True)
            monitor_thread.start()
            
            try:
                # 初始化系统（这里会加载所有组件，包括ASR模型）
                # 注意：这个过程可能需要30-60秒，特别是ASR模型加载
                print(f"[会话] 开始创建VoiceChatSystem实例...")
                system = VoiceChatSystem()
                print(f"[会话] VoiceChatSystem实例创建成功")
                
                # 系统初始化完成，停止监控并发送最终进度
                loading_monitor_active = False
                
                # 等待监控线程停止（最多等待2.5秒，确保线程退出循环）
                if monitor_thread.is_alive():
                    import time
                    for _ in range(5):  # 最多等待2.5秒（0.5秒 * 5次）
                        time.sleep(0.5)
                        if not monitor_thread.is_alive():
                            break
                
                # 发送各个组件已就绪的信号（快速连续发送，无延迟）
                emit_loading_progress("ASR模型加载完成", 40, room=emit_to_room)
                emit_loading_progress("初始化LLM客户端", 50, room=emit_to_room)
                emit_loading_progress("初始化记忆系统", 60, room=emit_to_room)
                emit_loading_progress("初始化TTS客户端", 70, room=emit_to_room)
                emit_loading_progress("初始化MCP管理器", 80, room=emit_to_room)
                emit_loading_progress("系统初始化完成", 90, room=emit_to_room)
                emit_loading_progress("完成", 100, room=emit_to_room)
                
                # 立即发送完成事件，确保前端及时响应
                try:
                    socketio.emit('loading_complete', {'session_id': session_id}, room=emit_to_room)
                    print(f"[进度] 已发送 loading_complete 事件 (房间: {emit_to_room})")
                except Exception as e:
                    print(f"[进度] 发送 loading_complete 失败: {e}")
                
            except Exception as e:
                loading_monitor_active = False
                import traceback
                error_detail = traceback.format_exc()
                print(f"[会话] 创建VoiceChatSystem失败: {e}")
                print(f"[会话] 详细错误:\n{error_detail}")
                raise
            
            sessions[session_id] = system
            loading_status["is_loading"] = False
            return session_id, system
        except Exception as e:
            loading_status["is_loading"] = False
            if emit_to_room:
                socketio.emit('loading_error', {'error': str(e)}, room=emit_to_room)
            raise
    
    return session_id, sessions[session_id]


def initialize_global_system():
    """初始化全局系统（可选，用于单会话模式）"""
    global global_system
    if global_system is None:
        try:
            print("[系统] 正在初始化全局语音对话系统...")
            global_system = VoiceChatSystem()
            sessions[default_session_id] = global_system
            print("[系统] 全局系统初始化完成")
        except Exception as e:
            print(f"[系统] 全局系统初始化失败: {e}")


@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取系统状态"""
    try:
        global loading_status
        
        # 检查是否有会话已创建
        has_session = len(sessions) > 0
        
        if not has_session:
            return jsonify({
                "asr_ready": False,
                "llm_ready": False,
                "tts_ready": False,
                "mcp_enabled": False,
                "is_loading": loading_status["is_loading"],
                "progress": loading_status["progress"],
                "current_step": loading_status["current_step"],
                "message": "系统未初始化"
            })
        
        # 获取第一个会话的系统
        first_session_id = list(sessions.keys())[0]
        system = sessions[first_session_id]
        
        return jsonify({
            "asr_ready": system.asr is not None,
            "llm_ready": system.llm_client is not None,
            "tts_ready": system.tts_client is not None,
            "mcp_enabled": system.mcp_manager is not None,
            "tts_enabled": system.tts_enabled,
            "streaming_tts_enabled": system.streaming_tts_enabled,
            "sessions_count": len(sessions),
            "is_loading": loading_status["is_loading"],
            "progress": loading_status["progress"],
            "current_step": loading_status["current_step"]
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "asr_ready": False,
            "llm_ready": False,
            "tts_ready": False,
            "mcp_enabled": False,
            "is_loading": False
        }), 500


@app.route("/api/chat/text", methods=["POST"])
def chat_text():
    """文本对话接口"""
    try:
        data = request.json
        message = data.get("message", "").strip()
        session_id = data.get("session_id")
        
        if not message:
            return jsonify({"success": False, "error": "消息不能为空"}), 400
        
        session_id, system = get_or_create_session(session_id, emit_to_room=request.sid)
        
        # 调用LLM对话
        result = system.llm_client.chat_completion(
            messages=system.chat_manager.get_messages() + [
                {"role": "user", "content": message}
            ],
            stream=False,
            on_content=None,
            on_complete=None,
            on_tool_call_detected=None
        )
        
        if result["success"]:
            # 添加到对话历史
            system.chat_manager.add_user_message(message)
            system.chat_manager.add_assistant_message(result["content"])
            
            return jsonify({
                "success": True,
                "content": result["content"],
                "session_id": session_id
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "未知错误")
            }), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chat/audio", methods=["POST"])
def chat_audio():
    """音频对话接口"""
    try:
        session_id = request.form.get("session_id")
        
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "未找到音频文件"}), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({"success": False, "error": "音频文件名为空"}), 400
        
        session_id, system = get_or_create_session(session_id, emit_to_room=request.sid)
        
        # 保存临时音频文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            audio_file.save(tmp_file.name)
            tmp_audio_path = tmp_file.name
        
        try:
            # 读取音频文件
            sample_rate, audio_data = wavfile.read(tmp_audio_path)
            
            # 转换为numpy数组（如果是立体声，转换为单声道）
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # 确保是16kHz采样率（ASR需要）
            if sample_rate != 16000:
                from scipy import signal
                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = signal.resample(audio_data, num_samples)
                sample_rate = 16000
            
            # 转换为float32格式
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                if audio_data.dtype == np.int16:
                    audio_data = audio_data / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data / 2147483648.0
            
            # 调用ASR识别
            asr_result = system.asr.transcribe_audio_data(
                audio_data,
                sample_rate=sample_rate,
                language="auto"
            )
            
            if "error" in asr_result:
                return jsonify({
                    "success": False,
                    "error": f"语音识别失败: {asr_result['error']}"
                }), 500
            
            transcribed_text = asr_result["clean_text"]
            
            # 调用LLM对话
            result = system.llm_client.chat_completion(
                messages=system.chat_manager.get_messages() + [
                    {"role": "user", "content": transcribed_text}
                ],
                stream=False,
                on_content=None,
                on_complete=None,
                on_tool_call_detected=None
            )
            
            if result["success"]:
                # 添加到对话历史
                system.chat_manager.add_user_message(transcribed_text)
                system.chat_manager.add_assistant_message(result["content"])
                
                return jsonify({
                    "success": True,
                    "transcribed_text": transcribed_text,
                    "content": result["content"],
                    "session_id": session_id
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "未知错误")
                }), 500
                
        finally:
            # 清理临时文件
            if os.path.exists(tmp_audio_path):
                os.remove(tmp_audio_path)
                
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chat/history", methods=["GET"])
def get_history():
    """获取对话历史"""
    try:
        session_id = request.args.get("session_id")
        
        if not session_id:
            session_id = default_session_id
        
        if session_id not in sessions:
            return jsonify({"history": []})
        
        system = sessions[session_id]
        messages = system.chat_manager.history
        
        return jsonify({
            "session_id": session_id,
            "history": messages
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/clear", methods=["POST"])
def clear_history():
    """清空对话历史"""
    try:
        data = request.json or {}
        session_id = data.get("session_id")
        
        if not session_id:
            session_id = default_session_id
        
        if session_id in sessions:
            sessions[session_id].chat_manager.clear_history()
            return jsonify({"success": True, "session_id": session_id})
        else:
            return jsonify({"success": False, "error": "会话不存在"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/session/create", methods=["POST"])
def create_session():
    """创建新会话"""
    try:
        session_id = str(uuid.uuid4())
        session_id, system = get_or_create_session(session_id, emit_to_room=request.sid)
        return jsonify({
            "success": True,
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== WebSocket事件处理 ====================

@socketio.on('connect')
def handle_connect():
    """处理WebSocket连接"""
    print(f"[WebSocket] 客户端连接: {request.sid}")
    
    # 检查默认会话是否已存在，如果存在则立即通知前端
    if default_session_id in sessions:
        emit('loading_complete', {'session_id': default_session_id})
        print(f"[WebSocket] 会话已存在，立即发送 loading_complete (会话: {default_session_id})")
    
    emit('connected', {'message': '连接成功'})


@socketio.on('start_loading')
def handle_start_loading(data):
    """开始加载系统"""
    try:
        session_id = data.get('session_id')
        if not session_id:
            session_id = default_session_id
        
        # 如果会话已存在，立即发送完成事件并返回
        if session_id in sessions:
            socketio.emit('loading_complete', {'session_id': session_id}, room=request.sid)
            print(f"[加载] 会话已存在，立即发送 loading_complete (会话: {session_id}, 房间: {request.sid})")
            return
        
        # 在新线程中创建会话并发送进度
        # 需要在创建线程前保存 request.sid，因为线程中没有请求上下文
        client_sid = request.sid
        
        import threading
        def load_system():
            try:
                session_id_result, system = get_or_create_session(session_id, emit_to_room=client_sid)
                # 即使MCP初始化有警告，也认为系统加载成功
                socketio.emit('loading_complete', {'session_id': session_id_result}, room=client_sid)
            except Exception as e:
                import traceback
                error_msg = str(e)
                # 简化错误信息，不包含完整traceback（避免太长）
                if "MCP" in error_msg or "async" in error_msg.lower():
                    # MCP相关错误不影响主要功能
                    print(f"[警告] 加载过程中出现非关键错误: {error_msg}")
                    # 仍然发送加载完成，因为系统基本功能可用
                    try:
                        socketio.emit('loading_complete', {'session_id': session_id}, room=client_sid)
                    except:
                        pass
                else:
                    error_detail = str(e) + '\n' + traceback.format_exc()
                    socketio.emit('loading_error', {'error': error_detail}, room=client_sid)
        
        thread = threading.Thread(target=load_system, daemon=True)
        thread.start()
        
    except Exception as e:
        emit('loading_error', {'error': str(e)})


@socketio.on('disconnect')
def handle_disconnect():
    """处理WebSocket断开"""
    print(f"[WebSocket] 客户端断开: {request.sid}")


@socketio.on('text_message')
def handle_text_message(data):
    """处理文本消息"""
    try:
        session_id = data.get('session_id')
        message = data.get('message', '').strip()
        
        if not message:
            emit('error', {'error': '消息不能为空'})
            return
        
        session_id, system = get_or_create_session(session_id, emit_to_room=request.sid)
        
        # 添加到对话历史
        system.chat_manager.add_user_message(message)
        
        # 发送识别结果（文本输入也使用transcribed事件，保持一致性，立即发送）
        socketio.emit('transcribed', {'text': message, 'session_id': session_id}, room=request.sid)
        socketio.sleep(0)  # 强制立即发送
        
        # 流式调用LLM
        accumulated_content = ""
        
        def on_content(content: str):
            """流式内容回调"""
            nonlocal accumulated_content
            accumulated_content += content
            socketio.emit('llm_content', {
                'content': content,
                'session_id': session_id
            }, room=request.sid)
            # 强制立即发送，避免缓冲
            socketio.sleep(0)
        
        def on_tool_call_detected():
            """工具调用检测回调"""
            socketio.emit('system_message', {
                'type': 'tool_call',
                'message': '🔧 检测到工具调用，开始处理...',
                'session_id': session_id
            }, room=request.sid)
            socketio.sleep(0)  # 强制立即发送
        
        def on_mcp_iteration(iteration: int, max_iterations: int, tool_names: list = None):
            """MCP循环迭代回调"""
            if tool_names and len(tool_names) > 0:
                socketio.emit('system_message', {
                    'type': 'mcp_iteration',
                    'message': f'🔄 MCP循环第 {iteration}/{max_iterations} 次: 调用工具 {", ".join(tool_names)}',
                    'session_id': session_id
                }, room=request.sid)
                socketio.sleep(0)  # 强制立即发送
            else:
                socketio.emit('system_message', {
                    'type': 'mcp_iteration',
                    'message': f'🔄 MCP循环第 {iteration}/{max_iterations} 次',
                    'session_id': session_id
                }, room=request.sid)
                socketio.sleep(0)  # 强制立即发送
        
        def on_tool_execution(tool_name: str):
            """工具执行开始回调"""
            socketio.emit('system_message', {
                'type': 'tool_execution',
                'message': f'⚙️ 开始执行工具: {tool_name}',
                'session_id': session_id
            }, room=request.sid)
            socketio.sleep(0)  # 强制立即发送
        
        def on_tool_complete(tool_name: str):
            """工具执行完成回调"""
            socketio.emit('system_message', {
                'type': 'tool_complete',
                'message': f'✅ 工具执行完成: {tool_name}',
                'session_id': session_id
            }, room=request.sid)
            socketio.sleep(0)  # 强制立即发送
        
        def on_complete(result: dict):
            """完成回调"""
            if result["success"]:
                # 确保最终内容被发送到前端（特别是MCP调用后的回复）
                final_content = result.get("content", "")
                # 只在没有流式内容或MCP调用后才发送完整内容
                # 如果已经有流式内容，finishLLMResponse会处理，这里只发送完成信号
                if final_content and accumulated_content == "":
                    # 没有流式内容（可能是MCP调用后的完整回复），发送完整内容
                    system.chat_manager.add_assistant_message(final_content)
                    socketio.emit('llm_complete', {
                        'content': final_content,
                        'session_id': session_id
                    }, room=request.sid)
                elif final_content:
                    # 有流式内容，只发送完成信号，不覆盖流式内容
                    system.chat_manager.add_assistant_message(final_content)
                    socketio.emit('llm_complete', {
                        'content': '',  # 发送空内容表示完成，由前端保持流式内容
                        'session_id': session_id
                    }, room=request.sid)
            else:
                socketio.emit('error', {
                    'error': result.get("error", "未知错误"),
                    'session_id': session_id
                }, room=request.sid)
        
        # 调用LLM（流式）
        result = system.llm_client.chat_completion(
            messages=system.chat_manager.get_messages(),
            stream=True,
            on_content=on_content,
            on_complete=on_complete,
            on_tool_call_detected=on_tool_call_detected,
            on_mcp_iteration=on_mcp_iteration,
            on_tool_execution=on_tool_execution,
            on_tool_complete=on_tool_complete
        )
        
    except Exception as e:
        emit('error', {'error': str(e)})


@socketio.on('audio_data')
def handle_audio_data(data):
    """处理音频数据（base64编码）"""
    try:
        session_id = data.get('session_id')
        audio_base64 = data.get('audio_data')
        sample_rate = data.get('sample_rate', 16000)
        
        if not audio_base64:
            emit('error', {'error': '音频数据为空'})
            return
        
        session_id, system = get_or_create_session(session_id, emit_to_room=request.sid)
        
        # 解码base64音频数据
        audio_bytes = base64.b64decode(audio_base64)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        
        # 发送系统消息：语音识别中
        socketio.emit('system_message', {
            'type': 'asr',
            'message': '🎤 正在进行语音识别...',
            'session_id': session_id
        }, room=request.sid)
        
        # 调用ASR识别
        asr_result = system.asr.transcribe_audio_data(
            audio_array,
            sample_rate=sample_rate,
            language="auto"
        )
        
        if "error" in asr_result:
            emit('error', {'error': f"语音识别失败: {asr_result['error']}"})
            return
        
        transcribed_text = asr_result["clean_text"]
        
        # 发送系统消息：识别完成
        socketio.emit('system_message', {
            'type': 'asr',
            'message': f'✅ 语音识别完成: {transcribed_text[:30]}...',
            'session_id': session_id
        }, room=request.sid)
        
        # 添加到对话历史
        system.chat_manager.add_user_message(transcribed_text)
        
        # 发送识别结果（立即发送，确保前端立即显示）
        socketio.emit('transcribed', {
            'text': transcribed_text,
            'session_id': session_id
        }, room=request.sid)
        socketio.sleep(0)  # 强制立即发送
        
        # 流式调用LLM
        accumulated_content = ""
        
        def on_content(content: str):
            """流式内容回调"""
            nonlocal accumulated_content
            accumulated_content += content
            socketio.emit('llm_content', {
                'content': content,
                'session_id': session_id
            }, room=request.sid)
            # 强制立即发送，避免缓冲
            socketio.sleep(0)
        
        def on_tool_call_detected():
            """工具调用检测回调"""
            socketio.emit('system_message', {
                'type': 'tool_call',
                'message': '🔧 检测到工具调用，开始处理...',
                'session_id': session_id
            }, room=request.sid)
            socketio.sleep(0)  # 强制立即发送
        
        def on_mcp_iteration(iteration: int, max_iterations: int, tool_names: list = None):
            """MCP循环迭代回调"""
            if tool_names and len(tool_names) > 0:
                socketio.emit('system_message', {
                    'type': 'mcp_iteration',
                    'message': f'🔄 MCP循环第 {iteration}/{max_iterations} 次: 调用工具 {", ".join(tool_names)}',
                    'session_id': session_id
                }, room=request.sid)
                socketio.sleep(0)  # 强制立即发送
            else:
                socketio.emit('system_message', {
                    'type': 'mcp_iteration',
                    'message': f'🔄 MCP循环第 {iteration}/{max_iterations} 次',
                    'session_id': session_id
                }, room=request.sid)
                socketio.sleep(0)  # 强制立即发送
        
        def on_tool_execution(tool_name: str):
            """工具执行开始回调"""
            socketio.emit('system_message', {
                'type': 'tool_execution',
                'message': f'⚙️ 开始执行工具: {tool_name}',
                'session_id': session_id
            }, room=request.sid)
            socketio.sleep(0)  # 强制立即发送
        
        def on_tool_complete(tool_name: str):
            """工具执行完成回调"""
            socketio.emit('system_message', {
                'type': 'tool_complete',
                'message': f'✅ 工具执行完成: {tool_name}',
                'session_id': session_id
            }, room=request.sid)
            socketio.sleep(0)  # 强制立即发送
        
        def on_complete(result: dict):
            """完成回调"""
            if result["success"]:
                # 确保最终内容被发送到前端（特别是MCP调用后的回复）
                final_content = result.get("content", "")
                # 只在没有流式内容或MCP调用后才发送完整内容
                # 如果已经有流式内容，finishLLMResponse会处理，这里只发送完成信号
                if final_content and accumulated_content == "":
                    # 没有流式内容（可能是MCP调用后的完整回复），发送完整内容
                    system.chat_manager.add_assistant_message(final_content)
                    socketio.emit('llm_complete', {
                        'content': final_content,
                        'session_id': session_id
                    }, room=request.sid)
                elif final_content:
                    # 有流式内容，只发送完成信号，不覆盖流式内容
                    system.chat_manager.add_assistant_message(final_content)
                    socketio.emit('llm_complete', {
                        'content': '',  # 发送空内容表示完成，由前端保持流式内容
                        'session_id': session_id
                    }, room=request.sid)
            else:
                socketio.emit('error', {
                    'error': result.get("error", "未知错误"),
                    'session_id': session_id
                }, room=request.sid)
        
        # 调用LLM（流式）
        result = system.llm_client.chat_completion(
            messages=system.chat_manager.get_messages(),
            stream=True,
            on_content=on_content,
            on_complete=on_complete,
            on_tool_call_detected=on_tool_call_detected,
            on_mcp_iteration=on_mcp_iteration,
            on_tool_execution=on_tool_execution,
            on_tool_complete=on_tool_complete
        )
        
    except Exception as e:
        emit('error', {'error': str(e)})


@socketio.on('get_history')
def handle_get_history(data):
    """获取对话历史（WebSocket）"""
    try:
        session_id = data.get('session_id', default_session_id)
        
        if session_id in sessions:
            system = sessions[session_id]
            messages = system.chat_manager.history
            emit('history', {
                'history': messages,
                'session_id': session_id
            })
        else:
            emit('history', {'history': [], 'session_id': session_id})
            
    except Exception as e:
        emit('error', {'error': str(e)})


@socketio.on('clear_history')
def handle_clear_history(data):
    """清空对话历史（WebSocket）"""
    try:
        session_id = data.get('session_id', default_session_id)
        
        if session_id in sessions:
            sessions[session_id].chat_manager.clear_history()
            emit('history_cleared', {'session_id': session_id})
        else:
            emit('error', {'error': '会话不存在'})
            
    except Exception as e:
        emit('error', {'error': str(e)})


if __name__ == "__main__":
    # 延迟初始化全局系统（避免启动时阻塞）
    print("[应用] 正在启动Flask应用...")
    print("[提示] 系统将在首次请求时初始化")
    
    # 启动应用
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True
    )
