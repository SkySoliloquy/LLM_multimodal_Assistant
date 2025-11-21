/**
 * 主应用入口 - 集成语音对话功能
 * 这是改造后的main.js，集成了语音对话系统
 */
import { uiConfig } from './config.js';
// 注意：chat.js 已在 HTML 中通过 <script> 标签加载，不需要在这里导入
// 如果chatModule未定义，等待一下

const {
  chrome,
  splash,
  iconRegistry,
  formShapes,
  toolset,
  scenes,
  interfaceProfiles,
  thread,
} = uiConfig;

const state = {
  currentScene: 0,
  splashVisible: true,
  splashCompleted: false,
  filters: {
    orchestration: new Set(),
    handoff: new Set(),
  },
  chatHistory: [], // 聊天历史
  systemMessages: [], // 系统消息历史
  isRecording: false, // 录音状态
  isConnected: false, // WebSocket连接状态
};

// 将state暴露给全局，供chat.js使用
window.state = state;

// app 元素将在初始化时获取
let app = null;

/**
 * 初始化应用
 */
function initApp() {
  // 等待DOM加载完成
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initializeAfterLoad();
    });
  } else {
    initializeAfterLoad();
  }
}

/**
 * DOM加载完成后的初始化
 */
function initializeAfterLoad() {
  // 获取 app 元素
  app = document.querySelector('#app');
  
  // 确保 app 元素存在
  if (!app) {
    console.error('[错误] #app 元素不存在');
    return;
  }
  
  console.log('[应用] 开始初始化...');
  
  // 先初始化WebSocket（必须在渲染前，以便在启动界面时能监听加载事件）
  if (window.chatModule) {
    try {
      window.chatModule.initWebSocket();
      console.log('[应用] WebSocket初始化完成');
      
      // 等待 WebSocket 连接建立后再渲染
      const socket = window.chatModule.socket;
      if (socket) {
        // 如果已经连接，直接渲染
        if (socket.connected) {
          renderScene();
        } else {
          // 等待连接后再渲染
          socket.once('connect', () => {
            console.log('[应用] WebSocket已连接，开始渲染场景');
            renderScene();
          });
        }
      } else {
        // 如果 socket 还不存在，延迟渲染
        setTimeout(() => {
          renderScene();
        }, 100);
      }
    } catch (error) {
      console.warn('[警告] chatModule初始化失败:', error);
      renderScene();
    }
  } else {
    console.warn('[警告] chatModule 未加载');
    renderScene();
  }
  
  // 渲染场景（启动界面会监听加载事件）
  // 注意：上面的逻辑已经处理了渲染，这里不再需要
  
  // 绑定事件（延迟绑定，因为DOM可能还没完全渲染）
  setTimeout(() => {
    try {
      bindEvents();
      console.log('[应用] 事件绑定完成');
    } catch (error) {
      console.error('[错误] 事件绑定失败:', error);
    }
    
    // 初始化音频录制（异步，不阻塞渲染）
    if (window.chatModule) {
      window.chatModule.initAudioRecording().then(success => {
        if (success) {
          console.log('[应用] 音频录制初始化成功');
        }
      }).catch(err => {
        console.warn('[应用] 音频录制初始化失败:', err);
      });
      
      // 设置系统消息回调
      window.chatModule.onSystemMessage = (data) => {
        addSystemMessage(data.type, data.message);
      };
    }
  }, 100);
}

/**
 * 绑定事件
 */
function bindEvents() {
  // 录音按钮
  const micButton = document.querySelector('.mic-button');
  if (micButton) {
    micButton.addEventListener('click', () => {
      if (state.isRecording) {
        stopRecording();
      } else {
        startRecording();
      }
    });
  }
  
  // 文本输入
  const textInput = document.querySelector('.chat-input input');
  // 选择发送按钮（.chat-input下最后一个button，不是mic-button）
  const sendButton = document.querySelector('.chat-input button:not(.mic-button)');
  
  if (textInput) {
    textInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && textInput.value.trim()) {
        sendTextMessage(textInput.value.trim());
        textInput.value = '';
      }
    });
  }
  
  if (sendButton) {
    sendButton.addEventListener('click', () => {
      if (textInput && textInput.value.trim()) {
        sendTextMessage(textInput.value.trim());
        textInput.value = '';
      }
    });
    // 确保按钮可点击（移除disabled属性）
    sendButton.disabled = false;
  }
  
  // 清空历史按钮
  const clearHistoryBtn = document.querySelector('.chat-pill');
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', () => {
      if (window.chatModule) {
        window.chatModule.clearHistory();
      }
    });
  }
}

