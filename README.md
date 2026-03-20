# Zoo Multi-Agent System 🐾

Agent动物园 - 雪球(雪纳瑞)、六六(蓝鹦鹉)、小黄(黄鹦鹉)

## 动物成员

- **雪球 (Xueqiu)**: 雪纳瑞 - `opencode` CLI - 主架构师
- **六六 (Liuliu)**: 虎皮鹦鹉(蓝) - `claude` CLI - Code Review
- **小黄 (Xiaohuang)**: 虎皮鹦鹉(黄绿) - `crush` CLI - 视觉设计

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

## API 端点

### 消息端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/messages` | 发送消息给动物们 |
| GET | `/api/threads/{thread_id}` | 获取线程详情 |
| POST | `/api/threads/{thread_id}/cancel` | 取消线程 |

### MCP 回调端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/callbacks/post-message` | 动物 posting 消息 |
| GET | `/api/callbacks/thread-context` | 获取线程上下文 |
| GET | `/api/callbacks/pending-mentions` | 检查 @提及 |

### WebSocket

| 路径 | 描述 |
|------|------|
| `/ws` | 实时多动物通信 |

## 项目结构

```
zoo/
├── api/              # API Layer (Phase 5)
│   ├── __init__.py
│   ├── schemas.py    # Pydantic schemas
│   ├── routes.py     # FastAPI routes
│   └── dependencies.py # Dependency injection
├── core/             # Core Services (Phase 3)
│   ├── config.py     # Configuration
│   ├── models.py     # Pydantic models
│   └── types.py      # Type definitions
├── services/         # Business Logic (Phase 4)
│   ├── cli_spawner.py   # CLI process management
│   ├── invocation_tracker.py # Invocation tracking
│   └── mcp_callback_router.py # MCP callbacks
├── utils/            # Utilities (Phase 2)
│   ├── a2a_mentions.py   # @mention parsing
│   └── a2a_router.py     # Animal routing
├── agents/           # Animal Agents (Phase 1)
│   ├── xueqiu.py
│   ├── liuliu.py
│   └── xiaohuang.py
├── web/              # Web Frontend (Phase 6)
│   └── static/
│       ├── index.html
│       ├── css/
│       ├── js/
│       └── assets/
├── storage/          # Data Storage (Phase 4)
├── tests/            # Tests
├── main.py           # Application entry point
└── README.md
```

## 技术栈

- **Framework**: FastAPI
- **WebSocket**: Standard WebSocket support
- **Pydantic**: Data validation
- **CLI Tools**: opencode, claude, crush
- **Async**: asyncio, async/await

## 开发

```bash
# 开发模式 (自动重载)
uvicorn main:app --reload

# 运行测试
pytest tests/

# 类型检查
mypy zoo/
```

## 许可证

MIT License
