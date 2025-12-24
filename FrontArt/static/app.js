/**
 * 语音对话系统 - 前端应用
 * 简洁、功能完整的实现
 */

class VoiceChatApp {
    constructor() {
        this.socket = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.mediaStream = null;
        this.audioContext = null;
        this.processorNode = null;
        this.sourceNode = null;
        this.inputSampleRate = 44100;
        this.targetSampleRate = 16000;
        this.downsampledBuffers = [];
        this.audioChunks = [];
        this.pendingUserEcho = null;
        this.sessionId = null;
        this.systemReady = false;
        this.hasOpenAssistantMessage = false;
        this.receivedLLMStream = false;
        this.isLoadingFlow = false;
        this.loadingPollTimer = null;
        this.hasEnteredMain = false;
        
        this.initializeElements();
        this.initializeSocket();
        this.attachEventListeners();
    }

    /**
     * 初始化DOM元素引用
     */
    initializeElements() {
        // 主要元素
        this.app = document.querySelector('#app');
        this.loadingScreen = document.querySelector('#loadingScreen');
        this.messagesContainer = document.querySelector('#messagesContainer');
        
        // 状态指示器
        this.statusDot = document.querySelector('#statusDot');
        this.statusText = document.querySelector('#statusText');
        this.progressFill = document.querySelector('#progressFill');
        this.progressText = document.querySelector('#progressText');
        this.loadingStep = document.querySelector('#loadingStep');

        // MCP状态卡片元素
        this.mcpStatusBox = document.querySelector('#mcpStatusBox');
        this.mcpTimerEl = document.querySelector('#mcpTimer');
        this.mcpTextEl = document.querySelector('#mcpText');
        this.mcpToolsEl = document.querySelector('#mcpTools');
        
        // 按钮
        this.recordBtn = document.querySelector('#recordBtn');
        this.textInputBtn = document.querySelector('#textInputBtn');
        this.historyBtn = document.querySelector('#historyBtn');
        this.clearBtn = document.querySelector('#clearBtn');
        this.sendBtn = document.querySelector('#sendBtn');
        
        // 输入区域
        this.textInputArea = document.querySelector('#textInputArea');
        this.textInput = document.querySelector('#textInput');
        
        // 状态显示
        this.asrStatus = document.querySelector('#asrStatus');
        this.llmStatus = document.querySelector('#llmStatus');
        this.ttsStatus = document.querySelector('#ttsStatus');
        this.mcpStatus = document.querySelector('#mcpStatus');
        
        // 开关
        this.ttsToggle = document.querySelector('#ttsToggle');
        this.realtimeToggle = document.querySelector('#realtimeToggle');
        
        // 模态框
        this.historyModal = document.querySelector('#historyModal');
        this.historyContent = document.querySelector('#historyContent');
        this.closeHistoryBtn = document.querySelector('#closeHistoryBtn');
        this.confirmModal = document.querySelector('#confirmModal');
        this.confirmBtn = document.querySelector('#confirmBtn');
        this.cancelBtn = document.querySelector('#cancelBtn');
    }

