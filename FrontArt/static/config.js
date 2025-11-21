export const uiConfig = {
  chrome: {
    date: {
      day: '2025年',
      full: '11月14日',
    },
    brand: 'Mory',
    year: '2025',
    paletteLabel: 'MCP Server',
    footer: ['END IS UI', '013'],
    messagePanel: {
      title: '消息控制台',
      indicator: 'Live',
      inputHint: '···',
    },
    chatPanel: {
      title: 'LLM 会话',
      subtitle: '',
      inputPlaceholder: '输入消息...',
      messages: [
        { role: 'user', content: '请汇总当前多渠道的响应速度。' },
        { role: 'assistant', content: '平均响应 2.4s，WhatsApp 最快，Email 最慢。' },
        { role: 'user', content: '若延迟 > 3s 时请自动切换备用 MCP。' },
        { role: 'assistant', content: '已设置 SLA 预警阈值为 3s，并同步备用路由。' },
        { role: 'user', content: '继续记录最近 5 分钟的用户反馈关键字。' },
        { role: 'assistant', content: '关键词包括：退款、无法连接、语音识别、延迟。' },
      ],
    },
  },
  splash: {
    status: '系统加载中...',
    heroLabel: 'FLYDRONE HUD',
    caption: 'NAVIGATION MODE SET TO AUTOMATIC · SWITCH TO MANUAL IF NECESSARY · SYNC SWITCHES A1 & A2',
    leftScale: {
      label: 'FLYDRONE · V1.6',
      ticks: ['350', '300', '250', '200', '150', '100', '50'],
    },
    rightScale: {
      label: 'LOCATION · 65°',
      sub: 'ALT · 153M',
      ticks: ['90', '120', '150', '180', '210', '240'],
    },
  },
  iconRegistry: {
    messenger: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="currentColor"
          d="M12 2.1A9.9 9.9 0 0 0 2 11.6c0 2.9 1.2 5.3 3.2 7a.9.9 0 0 1 .3.8l-.2 2c0 .6.6 1 1.2.7l2.4-1.1a1.5 1.5 0 0 1 1-.1c.6.1 1.2.2 1.9.2a9.9 9.9 0 1 0 0-19.9Z"
          opacity=".15"
        />
        <path
          fill="currentColor"
          d="M10.9 11.6 7.4 7.9 4 13.1l6-3.6 3.5 3.7 3.4-5.3-6 3.7Z"
        />
      </svg>
    `,
    email: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="6" width="18" height="12" rx="2" ry="2" opacity=".2" fill="currentColor" />
        <path
          d="M4 7.2 12 12l8-4.8"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    `,
    whatsapp: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="currentColor"
          d="M12 3.1a8.9 8.9 0 0 0-7.6 13.6L3.8 21l4.4-1.4A8.9 8.9 0 1 0 12 3.1Z"
          opacity=".2"
        />
        <path
          fill="currentColor"
          d="M10.3 7.5 9 7a.6.6 0 0 0-.9.4c-.3 1.3-.1 3 .6 4.3.8 1.3 2 2.4 3.4 3 .8.4 1.6.6 2.4.6.4 0 .7-.2.9-.6l.5-1.2a.6.6 0 0 0-.3-.8l-1.8-.7a.6.6 0 0 0-.7.2l-.3.4c-.2.2-.4.3-.7.2a4.6 4.6 0 0 1-2.6-2.6c-.1-.3 0-.5.2-.7l.3-.4c.2-.2.2-.5 0-.7l-.7-1.5a.6.6 0 0 0-.5-.4Z"
        />
      </svg>
    `,
    instagram: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4" y="4" width="16" height="16" rx="4" ry="4" opacity=".2" fill="currentColor" />
        <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2" />
        <circle cx="17" cy="7" r="1" fill="currentColor" />
      </svg>
    `,
    chat: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M5 5h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-4.2L9 21v-5H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"
          fill="currentColor"
          opacity=".2"
        />
        <path
          d="M8 10h8M8 13h5"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
    `,
    voice: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="8" y="4" width="8" height="12" rx="4" ry="4" fill="currentColor" opacity=".2" />
        <path
          d="M12 18v3M8 12a4 4 0 0 0 8 0M6 12h2m8 0h2"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
    `,
  },
  formShapes: [
    {
      id: 'cube',
      label: 'Cube',
      icon: `
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <rect x="9" y="9" width="14" height="14" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="1.5" />
          <path d="M9 14h14" stroke="currentColor" stroke-width="1.5" opacity="0.6" />
          <path d="M16 9v14" stroke="currentColor" stroke-width="1.5" opacity="0.6" />
        </svg>
      `,
    },
    {
      id: 'sphere',
      label: 'Sphere',
      icon: `
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <circle cx="16" cy="16" r="10" fill="none" stroke="currentColor" stroke-width="1.5" />
          <ellipse cx="16" cy="16" rx="10" ry="4.5" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5" />
        </svg>
      `,
    },
    {
      id: 'cone',
      label: 'Cone',
      icon: `
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <path d="M8 24h16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          <path d="M8 24 16 8l8 16" fill="none" stroke="currentColor" stroke-width="1.5" />
        </svg>
      `,
    },
    {
      id: 'cylinder',
      label: 'Cylinder',
      icon: `
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <rect x="10" y="9" width="12" height="14" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="1.5" />
          <ellipse cx="16" cy="9" rx="6" ry="2.5" fill="none" stroke="currentColor" stroke-width="1.2" />
          <ellipse cx="16" cy="23" rx="6" ry="2.5" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5" />
        </svg>
      `,
    },
    {
      id: 'array',
      label: 'Array',
      icon: `
        <svg viewBox="0 0 32 32" aria-hidden="true">
          <circle cx="10" cy="12" r="2" fill="currentColor" />
          <circle cx="16" cy="12" r="2" fill="currentColor" opacity="0.75" />
          <circle cx="22" cy="12" r="2" fill="currentColor" opacity="0.5" />
          <circle cx="10" cy="20" r="2" fill="currentColor" opacity="0.9" />
          <circle cx="16" cy="20" r="2" fill="currentColor" opacity="0.6" />
          <circle cx="22" cy="20" r="2" fill="currentColor" opacity="0.4" />
        </svg>
      `,
    },
  ],
  toolset: ['主界面','语音模式','记忆库',"配置"],
  scenes: [
    {
      id: 'orchestration',
      label: '全渠道编排',
      headline: 'LLM 语音助手调度 MCP 服务，实现多触点协同。',
      description:
        '一次语音请求即可唤起客服机器人、社交媒体、邮件和WhatsApp接力，实时同步上下游状态。',
      accent: '#2563eb',
      core: '语音助手负责跟踪客户上下文，将指令拆分成多个 MCP 工具调用实施闭环。',
      nodes: [
        { label: 'Messenger', icon: 'messenger', color: '#8b5cf6', ring: 'outer', angle: 10 },
        { label: 'Email', icon: 'email', color: '#38bdf8', ring: 'outer', angle: 70 },
        { label: 'WhatsApp', icon: 'whatsapp', color: '#22c55e', ring: 'outer', angle: 135 },
        { label: 'Instagram', icon: 'instagram', color: '#fb7185', ring: 'outer', angle: 200 },
        { label: 'Voice Bot', icon: 'voice', color: '#fbbf24', ring: 'inner', angle: 290 },
        { label: 'Help Desk', icon: 'chat', color: '#0ea5e9', ring: 'inner', angle: 245 },
        { label: 'Slack Bot', icon: 'chat', color: '#7dd3fc', ring: 'inner', angle: 320 },
        { label: 'CRM Sync', icon: 'email', color: '#f87171', ring: 'outer', angle: 255 },
      ],
    },
    {
      id: 'handoff',
      label: '人机协作',
      headline: 'MCP 服务动态切换，保障人工与语音助手无缝衔接。',
      description:
        '语音助手先完成信息采集，再将有效上下文交给人工座席或知识库工具，保持客户体验连贯。',
      accent: '#7c3aed',
      core: '助手依据 SLA 自动在 MCP 工具间切换，必要时触发人工托管并同步所有渠道。',
      nodes: [
        { label: '语音表单', icon: 'voice', color: '#fbbf24', ring: 'inner', angle: 330 },
        { label: '客服机器人', icon: 'chat', color: '#0ea5e9', ring: 'inner', angle: 270 },
        { label: 'Messenger', icon: 'messenger', color: '#8b5cf6', ring: 'outer', angle: 30 },
        { label: '邮箱', icon: 'email', color: '#38bdf8', ring: 'outer', angle: 95 },
        { label: '社媒DM', icon: 'instagram', color: '#fb7185', ring: 'outer', angle: 170 },
        { label: 'WhatsApp', icon: 'whatsapp', color: '#22c55e', ring: 'outer', angle: 230 },
        { label: 'FAQ Agent', icon: 'chat', color: '#60a5fa', ring: 'inner', angle: 205 },
        { label: 'Audit Log', icon: 'email', color: '#a855f7', ring: 'outer', angle: 350 },
      ],
    },
  ],
  interfaceProfiles: {
    orchestration: {
      form: 'cube',
      tool: 'Rotation',
      brightness: 0.68,
      shadow: 0.32,
    },
    handoff: {
      form: 'sphere',
      tool: 'Texture',
      brightness: 0.45,
      shadow: 0.6,
    },
  },
  thread: [], // 清空示例数据，改为实时系统消息
};

