# 灵语 (LingYu) — 智能语音输入法

语音输入法实训项目 — 颖之妙想队
#DEMO演示视频：
#【灵语-AI语音识别-七牛云实训demo演示】 https://www.bilibili.com/video/BV1TWGo6ME76/?share_source=copy_web&vd_source=a69773f6e405918d5afbb8c3397a1e1e

**灵语**是一款基于 AI 的智能语音输入法桌面应用。支持 SenseVoice 离线语音识别、DeepSeek 大模型场景化文本润色、行业词库纠错，采用 Electron + Python FastAPI 混合架构，在 Windows 桌面提供流畅的语音转文字体验。

---

## 功能特性

### 核心功能
- **离线语音识别** — 基于 SenseVoice 模型，中文识别精准，支持标点恢复
- **AI 场景润色** — 办公/聊天/创作三种场景，通过 DeepSeek 大模型智能优化文案，每次输出 3 个不同风格版本供选择
- **行业词库纠错** — 9 大行业专业词库，自动纠正 ASR 误识别（如"拍 touch"→"PyTorch"）
- **用户词库学习** — 自动记录用户手动修正，形成个性化词库
- **历史记录** — 自动保存语音输入历史，支持检索和回看

### 桌面体验
- **悬浮球** — 桌面置顶悬浮球，单击呼出/隐藏浮窗，支持拖拽
- **紧凑浮窗** — 900×300 精简浮窗，实时转写 + AI 优化卡片一键发送
- **完整窗口** — 全部功能完整展示，方便管理配置和查看历史
- **全局热键** — Alt+Q 快速切换语音输入
- **系统托盘** — 常驻托盘，后台静默运行
- **文本注入** — 点击文案自动复制，点击目标输入框自动粘贴

---

## 项目架构

```
                    ┌──────────────────────────────────┐
                    │       Electron 桌面壳             │
                    │  ┌────────────────────────────┐  │
                    │  │  主进程                      │  │
                    │  │  · 子进程管理 · 全局热键     │  │
                    │  │  · 系统托盘 · 文本注入引擎   │  │
                    │  └────────┬─────────────────┘  │
                    │  ┌────────┴─────────────────┐  │
                    │  │  渲染进程 (React + Vite)  │  │
                    │  │  · 紧凑浮窗 · 完整窗口    │  │
                    │  │  · 音频捕获 · 场景切换    │  │
                    │  └────────┬─────────────────┘  │
                    └───────────┼─────────────────────┘
                                │ HTTP / WebSocket
                    ┌───────────┼─────────────────────┐
                    │    Python 后端 (FastAPI)         │
                    │  ┌────────────────────────┐     │
                    │  │  ASR 引擎               │     │
                    │  │  · SenseVoice 离线识别  │     │
                    │  ├────────────────────────┤     │
                    │  │  AI 服务层              │     │
                    │  │  · PromptManager        │     │
                    │  │  · 场景化润色 (DeepSeek)│     │
                    │  │  · 行业词库纠错         │     │
                    │  │  · 编辑分析学习         │     │
                    │  ├────────────────────────┤     │
                    │  │  数据层 (SQLite)        │     │
                    │  │  · 词库 · 纠错 · 历史  │     │
                    │  │  · 用户画像 · 编辑日志 │     │
                    │  └────────────────────────┘     │
                    └─────────────────────────────────┘
```

### 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 桌面壳 | Electron 28 + TypeScript | 主进程/渲染进程分离 |
| 前端 | React 18 + Vite | 双模式渲染（浮窗/完整窗口） |
| 后端 | Python FastAPI + Uvicorn | REST API + WebSocket |
| ASR | SenseVoice | 离线中文语音识别 |
| LLM | DeepSeek (deepseek-chat) | 场景化文本润色 |
| 数据库 | SQLite | 词库/纠错/历史/用户画像/编辑日志 |

---

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.10+
- Node.js 18+
- FFmpeg（用于音频转码）

### 安装

```bash
# 1. 安装 Python 依赖
cd backend
pip install -r requirements.txt

# 2. 安装前端依赖
cd ../frontend
npm install

# 3. 安装 Electron 依赖
cd ../electron
npm install

# 4. 配置环境变量
cd ../backend
# 编辑 .env 文件，填入你的 DeepSeek API Key
```

### 运行

```bash
# 1. 启动后端 (FastAPI :8000)
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 2. 启动前端 (React :3000) — 新开一个终端
cd frontend
npm run dev

# 3. 启动 Electron 桌面应用 — 新开一个终端
cd electron
npx tsc && npx electron .
```

或者直接双击 `start.bat` 一键启动后端和前端。