    /**
     * 初始化WebSocket连接
     */
    initializeSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('[WebSocket] 已连接');
            this.updateConnectionStatus(true);
            if (!this.systemReady && !this.isLoadingFlow && !this.hasEnteredMain) {
                this.startLoadingSequence();
            }
        });

        this.socket.on('disconnect', () => {
            console.log('[WebSocket] 已断开');
            this.updateConnectionStatus(false);
            if (this.loadingPollTimer) {
                clearInterval(this.loadingPollTimer);
                this.loadingPollTimer = null;
            }
        });

        // 加载进度事件
        this.socket.on('loading_progress', (data) => {
            if (this.systemReady) return; // 已就绪则忽略后续进度事件，防止抖动
            this.updateLoadingProgress(data.step, data.progress);
        });

        // 加载完成事件
        this.socket.on('loading_complete', (data) => {
            console.log('[加载] 系统初始化完成');
            this.sessionId = data.session_id || this.sessionId || 'default';
            this.systemReady = true;
            this.hideLoadingScreen();
            this.updateSystemStatus();
        });

        // 后端状态同步事件（TTS/实时语音）
        this.socket.on('state_update', (data) => {
            if (data.session_id && !this.sessionId) {
                this.sessionId = data.session_id;
            }
            if (typeof data.tts_enabled === 'boolean') {
                this.ttsToggle.checked = data.tts_enabled;
            }
            if (typeof data.realtime_voice_enabled === 'boolean') {
                this.realtimeToggle.checked = data.realtime_voice_enabled;
            }
        });

        // MCP系统消息驱动计时器与状态
        this.socket.on('system_message', (data) => {
            const t = data.type || 'info';
            if (t === 'tool_call') {
                this.startMcpTimer();
                this.mcpTextEl.textContent = '工具调用开始';
                this.mcpToolsEl.textContent = '-';
            } else if (t === 'mcp_iteration') {
                const iter = data.iteration || 0;
                const maxIter = data.max_iterations || 0;
                this.mcpTextEl.textContent = `MCP循环 ${iter}/${maxIter}`;
                const names = (data.tool_names || []).join(', ');
                this.mcpToolsEl.textContent = names || '-';
                if (!this.mcpTimerId) this.startMcpTimer();
            } else if (t === 'tool_execution') {
                const tool = data.tool_name || '';
                this.mcpTextEl.textContent = `执行工具: ${tool}`;
                if (!this.mcpTimerId) this.startMcpTimer();
            } else if (t === 'tool_complete') {
                const tool = data.tool_name || '';
                this.mcpTextEl.textContent = `工具完成: ${tool}`;
                this.stopMcpTimer(true);
            } else if (t === 'asr') {
                // 其它系统提示（如ASR）走Toast
                this.showToast(data.message || '', 'info');
            } else {
                this.showToast(data.message || '', 'info');
            }
        });

        // 加载错误事件
        this.socket.on('loading_error', (data) => {
            console.error('[加载] 错误:', data.error);
            this.showError('系统初始化失败: ' + data.error);
        });

        // 转录完成事件
        this.socket.on('transcribed', (data) => {
            // 开启新一轮流式会话状态
            this.hasOpenAssistantMessage = false;
            this.receivedLLMStream = false;
            this.addUserMessageOnce(data.text);
        });

        // LLM流式内容
        this.socket.on('llm_content', (data) => {
            this.receivedLLMStream = true;
            // 确保有assistant占位气泡
            this.ensureAssistantPlaceholder();
            this.appendToLastAssistantMessage(data.content);
        });

        // LLM完成
        this.socket.on('llm_complete', (data) => {
            // 结束占位标记
            const hadStream = this.receivedLLMStream;
            this.hasOpenAssistantMessage = false;
            this.receivedLLMStream = false;
            if (!hadStream && data.content) {
                // 只有未收到流式时才一次性追加完整内容，避免重复
                this.addMessage('assistant', data.content);
            }
        });

        // 系统消息
        this.socket.on('system_message', (data) => {
            this.showToast(data.message, 'info');
        });

        // 错误处理
        this.socket.on('error', (data) => {
            this.showError(data.error);
        });

        // 历史记录
        this.socket.on('history', (data) => {
            this.displayHistory(data.history);
        });

        // 历史清空
        this.socket.on('history_cleared', (data) => {
            this.showToast('✅ 对话历史已清空', 'success');
        });
    }

    /**
     * 绑定事件监听器
     */
    attachEventListeners() {
        // 录音按钮
        this.recordBtn.addEventListener('mousedown', () => this.startRecording());
        this.recordBtn.addEventListener('mouseup', () => this.stopRecording());
        this.recordBtn.addEventListener('mouseleave', () => {
            if (this.isRecording) this.stopRecording();
        });

        // 触摸设备支持
        this.recordBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        this.recordBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopRecording();
        });

        // 文字输入按钮
        this.textInputBtn.addEventListener('click', () => {
            this.toggleTextInput();
        });

        // 发送按钮
        this.sendBtn.addEventListener('click', () => {
            this.sendTextMessage();
        });

        // 文字输入框回车发送
        this.textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendTextMessage();
            }
        });

        // 历史按钮
        this.historyBtn.addEventListener('click', () => {
            this.socket.emit('get_history', { session_id: this.sessionId });
        });

        // 清空按钮
        this.clearBtn.addEventListener('click', () => {
            this.showConfirmDialog('确定要清空对话历史吗？', () => {
                this.socket.emit('clear_history', { session_id: this.sessionId });
            });
        });

        // 模态框关闭
        this.closeHistoryBtn.addEventListener('click', () => {
            this.historyModal.classList.remove('active');
        });

        this.cancelBtn.addEventListener('click', () => {
            this.confirmModal.classList.remove('active');
        });

        // 点击模态框背景关闭
        this.historyModal.addEventListener('click', (e) => {
            if (e.target === this.historyModal) {
                this.historyModal.classList.remove('active');
            }
        });

        this.confirmModal.addEventListener('click', (e) => {
            if (e.target === this.confirmModal) {
                this.confirmModal.classList.remove('active');
            }
        });

        // 开关事件
        this.ttsToggle.addEventListener('change', () => {
            this.handleTtsToggle();
        });

        this.realtimeToggle.addEventListener('change', () => {
            this.handleRealtimeToggle();
        });

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }

    /**
     * 处理键盘快捷键
     */
    handleKeyboardShortcuts(e) {
        // 检查是否在输入框中
        if (e.target === this.textInput) {
            return;
        }

        // 小键盘快捷键
        if (e.code === 'Numpad4') {
            e.preventDefault();
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        } else if (e.code === 'Numpad5') {
            e.preventDefault();
            this.toggleTextInput();
        } else if (e.code === 'Numpad6') {
            e.preventDefault();
            this.socket.emit('get_history', { session_id: this.sessionId });
        } else if (e.code === 'Numpad7') {
            e.preventDefault();
            this.showConfirmDialog('确定要清空对话历史吗？', () => {
                this.socket.emit('clear_history', { session_id: this.sessionId });
            });
        } else if (e.code === 'Numpad8') {
            e.preventDefault();
            this.ttsToggle.checked = !this.ttsToggle.checked;
            this.handleTtsToggle();
        } else if (e.code === 'Numpad9') {
            e.preventDefault();
            this.realtimeToggle.checked = !this.realtimeToggle.checked;
            this.handleRealtimeToggle();
        }
    }

    /**
     * 开始录音
     */
    async startRecording() {
        if (this.isRecording || !this.systemReady) return;

        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
            // 创建音频上下文（尽量使用16k采样率）
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: this.targetSampleRate });
            this.inputSampleRate = this.audioContext.sampleRate || 44100;

            this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
            const bufferSize = 4096;
            this.processorNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

            this.processorNode.onaudioprocess = (event) => {
                const inputBuffer = event.inputBuffer.getChannelData(0);
                // 下采样并存储为Int16
                const int16Frame = this.resampleFloat32ToInt16(inputBuffer, this.inputSampleRate, this.targetSampleRate);
                if (int16Frame && int16Frame.length > 0) {
                    this.downsampledBuffers.push(int16Frame);
                }
            };

            this.sourceNode.connect(this.processorNode);
            // 连接到静音增益，避免回放到扬声器造成回声
            const silentGain = this.audioContext.createGain();
            silentGain.gain.value = 0;
            this.processorNode.connect(silentGain);
            silentGain.connect(this.audioContext.destination);

            this.isRecording = true;
            this.downsampledBuffers = [];
            this.recordBtn.classList.add('recording');
            this.recordBtn.querySelector('.btn-text').textContent = '录音中...';
            this.showToast('🎤 开始录音...', 'info');
        } catch (error) {
            console.error('[录音] 错误:', error);
            this.showError('无法访问麦克风: ' + error.message);
        }
    }

    /**
     * 停止录音
     */
    stopRecording() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.recordBtn.classList.remove('recording');
        this.recordBtn.querySelector('.btn-text').textContent = '录音';

        try {
            if (this.processorNode) {
                this.processorNode.disconnect();
                this.processorNode.onaudioprocess = null;
                this.processorNode = null;
            }
            if (this.sourceNode) {
                this.sourceNode.disconnect();
                this.sourceNode = null;
            }
            if (this.audioContext) {
                const ctx = this.audioContext;
                this.audioContext = null;
                // 优雅关闭
                ctx.close && ctx.close().catch(() => {});
            }
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(t => t.stop());
                this.mediaStream = null;
            }
        } catch (e) {
            console.warn('[录音] 释放资源警告:', e);
        }

        this.handleRecordingStop();
    }

    /**
     * 处理录音停止
     */
    handleRecordingStop() {
        this.showToast('⏹️ 录音结束，正在处理...', 'info');
        // 合并所有Int16帧
        const totalLength = this.downsampledBuffers.reduce((sum, arr) => sum + arr.length, 0);
        if (!totalLength) {
            this.showError('未捕获到有效音频，请重试');
            return;
        }
        const merged = new Int16Array(totalLength);
        let offset = 0;
        for (const chunk of this.downsampledBuffers) {
            merged.set(chunk, offset);
            offset += chunk.length;
        }
        // 编码为Base64
        const base64Audio = this.arrayBufferToBase64(merged.buffer);
        this.socket.emit('audio_data', {
            session_id: this.sessionId,
            audio_data: base64Audio,
            sample_rate: this.targetSampleRate
        });
        // 清空缓存
        this.downsampledBuffers = [];
    }

    /**
     * ArrayBuffer转Base64
     */
    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const chunkSize = 0x8000; // 分块避免堆栈溢出
        for (let i = 0; i < bytes.byteLength; i += chunkSize) {
            const chunk = bytes.subarray(i, i + chunkSize);
            binary += String.fromCharCode.apply(null, chunk);
        }
        return btoa(binary);
    }

    /**
     * 将Float32 PCM重采样为Int16（线性插值）
     */
    resampleFloat32ToInt16(float32Array, fromSampleRate, toSampleRate) {
        if (!float32Array || float32Array.length === 0) return new Int16Array(0);
        if (fromSampleRate === toSampleRate) {
            // 直接转换
            const out = new Int16Array(float32Array.length);
            for (let i = 0; i < float32Array.length; i++) {
                let s = Math.max(-1, Math.min(1, float32Array[i]));
                out[i] = (s < 0 ? s * 32768 : s * 32767) | 0;
            }
            return out;
        }
        const ratio = fromSampleRate / toSampleRate;
        const newLength = Math.round(float32Array.length / ratio);
        const out = new Int16Array(newLength);
        let pos = 0;
        for (let i = 0; i < newLength; i++) {
            const idx = i * ratio;
            const i0 = Math.floor(idx);
            const i1 = Math.min(i0 + 1, float32Array.length - 1);
            const frac = idx - i0;
            const sample = float32Array[i0] * (1 - frac) + float32Array[i1] * frac;
            let s = Math.max(-1, Math.min(1, sample));
            out[pos++] = (s < 0 ? s * 32768 : s * 32767) | 0;
        }
        return out;
    }

    /**
     * 切换文字输入区域
     */
    toggleTextInput() {
        const isVisible = this.textInputArea.style.display !== 'none';
        if (isVisible) {
            this.textInputArea.style.display = 'none';
        } else {
            this.textInputArea.style.display = 'flex';
            this.textInput.focus();
        }
    }

    /**
     * 发送文本消息
     */
    sendTextMessage() {
        const message = this.textInput.value.trim();
        if (!message || !this.systemReady) return;

        // 先在本地显示用户消息，并标记避免服务端回显重复
        this.addMessage('user', message);
        this.pendingUserEcho = message;
        this.textInput.value = '';
        this.socket.emit('text_message', {
            session_id: this.sessionId,
            message: message
        });
    }

    /**
     * 添加消息到聊天区域
     */
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const p = document.createElement('p');
        p.textContent = content;
        
        messageDiv.appendChild(p);
        this.messagesContainer.appendChild(messageDiv);
        
        // 自动滚动到底部
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    /**
     * 确保存在一个assistant占位消息用于流式追加
     */
    ensureAssistantPlaceholder() {
        if (!this.hasOpenAssistantMessage) {
            this.addMessage('assistant', '');
            this.hasOpenAssistantMessage = true;
        }
    }

    /**
     * 向最后一条assistant消息追加内容
     */
    appendToLastAssistantMessage(content) {
        const messages = this.messagesContainer.querySelectorAll('.message.assistant');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            const p = lastMessage.querySelector('p');
            if (p) {
                p.textContent += content;
                this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
            }
        } else {
            // 如果没有assistant消息，则创建一个
            this.ensureAssistantPlaceholder();
            this.appendToLastAssistantMessage(content);
        }
    }

    /**
     * 仅在未回显的情况下添加用户消息
     */
    addUserMessageOnce(text) {
        if (this.pendingUserEcho && this.pendingUserEcho === text) {
            // 服务端回显，与已显示一致，跳过
            this.pendingUserEcho = null;
            return;
        }
        this.addMessage('user', text);
    }

    /**
     * 显示错误信息
     */
    showError(message) {
        this.showToast('❌ ' + message, 'error');
    }

    /**
     * 右下角Toast
     */
    showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            if (toast && toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, duration);
    }

    /**
     * 显示确认对话框
     */
    showConfirmDialog(message, onConfirm) {
        document.querySelector('#confirmMessage').textContent = message;
        this.confirmModal.classList.add('active');
        
        // 清除之前的事件监听器
        const newConfirmBtn = this.confirmBtn.cloneNode(true);
        this.confirmBtn.parentNode.replaceChild(newConfirmBtn, this.confirmBtn);
        this.confirmBtn = newConfirmBtn;
        
        this.confirmBtn.addEventListener('click', () => {
            onConfirm();
            this.confirmModal.classList.remove('active');
        });
    }

    /**
     * 显示对话历史
     */
    displayHistory(history) {
        if (!history || history.length === 0) {
            this.historyContent.innerHTML = '<p style="text-align: center; color: #999;">暂无对话历史</p>';
        } else {
            let html = '';
            for (const msg of history) {
                const role = msg.role === 'user' ? '👤 用户' : '🤖 助手';
                html += `
                    <div class="history-item">
                        <div class="history-role">${role}</div>
                        <div class="history-content">${this.escapeHtml(msg.content)}</div>
                    </div>
                `;
            }
            this.historyContent.innerHTML = html;
        }
        this.historyModal.classList.add('active');
    }

    /**
     * 转义HTML特殊字符
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 处理TTS开关
     */
    handleTtsToggle() {
        const enabled = this.ttsToggle.checked;
        this.socket.emit('toggle_tts', { session_id: this.sessionId });
        const status = enabled ? '开启' : '关闭';
        this.showToast(`🔊 TTS语音合成已${status}`, 'info');
    }

    /**
     * 处理实时语音开关
     */
    handleRealtimeToggle() {
        const enabled = this.realtimeToggle.checked;
        this.socket.emit('toggle_realtime', { session_id: this.sessionId });
        const status = enabled ? '开启' : '关闭';
        this.showToast(`🗣️ 实时语音识别已${status}`, 'info');
    }

    /**
     * 更新连接状态
     */
    updateConnectionStatus(connected) {
        if (connected) {
            this.statusDot.classList.add('connected');
            this.statusDot.classList.remove('disconnected');
            this.statusText.textContent = '已连接';
        } else {
            this.statusDot.classList.remove('connected');
            this.statusDot.classList.add('disconnected');
            this.statusText.textContent = '已断开';
        }
    }

    /**
     * 更新加载进度
     */
    updateLoadingProgress(step, progress) {
        this.loadingStep.textContent = step;
        this.progressFill.style.width = progress + '%';
        this.progressText.textContent = Math.round(progress) + '%';
    }

    /**
     * 隐藏加载屏幕
     */
    hideLoadingScreen() {
        if (this.loadingPollTimer) {
            clearInterval(this.loadingPollTimer);
            this.loadingPollTimer = null;
        }
        this.isLoadingFlow = false;
        this.hasEnteredMain = true;
        this.loadingScreen.style.display = 'none';
    }

    /**
     * 启动加载序列（含轮询兜底）
     */
    startLoadingSequence() {
        if (this.systemReady) return; // 已就绪不再进入加载流程
        this.isLoadingFlow = true;
        // 显示加载界面
        this.loadingScreen.style.display = 'flex';
        // 触发后端加载
        this.socket.emit('start_loading', { session_id: null });
        // 轮询 /api/status 兜底进度
        if (this.loadingPollTimer) {
            clearInterval(this.loadingPollTimer);
        }
        this.loadingPollTimer = setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                // 同步进度
                if (typeof data.progress === 'number') {
                    this.updateLoadingProgress(data.current_step || '初始化中...', data.progress);
                }
                // 如果系统已就绪或进度到100，结束加载
                if ((data.sessions_count && data.sessions_count > 0) || data.progress >= 100 || data.is_loading === false) {
                    this.systemReady = true;
                    if (!this.sessionId) this.sessionId = 'default';
                    this.hideLoadingScreen();
                    this.updateSystemStatus();
                }
            } catch (err) {
                // 忽略瞬时错误
            }
        }, 1000);
    }

    /**
     * 更新系统状态
     */
    updateSystemStatus() {
        // 发送状态请求
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                this.asrStatus.textContent = data.asr_ready ? '✅ 就绪' : '❌ 未就绪';
                this.asrStatus.className = 'value ' + (data.asr_ready ? 'ready' : 'error');
                
                this.llmStatus.textContent = data.llm_ready ? '✅ 就绪' : '❌ 未就绪';
                this.llmStatus.className = 'value ' + (data.llm_ready ? 'ready' : 'error');
                
                this.ttsStatus.textContent = data.tts_ready ? '✅ 就绪' : '❌ 未就绪';
                this.ttsStatus.className = 'value ' + (data.tts_ready ? 'ready' : 'error');
                
                this.mcpStatus.textContent = data.mcp_enabled ? '✅ 已启用' : '⚠️ 未启用';
                this.mcpStatus.className = 'value ' + (data.mcp_enabled ? 'ready' : '');
            })
            .catch(err => console.error('[状态] 获取失败:', err));
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new VoiceChatApp();
});

