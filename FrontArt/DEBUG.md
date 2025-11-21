# 调试说明

## 页面空白问题排查

如果页面显示空白，请按以下步骤排查：

### 1. 检查浏览器控制台
打开浏览器开发者工具（F12），查看 Console 标签，看是否有 JavaScript 错误。

### 2. 检查文件加载
在 Network 标签中，确认以下文件都成功加载：
- `/static/config.js` - 应该返回 200
- `/static/chat.js` - 应该返回 200
- `/static/app-integrated.js` - 应该返回 200
- `/static/style.css` - 应该返回 200

### 3. 检查常见错误

#### 错误：`chatModule is not defined`
**原因**：`chat.js` 还没有加载完成
**解决**：确保 `chat.js` 在 HTML 中的加载顺序在 `app-integrated.js` 之前

#### 错误：`config is not defined` 或 `Cannot access 'uiConfig' before initialization`
**原因**：`config.js` 加载失败或模块导入问题
**解决**：检查 `config.js` 是否使用正确的 ES6 模块导出

#### 错误：`Cannot read property 'querySelector' of null`
**原因**：在 DOM 加载完成前就尝试查询元素
**解决**：确保代码在 `DOMContentLoaded` 事件之后执行

### 4. 手动测试

在浏览器控制台中运行以下代码来测试各个模块：

```javascript
// 测试 config
console.log('config:', window.uiConfig || '未加载');

// 测试 chatModule
console.log('chatModule:', window.chatModule || '未加载');

// 测试 app 元素
console.log('app元素:', document.querySelector('#app'));

// 手动初始化（如果自动初始化失败）
if (window.chatModule) {
  window.chatModule.initWebSocket();
}
```

### 5. 临时解决方案

如果问题持续，可以尝试：
1. 清除浏览器缓存（Ctrl+Shift+Delete）
2. 硬刷新页面（Ctrl+F5）
3. 检查 Flask 日志中是否有错误信息