> 首次启动 SenseVoice 会自动下载模型（约 1.5GB），请耐心等待。

### 环境变量配置

编辑 `backend/.env` 文件：

```ini
# 大模型提供商
LLM_PROVIDER=deepseek

# DeepSeek 配置（推荐，国内直连，价格便宜）
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 运行模式
LLM_ENABLED=true
MVP_MODE=false
```

---

## 项目结构

```
├── backend/                 # Python 后端
│   ├── main.py              # FastAPI 主入口 + API 路由
│   ├── config.py            # 全局配置（pydantic-settings）
│   ├── .env                 # 环境变量（API Key 等）
│   ├── database/            # 数据库层
│   │   ├── industry_lexicon_db.py  # 行业词库
│   │   ├── lexicon_db.py          # 用户词库
│   │   └── ...
│   └── services/            # 业务服务
│       ├── optimization_service.py # 规则优化（降级用）
│       ├── profile_prompt_builder.py # 用户画像构建
│       └── ...
├── frontend/                # React 前端
│   ├── src/
│   │   ├── components/      # UI 组件
│   │   │   ├── CompactOverlay.tsx   # 紧凑浮窗
│   │   │   └── ...
│   │   ├── hooks/           # 自定义 Hooks
│   │   └── services/        # API 调用
│   └── index.html
├── electron/                # Electron 桌面壳
│   └── src/
│       ├── main.ts          # 主进程入口
│       ├── preload.ts       # IPC 桥接
│       ├── overlay.ts       # 浮窗管理
│       ├── floatingBall.ts  # 悬浮球
│       ├── textInjector.ts  # 文本注入引擎
│       └── hotkeys.ts       # 全局热键
├── ai_services/             # AI 服务层
│   ├── asr/                 # 语音识别引擎 (SenseVoice)
│   ├── nlp/                 # NLP 流水线
│   ├── lexicon/             # 行业词库系统（9大行业，自动纠错）
│   ├── prompts/             # Prompt 模板管理系统
│   │   ├── prompt_manager.py    # Prompt 核心管理器（模板注册/渲染/LLM调用）
│   │   ├── office_prompts.py    # 办公场景 Prompt（5种子场景，3版本输出）
│   │   ├── chat_prompts.py      # 聊天场景 Prompt（emoji/颜文字生成）
│   │   └── creation_prompts.py  # 创作场景 Prompt（多轮对话协作）
│   └── cache/               # 缓存系统（内存+磁盘两级缓存）
├── databases/               # SQLite 数据文件
├── start.bat                # 一键启动脚本
└── CLAUDE.md                # AI 辅助开发规范
```

---

## 使用说明

1. **启动应用** — 运行后系统托盘出现麦克风图标，桌面显示悬浮球
2. **呼出浮窗** — 按 Alt+Q 或点击悬浮球
3. **开始录音** — 点击「开始录音」按钮，对着麦克风说话
4. **实时转写** — 浮窗中实时显示识别文字，支持中途编辑
5. **场景切换** — 在办公/聊天/创作场景间切换，获取不同优化建议
6. **AI 润色** — 系统自动调用 DeepSeek 大模型生成优化文案（约 2-5 秒）
7. **AI 润色** — 录音完成后自动调用 DeepSeek 大模型，根据场景生成 3 个优化版本卡片（约 2-5 秒）
8. **选择版本** — 从 3 个优化版本中挑选最合适的，点击卡片即可
9. **发送文字** — 点击优化卡片，文字自动复制到剪贴板，再点击目标输入框即可自动粘贴
8. **创作模式** — 支持多轮对话式创作（小说/项目策划），与 AI 协作完善内容

### 场景说明

- **办公** — 将口语化语音转为严谨书面语，支持 5 种子场景：
  - 沟通润色：口语→专业书面表达（如"跟老王说报表周五前交"→"请转告王工，报表需于本周五前提交"）
  - 内容代写：一句话生成完整邮件/周报/通知/请假申请
  - 会议纪要：口语会议讨论→结构化纪要（议题→讨论→结论→行动项）
  - 总结提炼：长文本→结构化要点
  - 公告通知：通知内容→规范公告格式
  - 每次输出 3 个版本（严谨版/清晰版/简洁版），自动校对错别字和语病
- **聊天** — 添加 emoji/颜文字，语气更生动自然，适合日常社交对话
- **创作** — 多轮对话创作，支持小说构思和项目策划，与 AI 协作完善内容

---

## 开发说明

本项目为实训项目，所有提交记录符合实训要求。

> Claude AI 辅助开发，本人自主整合调试

---

## 许可证

MIT License