/**
 * 添加系统消息（只更新消息列表部分，不重新渲染整个场景）
 */
function addSystemMessage(type, message) {
  const now = new Date();
  const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
  
  // 根据类型确定标题和角色
  let title = '系统';
  let role = 'system';
  
  if (type === 'tool_call') {
    title = '工具调用';
    role = 'system';
  } else if (type === 'mcp_iteration') {
    title = 'MCP循环';
    role = 'system';
  } else if (type === 'asr') {
    title = '语音识别';
    role = 'system';
  } else   if (type === 'tts') {
    title = '语音合成';
    role = 'system';
  } else if (type === 'mcp_complete') {
    title = 'MCP完成';
    role = 'system';
  } else if (type === 'tool_execution') {
    title = '工具执行';
    role = 'system';
  } else if (type === 'tool_complete') {
    title = '工具完成';
    role = 'system';
  }
  
  const systemMsg = {
    role: role,
    title: title,
    content: message,
    time: timeStr
  };
  
  // 添加到系统消息历史
  state.systemMessages.push(systemMsg);
  
  // 限制消息数量（最多保留50条）
  if (state.systemMessages.length > 50) {
    state.systemMessages.shift();
  }
  
  // 只更新消息列表部分，不重新渲染整个场景
  const messageList = document.querySelector('.message-list');
  if (messageList) {
    const msgLi = document.createElement('li');
    msgLi.className = `msg ${role}`;
    msgLi.innerHTML = `
      <div class="msg-meta">
        <span>${title}</span>
        <time>${timeStr}</time>
      </div>
      <p>${message}</p>
    `;
    messageList.appendChild(msgLi);
    
    // 滚动消息面板到底部
    messageList.scrollTop = messageList.scrollHeight;
  }
}

/**
 * 开始录音
 */
function startRecording() {
  if (window.chatModule) {
    window.chatModule.startRecording();
    state.isRecording = true;
    updateRecordingUI(true);
  }
}

/**
 * 停止录音
 */
function stopRecording() {
  if (window.chatModule) {
    window.chatModule.stopRecording();
    state.isRecording = false;
    updateRecordingUI(false);
  }
}

/**
 * 发送文本消息
 */
function sendTextMessage(message) {
  if (window.chatModule) {
    // 立即显示用户消息（前端预显示）
    const chatScroll = document.querySelector('.chat-scroll');
    if (chatScroll) {
      // 检查是否已经显示（避免重复）
      const lastMessage = chatScroll.lastElementChild;
      const lastContent = lastMessage?.querySelector('p')?.textContent;
      if (lastContent !== message) {
        window.chatModule.addChatMessage('user', message);
        // 添加到聊天历史（避免重复）
        const lastHistoryMsg = state.chatHistory[state.chatHistory.length - 1];
        if (!lastHistoryMsg || lastHistoryMsg.content !== message) {
          state.chatHistory.push({ role: 'user', content: message });
        }
      }
    }
    
    // 发送到后端
    window.chatModule.sendTextMessage(message);
  }
}

/**
 * 更新录音UI
 */
function updateRecordingUI(recording) {
  const micButton = document.querySelector('.mic-button');
  if (micButton) {
    micButton.classList.toggle('recording', recording);
    micButton.innerHTML = recording 
      ? '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.2"/><circle cx="12" cy="12" r="6" fill="currentColor"/></svg>'
      : '<svg viewBox="0 0 24 24"><rect x="9" y="4" width="6" height="10" rx="3" ry="3" fill="currentColor" /><path d="M12 14v4m-3 0h6m-9-7a6 6 0 0 0 12 0" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>';
  }
}

