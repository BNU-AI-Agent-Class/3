# 译途星球 🪐

> **翻译的路上，你不是一个人。**
>
> 一颗接住英专生深夜焦虑的小星球。先接住情绪，再翻译能力，最后给一个最小可执行动作。
> 不是招聘网站，不是测评工具，是你的温柔 AI 师姐。

---

## 这是什么

译途星球是一个面向大四语言学/翻译专业学生的 AI 陪伴工具。当用户在深夜因求职方向迷茫而焦虑时，小星（AI 师姐）会：

1. **先接住情绪** — 不强迫测评，入口自由选择
2. **再翻译能力** — 把"字幕组""追星""写同人文"翻译成职场竞争力
3. **最后给最小动作** — 3-5 个匹配方向 + 女性友好企业 + 三步可执行任务

---

## 项目结构

```
译途星球/
├── backend/               # Python FastAPI 后端
│   ├── main.py            # Harness + /api/chat 入口
│   ├── agent.md           # 小星人设（系统提示）
│   ├── skills/            # 5 个技能文件（危机转介置顶）
│   │   ├── skill_危机转介.md
│   │   ├── skill_情绪自检.md
│   │   ├── skill_能力重构.md
│   │   ├── skill_职业匹配.md
│   │   └── skill_师姐访谈.md
│   ├── data/              # 静态数据
│   │   ├── tag_mapping.json    # 标签→能力→赛道映射
│   │   ├── companies.json      # 女性友好企业库
│   │   ├── gad7.json           # GAD-7 量表
│   │   └── career_stories.json # 师姐访谈
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/              # 纯静态 HTML 前端
│   └── index.html         # 聊天界面（暗色 + 星空背景）
└── README.md              # 这个文件
```

---

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置 Key

编辑 `backend/.env`，填入 OpenRouter API Key（已预填）。

### 3. 启动后端

```bash
cd backend
uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/api/health 确认后端已启动。

### 4. 打开前端

直接在浏览器打开 `frontend/index.html`。

或者用 Python 起一个静态服务器：

```bash
cd frontend
python -m http.server 3000
```

然后访问 http://localhost:3000

---

## 安全设计（三条红线）

| 红线 | 实现 |
|---|---|
| **Key 不进前端** | `index.html` 里没有任何 key，只调 `/api/chat` |
| **危机代码兜底** | `is_crisis()` 确定性关键词匹配（入口 + 出口双重拦截）+ c3 子 agent 安全复核 |
| **不上线 = 没 impact** | 前端 → GitHub Pages / 后端 → Railway |

---

## 部署路径

### 前端 → GitHub Pages

1. 在 GitHub 建仓库，push `frontend/index.html`
2. Settings → Pages → Source: main branch → Save
3. 拿到 `https://你的用户名.github.io/仓库名/` 地址

### 后端 → Railway

1. 在 GitHub 建仓库，push `backend/` 代码
2. Railway 新建项目 → Deploy from GitHub repo
3. 设置环境变量：`OPENROUTER_API_KEY`、`MODEL`、`CORS_ORIGINS`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. 拿到 `.up.railway.app` 域名后，改 `frontend/index.html` 里的 `BACKEND` 常量

---

## 技术架构

```
浏览器 (index.html) ──fetch──> FastAPI (/api/chat) ──httpx──> OpenRouter (Claude)
      │                              │
      │  ✅ 危机按钮                 │  ✅ is_crisis() 入口拦截
      │  ✅ 优雅降级                 │  ✅ safety_review() 出口复核
      │  ✅ 无 key                  │  ✅ 白名单工具（无 bash）
                                    │  ✅ FALLBACK 优雅降级
```

---

## PRD 对应

本项目基于 T1-T5 DEFINE 设计卡实施：

- T1 选题·域分析卡 → 产品定位
- T2 用户画像 → 林雨欣凌晨场景设计
- T3 需求与旅程 → 入口选择 + GAD-7 + 能力重构 + 退场
- T4 PRD 与边界 → 红黄绿数据分级 + 危机护栏
- T5 DEFINE 设计卡 → 小星人设 + 工作流 + 记忆

---

*基于 Dev_depoly_guide 的 Build+Ship 双支柱构建。*
