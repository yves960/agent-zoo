# Agent Zoo 🐾

一个**多来源 Agent 自动发现与协作系统**。自动发现本机运行的 agents（本地配置、h-agent 团队、OpenCode 会话、mDNS 网络），通过统一的 Web UI 进行展示和对话。

## ✨ 特性

- 🔍 **多源自动发现** - 本地配置、h-agent 团队、OpenCode 会话、mDNS 网络广播
- 💬 **统一对话界面** - 通过 WebSocket 与任意 Agent 实时对话
- 🎨 **卡通风格前端** - Next.js 构建的可爱界面，支持筛选和搜索
- 🔧 **多工具支持** - opencode、claude、crush 等 CLI 工具
- 🌐 **HTTP API 调用** - 支持通过 HTTP API 调用 h-agent 和 OpenCode 会话

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

## 🔍 Agent 来源

| 来源 | 说明 |
|------|------|
| **本地** | `config/agents.yaml` 中配置的 Agent |
| **h-agent** | [h-agent](https://github.com/yves960/h-agent) 团队的 planner/coder/reviewer/devops 等角色 |
| **OpenCode 会话** | opencode serve 上运行的所有会话 |
| **网络发现** | 通过 mDNS 广播发现的局域网内的 Agent Zoo 实例 |

## 🎭 自定义 Agent

### 配置文件

编辑 `config/agents.yaml` 来配置本地 Agent：

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
      tool: opencode
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

## API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/animals` | 获取所有 Agent 列表（按来源筛选） |
| GET | `/api/external/agents` | 获取 h-agent 团队成员 |
| GET | `/api/network/agents` | 获取网络发现的 Agent |
| POST | `/api/messages` | 发送消息 |
| GET | `/api/threads/{thread_id}` | 获取对话线程 |
| WebSocket | `/api/ws` | 实时通信 |

## 项目结构

```
agent-zoo/
├── config/
│   └── agents.yaml           # Agent 配置文件
├── core/
│   ├── agent_config.py        # 配置模型
│   ├── websocket_manager.py   # WebSocket 管理
│   └── config.py              # 系统配置
├── agents/
│   ├── generic.py             # 通用 Agent 类
│   ├── registry.py            # Agent 注册表
│   ├── h_agent_service.py     # h-agent HTTP 调用
│   └── opencode_service.py    # OpenCode HTTP 调用
├── services/
│   ├── agent_dispatcher.py     # 消息分发
│   ├── agent_loader.py         # 配置加载
│   ├── h_agent_client.py      # h-agent API 客户端
│   ├── directory_scanner.py   # 目录扫描
│   ├── network_discovery.py   # mDNS 网络发现
│   └── opencode_session_discovery.py  # OpenCode 会话发现
├── api/
│   └── routes.py              # API 路由
├── web/                       # Next.js 前端
└── main.py                    # 入口
```

## 技术栈

- **Backend**: FastAPI, WebSocket, Pydantic
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Agent Tools**: opencode, claude, crush
- **网络发现**: python-zeroconf (mDNS)

## 相关项目

- [h-agent](https://github.com/yves960/h-agent) - 多角色 Agent 团队协作系统

## 许可证

MIT License