/**
 * 添加聊天消息（委托给chat.js的addChatMessage函数，避免重复实现）
 */
function addChatMessage(role, content) {
  // 委托给chat.js的addChatMessage函数，避免重复实现
  if (window.chatModule && typeof window.chatModule.addChatMessage === 'function') {
    window.chatModule.addChatMessage(role, content);
  } else {
    // 如果chat.js未加载，使用本地实现
    const chatScroll = document.querySelector('.chat-scroll');
    if (!chatScroll) {
      return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-bubble ${role}`;
    
    const metaDiv = document.createElement('div');
    metaDiv.className = 'chat-meta';
    metaDiv.textContent = role === 'user' ? '用户' : '助手';
    
    const contentP = document.createElement('p');
    contentP.textContent = content;
    
    messageDiv.appendChild(metaDiv);
    messageDiv.appendChild(contentP);
    
    chatScroll.appendChild(messageDiv);
    scrollToBottom();
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
 * 渲染场景
 */
const renderScene = () => {
  const scene = scenes[state.currentScene];
  const profile = interfaceProfiles[scene.id];
  const activeFilters = state.filters[scene.id];

  const formsMarkup = formShapes
    .map(
      ({ id, icon, label }) => `
        <button
          type="button"
          class="form-button ${profile.form === id ? 'is-active' : ''}"
          data-shape="${id}"
          title="${label}"
          aria-label="${label}"
        >
          ${icon}
        </button>
      `,
    )
    .join('');

  const toolsMarkup = toolset
    .map(
      (tool) => `
        <li class="${profile.tool === tool ? 'is-active' : ''}">
          <span class="tool-dot"></span>
          <span>${tool}</span>
        </li>
      `,
    )
    .join('');

  // 使用实际的聊天历史
  const chatMarkup = state.chatHistory
    .map(
      (msg) => `
        <div class="chat-bubble ${msg.role}">
          <div class="chat-meta">${msg.role === 'user' ? '用户' : '助手'}</div>
          <p>${msg.content}</p>
        </div>
      `,
    )
    .join('');

  // 使用实际的系统消息历史
  const threadMarkup = (state.systemMessages || [])
    .map(
      (msg) => `
        <li class="msg ${msg.role}">
          <div class="msg-meta">
            <span>${msg.title}</span>
            <time>${msg.time}</time>
          </div>
          <p>${msg.content}</p>
        </li>
      `,
    )
    .join('');

  const showSplash = state.splashVisible;
  const showMain = !showSplash;

  const splashLeftTicks = splash.leftScale.ticks.map((tick) => `<span>${tick}</span>`).join('');
  const splashRightTicks = splash.rightScale.ticks.map((tick) => `<span>${tick}</span>`).join('');

  const splashLayer = showSplash
    ? `
      <div class="hud-splash">
        <div class="splash-backdrop"></div>
        <div class="splash-cloud cloud-a"></div>
        <div class="splash-cloud cloud-b"></div>
        <div class="splash-grid"></div>
        <div class="splash-status">${splash.status}</div>
        <div class="splash-caption caption-top">${splash.heroLabel}</div>
        <div class="splash-caption caption-bottom">
          ${splash.caption}
        </div>
        <div class="splash-scale scale-left">
          <span class="label">${splash.leftScale.label}</span>
          <div class="ticks">
            ${splashLeftTicks}
          </div>
        </div>
        <div class="splash-scale scale-right">
          <span class="label">${splash.rightScale.label}</span>
          <span class="sub">${splash.rightScale.sub}</span>
          <div class="ticks">
            ${splashRightTicks}
          </div>
        </div>
        <div class="splash-ring ring-alpha"></div>
        <div class="splash-ring ring-beta"></div>
        <div class="splash-ring ring-gamma"></div>
        <div class="splash-core">
          <div class="emblem">
            <span></span>
            <span></span>
          </div>
          <span class="pulse-dot"></span>
          <span class="crosshair"></span>
        </div>
        <div class="splash-scan"></div>
        <div class="splash-beam"></div>
      </div>
    `
    : '';

  const mainLayer = showMain
    ? `
      <div class="surface fade-in">
        <header class="ui-header">
          <div class="ui-date">
            <span>${chrome.date.day}</span>
            <span>${chrome.date.full}</span>
          </div>
          <div class="ui-brand">${chrome.brand}</div>
          <div class="ui-year">${chrome.year}</div>
        </header>
        <div class="ui-grid">
          <aside class="panel panel-left">
            <div class="panel-section">
              <div class="section-title">Forms</div>
              <div class="forms-bar">
                ${formsMarkup}
              </div>
            </div>
            <div class="panel-section">
              <div class="section-title">Tools</div>
              <ul class="tool-list">
                ${toolsMarkup}
              </ul>
            </div>
          </aside>
          <section class="center-panel">
            <div class="canvas" data-scene="${scene.id}">
              <div class="visual-pane">
                <div class="radar" data-scene="${scene.id}" style="--accent: ${scene.accent};">
                  <div class="ring ring-1"></div>
                  <div class="ring ring-2"></div>
                  <div class="ring ring-3"></div>
                  <div class="halo"></div>
                  <button class="core" type="button" aria-label="切换模式">
                    <div class="logo">
                      <span class="bubble primary"></span>
                      <span class="bubble secondary"></span>
                    </div>
                  </button>
                  <div class="orbit-layer">
                    ${scene.nodes
                      .map((node) => {
                        const radius = node.ring === 'inner' ? 120 : 165;
                        const speed = node.speed ?? (node.ring === 'inner' ? 11 : 15);
                        const delay = ((-node.angle || 0) / 360) * speed;
                        const hidden = activeFilters.has(node.label);

                        return `
                          <div
                            class="orbital${hidden ? ' is-hidden' : ' is-visible'}"
                            data-label="${node.label}"
                            style="--radius: ${radius}px; --speed: ${speed}s; animation-delay: ${delay}s;"
                            aria-hidden="${hidden}"
                          >
                            <span class="track"></span>
                            <div class="chip-icon" style="--chip-color: ${node.color};">
                              ${iconRegistry[node.icon]}
                            </div>
                          </div>
                        `;
                      })
                      .join('')}
                  </div>
                </div>
              </div>
            </div>
            <div class="scene-core scene-core--palette">
              <div class="scene-core__head">
                <span>${chrome.paletteLabel}</span>
                <button class="add-service" type="button" aria-label="Add MCP Service">Add</button>
              </div>
              <div class="chip-palette">
                ${scene.nodes
                  .map(
                    (node) => `
                      <button
                        type="button"
                        class="palette-item ${activeFilters.has(node.label) ? 'is-muted' : 'is-active'}"
                        data-label="${node.label}"
                        style="--chip-color:${node.color};"
                        aria-pressed="${!activeFilters.has(node.label)}"
                      >
                        <div class="palette-label">
                          <span>${node.label}</span>
                          <div class="chip-icon">
                            ${iconRegistry[node.icon]}
                          </div>
                        </div>
                      </button>
                    `,
                  )
                  .join('')}
              </div>
            </div>
          </section>
          <aside class="panel panel-right">
            <section class="chat-window">
              <header>
                <div>
                  <span>${chrome.chatPanel.title}</span>
                  <small>${chrome.chatPanel.subtitle}</small>
                </div>
                <button type="button" class="chat-pill">清空</button>
              </header>
              <div class="chat-scroll">
                ${chatMarkup}
              </div>
              <div class="chat-input">
                <button type="button" class="mic-button" aria-label="开始录音">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="9" y="4" width="6" height="10" rx="3" ry="3" fill="currentColor" />
                    <path
                      d="M12 14v4m-3 0h6m-9-7a6 6 0 0 0 12 0"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.6"
                      stroke-linecap="round"
                    />
                  </svg>
                </button>
                <input type="text" placeholder="${chrome.chatPanel.inputPlaceholder}" />
                <button type="button">→</button>
              </div>
            </section>
            <section class="message-panel">
              <div class="message-card">
                <header>
                  <span>${chrome.messagePanel.title}</span>
                  <span class="indicator">${chrome.messagePanel.indicator}</span>
                </header>
                <ul class="message-list">
                  ${threadMarkup}
                </ul>
              </div>
            </section>
          </aside>
        </div>
        <footer class="ui-footer">
          <span>${chrome.footer[0]}</span>
          <span>${chrome.footer[1]}</span>
        </footer>
      </div>
    `
    : '';

  app.innerHTML = `${splashLayer}${mainLayer}`;

  // 重新绑定事件（因为DOM被重新创建）
  bindEvents();

  if (showMain) {
    app.querySelector('.core').addEventListener('click', () => {
      state.currentScene = (state.currentScene + 1) % scenes.length;
      renderScene();
    });

    const palette = app.querySelector('.chip-palette');
    palette.addEventListener('click', (event) => {
      const button = event.target.closest('.palette-item');
      if (!button) return;
      const label = button.dataset.label;
      let nowHidden;
      if (activeFilters.has(label)) {
        activeFilters.delete(label);
        nowHidden = false;
      } else {
        activeFilters.add(label);
        nowHidden = true;
      }

      button.classList.toggle('is-muted', nowHidden);
      button.classList.toggle('is-active', !nowHidden);
      button.setAttribute('aria-pressed', (!nowHidden).toString());

      const orbitChips = app.querySelectorAll(`.orbit-layer .orbital[data-label="${label}"]`);
      orbitChips.forEach((orbit) => {
        orbit.classList.toggle('is-hidden', nowHidden);
        orbit.classList.toggle('is-visible', !nowHidden);
        orbit.setAttribute('aria-hidden', nowHidden);
      });
    });
  }

  const splashElement = showSplash ? app.querySelector('.hud-splash') : null;
  if (showSplash && splashElement) {
    requestAnimationFrame(() => splashElement.classList.add('animate-in'));
    
    // 更新启动界面状态显示
    const updateSplashStatus = (text) => {
      const statusEl = splashElement.querySelector('.splash-status');
      if (statusEl) {
        statusEl.textContent = text;
      }
    };
    
    // 开始加载系统
    if (window.chatModule && window.chatModule.socket) {
      const socket = window.chatModule.socket;
      
      // 防止重复触发
      let loadingCompleted = false;
      let lastProgress = 0;
      
      // 统一的完成处理函数
      const handleLoadingComplete = (reason = '') => {
        if (loadingCompleted) {
          console.log('[加载] 已经完成，忽略重复事件:', reason);
          return;
        }
        loadingCompleted = true;
        console.log('[加载] 系统加载完成' + (reason ? ` (${reason})` : ''));
        updateSplashStatus('加载完成');
        clearTimeout(loadingTimeout);
        // 立即响应，无延迟
        dismissSplash();
      };
      
      // 监听加载进度
      const progressHandler = (data) => {
        // 如果已经完成，忽略所有进度消息（防止旧消息覆盖）
        if (loadingCompleted) {
          console.log('[加载] 已完成，忽略进度消息:', data.step, data.progress + '%');
          return;
        }
        
        // 忽略小于当前进度的消息（防止旧消息覆盖新进度）
        if (data.progress < lastProgress && lastProgress > 50) {
          console.log('[加载] 忽略旧的进度消息:', data.step, data.progress + '% (当前进度: ' + lastProgress + '%)');
          return;
        }
        
        console.log('[加载进度]', data.step, data.progress + '%');
        lastProgress = Math.max(lastProgress, data.progress); // 确保进度只增不减
        updateSplashStatus(`${data.step}... ${Math.round(data.progress)}%`);
        
        // 加载完成，立即响应，不等待其他事件
        if (data.is_complete || data.progress >= 100) {
          handleLoadingComplete('进度100%');
        }
      };
      
      // 监听加载完成事件
      const completeHandler = () => {
        handleLoadingComplete('complete事件');
      };
      
      // 监听错误事件
      const errorHandler = (data) => {
        console.error('[加载错误]', data.error);
        // 即使出现错误，如果是MCP相关的，仍然可以继续
        if (data.error && (data.error.includes('MCP') || data.error.includes('async'))) {
          console.warn('[警告] 非关键错误，系统仍可使用');
          handleLoadingComplete('非关键错误');
        } else {
          updateSplashStatus('加载失败: ' + (data.error || '未知错误'));
        }
      };
      
      // 注册事件监听器（每次重连都重新注册）
      socket.on('loading_progress', progressHandler);
      socket.on('loading_complete', completeHandler);
      socket.on('loading_error', errorHandler);
      
      // 设置连接成功回调
      if (window.chatModule) {
        window.chatModule.onConnected = () => {
          console.log('[加载] WebSocket连接成功，检查会话状态');
          // 如果还没完成，立即发送加载请求（后端会检查会话是否已存在）
          if (!loadingCompleted) {
            socket.emit('start_loading', {
              session_id: window.chatModule.sessionId || 'default'
            });
          }
        };
        
        // 设置加载完成回调
        window.chatModule.onLoadingComplete = (data) => {
          console.log('[加载] 通过回调收到加载完成事件:', data);
          handleLoadingComplete('连接时已加载');
        };
      }
      
      // 如果 WebSocket 重连，重新注册监听器
      socket.on('reconnect', () => {
        console.log('[WebSocket] 重连成功，重新注册事件监听器');
        socket.off('loading_progress', progressHandler);
        socket.off('loading_complete', completeHandler);
        socket.off('loading_error', errorHandler);
        socket.on('loading_progress', progressHandler);
        socket.on('loading_complete', completeHandler);
        socket.on('loading_error', errorHandler);
        // 重连后如果还没完成，立即检查状态
        if (!loadingCompleted) {
          // 立即发送加载请求（后端会检查会话是否已存在并立即返回）
          socket.emit('start_loading', {
            session_id: window.chatModule.sessionId || 'default'
          });
        }
      });
      
      // 在连接时也监听加载完成（可能连接时就已经完成了）
      socket.once('loading_complete', () => {
        if (!loadingCompleted) {
          console.log('[加载] 在连接时收到 loading_complete 事件');
          handleLoadingComplete('连接时已加载');
        }
      });
      
      // 添加超时保护：如果60秒后还没有加载完成，自动进入
      let loadingTimeout = setTimeout(() => {
        if (!loadingCompleted && lastProgress < 100) {
          console.warn('[警告] 加载超时，强制进入主界面');
          updateSplashStatus('加载超时，尝试进入主界面...');
          handleLoadingComplete('超时');
        }
      }, 60000); // 减少到60秒超时
      
      // 如果 socket 已经连接，立即检查状态
      if (socket.connected) {
        // 立即发送加载请求（后端会检查会话是否已存在）
        socket.emit('start_loading', {
          session_id: window.chatModule.sessionId || 'default'
        });
        updateSplashStatus('正在检查系统状态...');
      } else {
        // 等待连接后再发送
        socket.once('connect', () => {
          // 连接后立即检查状态
          socket.emit('start_loading', {
            session_id: window.chatModule.sessionId || 'default'
          });
          updateSplashStatus('正在检查系统状态...');
        });
        updateSplashStatus('正在连接服务器...');
      }
    } else {
      // 如果没有WebSocket，延迟后自动进入
      console.warn('[警告] WebSocket未连接，将在3秒后自动进入');
      updateSplashStatus('正在连接服务器...');
      setTimeout(() => {
        dismissSplash();
      }, 3000);
    }
    
    const dismissSplash = () => {
      if (state.splashCompleted) {
        console.log('[加载] dismissSplash 已调用，忽略重复调用');
        return;
      }
      state.splashCompleted = true;
      console.log('[加载] 开始退出启动界面');
      splashElement.classList.add('fade-out');
      // 减少淡出时间，加快响应
      setTimeout(() => {
        splashElement.classList.add('is-hidden');
        state.splashVisible = false;
        renderScene();
      }, 500); // 从900ms减少到500ms
    };
  }
};

// 启动应用
// 确保DOM已加载且app元素存在
function startApp() {
  const appElement = document.querySelector('#app');
  if (!appElement) {
    console.error('[错误] #app 元素不存在');
    setTimeout(startApp, 100);
    return;
  }
  
  console.log('[应用] DOM已准备，开始初始化...');
  initApp();
}

// 在模块加载时立即尝试启动
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startApp);
} else {
  // DOM 已经加载完成
  startApp();
}

