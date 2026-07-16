# 译途星球 · 后端

把 mini Claude Code harness 包成 FastAPI Web 服务，供前端调用。

## 本地运行

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（可选但推荐）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 OPENROUTER_API_KEY

# 5. 启动服务
uvicorn main:app --reload --port 8000
```

然后访问 http://localhost:8000/api/health 确认后端已启动。

## 架构说明

- **Harness 内核**：基于 1_claude_code_basic 的 c5_guard.py（JSON 工具循环 + 工具箱 + 子 agent 复核 + 权限门）
- **危机护栏**：`is_crisis()` 确定性关键词匹配（入口）+ `safety_review()` 子 agent 复核（出口）——双重保险
- **白名单工具**：5 个领域安全工具（tag_reconstruct / match_careers / get_company / get_story / gad7_score），无 bash/rm 等危险工具
- **优雅降级**：模型不可用时返回 FALLBACK 话术，绝不 500

## 部署到 Railway

1. GitHub 上建仓库，push 代码
2. Railway 新建项目 → Deploy from GitHub repo
3. 设置环境变量：`OPENROUTER_API_KEY`、`MODEL`、`CORS_ORIGINS`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. 拿到 `.up.railway.app` 域名
