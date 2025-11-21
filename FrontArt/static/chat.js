/**
 * 语音对话系统 - 前端通信模块
 * 负责WebSocket通信和音频录制
 */

// WebSocket客户端
let socket = null;
let sessionId = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let audioContext = null;
let currentStream = null;

// 音频配置
const AUDIO_CONFIG = {
    sampleRate: 16000,
    channels: 1,
    bitsPerSample: 16
};

/**
 * 初始化WebSocket连接
 */
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}`;
    
    socket = io(wsUrl);
    
    // 将socket暴露给外部，便于前端访问
    window.chatModule.socket = socket;
    
    socket.on('connect', () => {
        console.log('[WebSocket] 连接成功');
        updateConnectionStatus(true);
        
        // 创建或获取会话ID
        if (!sessionId) {
            sessionId = localStorage.getItem('sessionId') || generateSessionId();
            localStorage.setItem('sessionId', sessionId);
        }
    });
    
    socket.on('disconnect', () => {
        console.log('[WebSocket] 连接断开');
        updateConnectionStatus(false);
    });
    
    socket.on('connected', (data) => {
        console.log('[WebSocket] 服务器确认连接:', data);
        // 连接成功后，通知外部模块可以检查加载状态
        if (window.chatModule && window.chatModule.onConnected) {
            window.chatModule.onConnected();
        }
    });
    
    // 监听加载完成事件（可能在连接时就已收到）
    socket.on('loading_complete', (data) => {
        console.log('[WebSocket] 收到加载完成事件:', data);
        // 通知外部模块
        if (window.chatModule && window.chatModule.onLoadingComplete) {
            window.chatModule.onLoadingComplete(data);
        }
    });
    
    // 接收识别结果
    socket.on('transcribed', (data) => {
        console.log('[ASR] 识别结果:', data.text);
        displayTranscribedText(data.text);
    });
    
    // 接收流式LLM内容
    socket.on('llm_content', (data) => {
        console.log('[LLM] 流式内容:', data.content);
        appendLLMContent(data.content);
    });
    
    // 接收LLM完成消息
    socket.on('llm_complete', (data) => {
        console.log('[LLM] 完成:', data.content);
        finishLLMResponse(data.content);
    });
    
    // 接收错误
    socket.on('error', (data) => {
        console.error('[错误]', data.error);
        showError(data.error);
    });
    
    // 接收历史记录
    socket.on('history', (data) => {
        console.log('[历史]', data.history);
        displayHistory(data.history);
    });
    
    // 历史已清空
    socket.on('history_cleared', (data) => {
        console.log('[历史] 已清空');
        clearChatDisplay();
    });
    
    // 接收系统消息
    socket.on('system_message', (data) => {
        console.log('[系统消息]', data.type, data.message);
        // 调用外部模块的系统消息处理函数
        if (window.chatModule && window.chatModule.onSystemMessage) {
            window.chatModule.onSystemMessage(data);
        }
    });
}

/**
 * 生成会话ID
 */
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

/**
 * 更新连接状态显示
 */
function updateConnectionStatus(connected) {
    const statusElement = document.querySelector('.connection-status');
    if (statusElement) {
        statusElement.textContent = connected ? '已连接' : '未连接';
        statusElement.classList.toggle('connected', connected);
        statusElement.classList.toggle('disconnected', !connected);
    }
}

/**
 * 初始化音频录制
 */
async function initAudioRecording() {
    try {
        // 请求麦克风权限
        currentStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: AUDIO_CONFIG.channels,
                sampleRate: AUDIO_CONFIG.sampleRate,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
        
        // 创建AudioContext用于处理音频
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: AUDIO_CONFIG.sampleRate
        });
        
        // 创建MediaRecorder
        const options = {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 128000
        };
        
        // 检查浏览器支持
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'audio/webm';
        }
        
        mediaRecorder = new MediaRecorder(currentStream, options);
        
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            // 处理录制的音频
            await processRecordedAudio();
        };
        
        console.log('[音频] 音频录制初始化成功');
        return true;
        
    } catch (error) {
        console.error('[音频] 初始化失败:', error);
        showError('无法访问麦克风: ' + error.message);
        return false;
    }
}

/**
 * 开始录音
 */
async function startRecording() {
    if (isRecording) {
        return;
    }
    
    if (!mediaRecorder) {
        const success = await initAudioRecording();
        if (!success) {
            return;
        }
    }
    
    if (mediaRecorder.state === 'recording') {
        return;
    }
    
    try {
        audioChunks = [];
        mediaRecorder.start(1000); // 每1秒生成一个数据块
        isRecording = true;
        updateRecordingUI(true);
        console.log('[录音] 开始录音');
    } catch (error) {
        console.error('[录音] 启动失败:', error);
        showError('启动录音失败: ' + error.message);
    }
}

/**
 * 停止录音
 */
function stopRecording() {
    if (!isRecording || !mediaRecorder) {
        return;
    }
    
    if (mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
    
    isRecording = false;
    updateRecordingUI(false);
    console.log('[录音] 停止录音');
}

/**
 * 处理录制的音频
 */
async function processRecordedAudio() {
    try {
        if (audioChunks.length === 0) {
            console.warn('[音频] 没有录制到音频数据');
            return;
        }
        
        // 合并音频块
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        
        // 转换为WAV格式
        const wavBlob = await convertToWAV(audioBlob);
        
        // 转换为base64
        const base64Audio = await blobToBase64(wavBlob);
        
        // 通过WebSocket发送音频数据
        if (socket && socket.connected) {
            socket.emit('audio_data', {
                session_id: sessionId,
                audio_data: base64Audio,
                sample_rate: AUDIO_CONFIG.sampleRate
            });
            
            console.log('[音频] 音频数据已发送');
        } else {
            showError('WebSocket未连接');
        }
        
    } catch (error) {
        console.error('[音频] 处理失败:', error);
        showError('处理音频失败: ' + error.message);
    }
}

/**
 * 将Blob转换为WAV格式
 */
async function convertToWAV(audioBlob) {
    try {
        // 读取音频数据
        const arrayBuffer = await audioBlob.arrayBuffer();
        
        // 使用AudioContext解码音频
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        // 转换为16位PCM WAV格式
        const wavBuffer = audioBufferToWav(audioBuffer);
        
        return new Blob([wavBuffer], { type: 'audio/wav' });
        
    } catch (error) {
        console.error('[音频] WAV转换失败:', error);
        // 如果转换失败，返回原始blob
        return audioBlob;
    }
}

/**
 * 将AudioBuffer转换为WAV格式的ArrayBuffer
 */
function audioBufferToWav(buffer) {
    const length = buffer.length;
    const numberOfChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const arrayBuffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
    const view = new DataView(arrayBuffer);
    const channels = [];
    let offset = 0;
    let pos = 0;
    
    // 写入WAV头部
    const writeString = (str) => {
        for (let i = 0; i < str.length; i++) {
            view.setUint8(pos++, str.charCodeAt(i));
        }
    };
    
    writeString('RIFF');
    view.setUint32(pos, 36 + length * numberOfChannels * 2, true);
    pos += 4;
    writeString('WAVE');
    writeString('fmt ');
    view.setUint32(pos, 16, true);
    pos += 4;
    view.setUint16(pos, 1, true);
    pos += 2;
    view.setUint16(pos, numberOfChannels, true);
    pos += 2;
    view.setUint32(pos, sampleRate, true);
    pos += 4;
    view.setUint32(pos, sampleRate * numberOfChannels * 2, true);
    pos += 4;
    view.setUint16(pos, numberOfChannels * 2, true);
    pos += 2;
    view.setUint16(pos, 16, true);
    pos += 2;
    writeString('data');
    view.setUint32(pos, length * numberOfChannels * 2, true);
    pos += 4;
    
    // 写入音频数据
    for (let i = 0; i < numberOfChannels; i++) {
        channels.push(buffer.getChannelData(i));
    }
    
    while (pos < arrayBuffer.byteLength) {
        for (let i = 0; i < numberOfChannels; i++) {
            let sample = Math.max(-1, Math.min(1, channels[i][offset]));
            sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            view.setInt16(pos, sample, true);
            pos += 2;
        }
        offset++;
    }
    
    return arrayBuffer;
}

/**
 * 将Blob转换为base64
 */
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64data = reader.result.split(',')[1];
            resolve(base64data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

/**
 * 发送文本消息
 */
function sendTextMessage(message) {
    if (!socket || !socket.connected) {
        showError('WebSocket未连接');
        return;
    }
    
    if (!message || !message.trim()) {
        return;
    }
    
    socket.emit('text_message', {
        session_id: sessionId,
        message: message.trim()
    });
    
    console.log('[消息] 已发送:', message);
}

/**
 * 获取对话历史
 */
function getHistory() {
    if (!socket || !socket.connected) {
        showError('WebSocket未连接');
        return;
    }
    
    socket.emit('get_history', {
        session_id: sessionId
    });
}

/**
 * 清空对话历史
 */
function clearHistory() {
    if (!socket || !socket.connected) {
        showError('WebSocket未连接');
        return;
    }
    
    if (confirm('确定要清空对话历史吗？')) {
        socket.emit('clear_history', {
            session_id: sessionId
        });
    }
}

/**
 * 更新录音UI
 */
function updateRecordingUI(recording) {
    const micButton = document.querySelector('.mic-button');
    if (micButton) {
        micButton.classList.toggle('recording', recording);
        micButton.disabled = false;
    }
}

/**
 * 显示识别结果（立即显示，不等待LLM回复）
 */
function displayTranscribedText(text) {
    const chatScroll = document.querySelector('.chat-scroll');
    if (!chatScroll) {
        return;
    }
    
    // 检查是否已经显示（避免重复）
    const lastMessage = chatScroll.lastElementChild;
    const lastContent = lastMessage?.querySelector('p')?.textContent;
    if (lastContent !== text || !lastMessage?.classList.contains('user')) {
        // 立即在聊天窗口中显示用户消息
        addChatMessage('user', text);
        
        // 更新state.chatHistory（如果app-integrated.js可用）
        if (window.state && window.state.chatHistory) {
            // 检查是否已经添加（避免重复）
            const lastHistoryMsg = window.state.chatHistory[window.state.chatHistory.length - 1];
            if (!lastHistoryMsg || lastHistoryMsg.content !== text) {
                window.state.chatHistory.push({ role: 'user', content: text });
            }
        }
    }
}

/**
 * 追加LLM流式内容
 */
let currentLLMMessage = null;
let accumulatedLLMContent = '';

function appendLLMContent(content) {
    const chatScroll = document.querySelector('.chat-scroll');
    if (!chatScroll) {
        console.warn('[LLM] 找不到 .chat-scroll 元素');
        return;
    }
    
    if (!currentLLMMessage) {
        // 创建新的消息元素
        currentLLMMessage = createChatMessage('assistant', '');
        accumulatedLLMContent = '';
        // 立即添加到 DOM，这样流式更新时才能看到
        chatScroll.appendChild(currentLLMMessage);
        scrollToBottom();
    }
    
    // 追加内容
    accumulatedLLMContent += content;
    const contentElement = currentLLMMessage.querySelector('p');
    if (contentElement) {
        contentElement.textContent = accumulatedLLMContent;
        // 滚动到底部
        scrollToBottom();
    } else {
        console.warn('[LLM] 找不到消息内容元素');
    }
}

/**
 * 完成LLM响应（确保内容完整，不重复创建消息，不覆盖流式内容）
 */
function finishLLMResponse(content) {
    const chatScroll = document.querySelector('.chat-scroll');
    
    if (currentLLMMessage) {
        // 如果已经有流式消息，只更新最终内容（确保完整），不覆盖已有内容
        const contentElement = currentLLMMessage.querySelector('p');
        if (contentElement) {
            // 如果提供的内容更长，使用它（确保完整）
            // 否则保持已有的流式内容
            if (content && content.length > accumulatedLLMContent.length) {
                contentElement.textContent = content;
                accumulatedLLMContent = content;
            }
            // 如果内容为空（表示流式完成信号），保持已有内容不变
        } else {
            console.warn('[LLM] 完成时找不到消息内容元素');
        }
        
        // 更新state.chatHistory（如果app-integrated.js可用）
        if (window.state && window.state.chatHistory) {
            // 查找或更新最后一条助手消息
            const lastMsg = window.state.chatHistory[window.state.chatHistory.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
                // 如果提供的内容更长，使用它
                if (content && content.length > lastMsg.content.length) {
                    lastMsg.content = content;
                }
            } else {
                window.state.chatHistory.push({ 
                    role: 'assistant', 
                    content: content || accumulatedLLMContent 
                });
            }
        }
        
        // 重置状态，为下一次响应做准备
        currentLLMMessage = null;
        accumulatedLLMContent = '';
    } else if (chatScroll && content) {
        // 如果没有流式消息（可能是MCP调用后的完整回复），直接创建一个完整消息
        addChatMessage('assistant', content);
        
        // 更新state.chatHistory
        if (window.state && window.state.chatHistory) {
            window.state.chatHistory.push({ role: 'assistant', content: content });
        }
    }
    // 如果content为空且没有流式消息，只发送完成信号，不创建消息
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 添加聊天消息
 */
function addChatMessage(role, content) {
    const messageElement = createChatMessage(role, content);
    const chatScroll = document.querySelector('.chat-scroll');
    if (chatScroll) {
        chatScroll.appendChild(messageElement);
        scrollToBottom();
    }
}

/**
 * 创建聊天消息元素
 */
function createChatMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-bubble ${role}`;
    
    const metaDiv = document.createElement('div');
    metaDiv.className = 'chat-meta';
    metaDiv.textContent = role === 'user' ? '用户' : '助手';
    
    const contentP = document.createElement('p');
    contentP.textContent = content;
    
    messageDiv.appendChild(metaDiv);
    messageDiv.appendChild(contentP);
    
    return messageDiv;
}

