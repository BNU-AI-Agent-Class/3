# 译途星球 · 前端

纯静态 HTML 聊天界面，暗色星空主题，适配凌晨使用场景。

## 本地运行

直接用浏览器打开 `index.html` 即可。

或者用 Python 起一个静态服务器：

```bash
cd frontend
python -m http.server 3000
```

然后访问 http://localhost:3000

## 代码说明

- **无 key**：整个前端没有任何 API key，只通过 `fetch` 调后端 `/api/chat`
- **危机按钮**：右上角红色的"我需要帮助"按钮，一键发送危机求助
- **优雅降级**：后端连不上时显示兜底话术 + 求助热线，绝不白屏
- **三步流程**：入口选择 → GAD-7 自检（可选）/ 标签重构 → AI 师姐对话
- **暗色设计**：深蓝 + 星空背景，适配凌晨被窝里使用
- **响应式**：适配手机和电脑

## 部署到 GitHub Pages

1. 在 GitHub 上建一个新仓库（可以叫 `yitu-planet`）
2. push `frontend/index.html`（可以直接放在仓库根目录或 docs/ 目录）
3. Settings → Pages → Source: main branch, 选 `/ (root)` → Save
4. 等几分钟，拿到 `https://你的用户名.github.io/yitu-planet/` 地址
5. 上线前务必把 `BACKEND` 常量改成你的 Railway 域名

## 上线前安全检查

```bash
# 确保前端没有任何 key 泄漏
grep -i "sk-" index.html    # 必须为空！
grep -i "api.key" index.html  # 必须为空！
grep -i "openrouter" index.html  # 应该只在注释中出现
```
