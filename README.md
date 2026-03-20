# Agent Zoo 🐾

一个**可配置的多 Agent 协作系统**。用户可以通过配置文件自定义 Agent 的身份、性格和能力。

## ✨ 特性

- 🎭 **动态配置** - 通过 YAML 文件自定义 Agent 身份、性格、能力
- 💬 **WebSocket 实时通信** - 实时多 Agent 对话
- 🎨 **卡通风格前端** - Next.js 构建的可爱界面
- 🔧 **多工具支持** - opencode、claude、crush 等 CLI 工具

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

服务启动后:
- 前端页面: http://localhost:8001
- API 文档: http://localhost:8001/docs
- WebSocket: ws://localhost:8001/api/ws

## 🎭 自定义 Agent

### 配置文件

编辑 `config/agents.yaml` 来自定义你的 Agent：

```yaml
agents:
  - id: meiqiu
    name: 煤球
    species: 田园犬
    description: 我的全能助手
    color: "#8B4513"
    mention_patterns:
      - "@煤球"
      - "@meiqiu"
    enabled: true
    personality:
      traits:
        - 忠诚
        - 踏实
        - 朴实无华
      background: |
        煤球是一只来自乡间的田园犬，虽然没有名贵血统，
        但凭借勤奋和忠诚成为了最可靠的助手。
      style: 朴实直白，不说废话，直接给方案
      greetings:
        - "汪！有什么能帮你的？"
        - "来了！说吧，啥事？"
    capabilities:
      tool: opencode          # opencode | claude | crush | openai
      model: "minimax/MiniMax-M2.7"
      timeout: 300
```

### 配置字段说明

| 字段 | 说明 |
|------|------|
| `id` | Agent 唯一标识 |
| `name` | 显示名称 |
| `species` | 物种（如：田园犬、雪纳瑞、波斯猫）|
| `description` | 简短描述 |
| `color` | 主题颜色 |
| `mention_patterns` | @提及 的触发词 |
| `personality.traits` | 性格特点列表 |
| `personality.background` | 背景故事 |
| `personality.style` | 回复风格 |
| `personality.greetings` | 开场白 |
| `capabilities.tool` | CLI 工具（opencode/claude/crush/openai）|
| `capabilities.model` | 使用的模型 |

### 默认 Agent

系统预置了 4 个 Agent 作为示例：

| Agent | 物种 | 工具 | 角色 |
|-------|------|------|------|
| 煤球 | 田园犬 | opencode | 全能助手 |
| 雪球 | 雪纳瑞 | opencode | 开发工程师 |
| 六六 | 虎皮鹦鹉(蓝) | claude | 测试运维 |
| 小黄 | 虎皮鹦鹉(黄绿) | crush | 安全运维 |

## API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/animals` | 获取所有 Agent 列表 |
| POST | `/api/messages` | 发送消息 |
| GET | `/api/threads/{thread_id}` | 获取对话线程 |
| WebSocket | `/api/ws` | 实时通信 |

## 项目结构

```
agent-zoo/
├── config/
│   └── agents.yaml       # Agent 配置文件
├── core/
│   ├── agent_config.py   # 配置模型
│   └── config.py         # 系统配置
├── agents/
│   ├── generic.py        # 通用 Agent 类
│   └── registry.py       # Agent 注册
├── services/
│   ├── agent_dispatcher.py  # 消息分发
│   └── agent_loader.py      # 配置加载
├── api/
│   └── routes.py         # API 路由
├── web/                  # Next.js 前端
└── main.py               # 入口
```

## 技术栈

- **Backend**: FastAPI, WebSocket, Pydantic
- **Frontend**: Next.js, TypeScript
- **Agent Tools**: opencode, claude, crush

## 许可证

MIT License