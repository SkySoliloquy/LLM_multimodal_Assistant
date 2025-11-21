import { uiConfig } from './config.js';

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
};

const app = document.querySelector('#app');

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

  const threadMarkup = thread
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

  const chatMarkup = chrome.chatPanel.messages
    .map(
      (msg) => `
        <div class="chat-bubble ${msg.role}">
          <div class="chat-meta">${msg.role === 'user' ? 'User' : 'LLM'}</div>
          <p>${msg.content}</p>
        </div>
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
                <button type="button" class="chat-pill">记录</button>
              </header>
              <div class="chat-scroll">
                ${chatMarkup}
              </div>
              <div class="chat-input">
                <button type="button" class="mic-button" aria-label="开始录音" disabled>
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
                <input type="text" placeholder="${chrome.chatPanel.inputPlaceholder}" disabled />
                <button type="button" disabled>→</button>
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
    const dismissSplash = () => {
      if (state.splashCompleted) return;
      state.splashCompleted = true;
      splashElement.classList.add('fade-out');
      setTimeout(() => {
        splashElement.classList.add('is-hidden');
        state.splashVisible = false;
        renderScene();
      }, 900);
      window.removeEventListener('click', dismissSplash);
      window.removeEventListener('keydown', keyHandler);
    };
    const keyHandler = (evt) => {
      if (evt.key.toLowerCase() === 'enter' || evt.key.toLowerCase() === ' ') {
        dismissSplash();
      }
    };
    window.addEventListener('click', dismissSplash);
    window.addEventListener('keydown', keyHandler);
  }
};

renderScene();