/**
 * 显示历史记录
 */
function displayHistory(history) {
    const chatScroll = document.querySelector('.chat-scroll');
    if (!chatScroll) {
        return;
    }
    
    // 清空现有消息和流式消息状态
    chatScroll.innerHTML = '';
    currentLLMMessage = null;
    accumulatedLLMContent = '';
    
    // 显示历史消息
    history.forEach(msg => {
        const role = msg.role === 'user' ? 'user' : 'assistant';
        addChatMessage(role, msg.content);
    });
    
    // 同步到state.chatHistory（如果app-integrated.js可用）
    if (window.state) {
        window.state.chatHistory = history.map(msg => ({
            role: msg.role,
            content: msg.content
        }));
    }
    
    scrollToBottom();
}

/**
 * 清空聊天显示
 */
function clearChatDisplay() {
    const chatScroll = document.querySelector('.chat-scroll');
    if (chatScroll) {
        chatScroll.innerHTML = '';
    }
    
    // 重置流式消息状态
    currentLLMMessage = null;
    accumulatedLLMContent = '';
    
    // 清空state.chatHistory（如果app-integrated.js可用）
    if (window.state) {
        window.state.chatHistory = [];
    }
}

/**
 * 滚动到底部
 */
function scrollToBottom() {
    const chatScroll = document.querySelector('.chat-scroll');
    if (chatScroll) {
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }
}

/**
 * 显示错误消息
 */
function showError(message) {
    console.error('[错误]', message);
    // 可以在这里添加UI错误提示
    alert('错误: ' + message);
}

// 导出函数供其他模块使用
window.chatModule = {
    initWebSocket,
    initAudioRecording,
    startRecording,
    stopRecording,
    sendTextMessage,
    getHistory,
    clearHistory,
    updateRecordingUI,
    addChatMessage, // 导出addChatMessage供外部使用
    displayTranscribedText, // 导出displayTranscribedText供外部使用
    appendLLMContent, // 导出appendLLMContent供外部使用
    finishLLMResponse, // 导出finishLLMResponse供外部使用
    get sessionId() {
        return sessionId;
    },
    get socket() {
        return socket;
    },
    // 回调函数占位符，由外部模块设置
    onConnected: null,
    onLoadingComplete: null,
    onSystemMessage: null
};

