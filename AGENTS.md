# AGENTS.md - Agent Zoo Development Guide

Agent Zoo is a multi-source agent auto-discovery system (Python 3.14+ backend, Next.js frontend).

- **Backend**: FastAPI, WebSocket, Pydantic
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Radix UI

## Build/Lint/Test Commands

### Python Backend
```bash
pytest                                    # All tests
pytest tests/test_agent_registry.py                   # Single file
pytest tests/test_agent_registry.py::TestAgentRegistryGetService::test_get_service_creates_instance  # Single test
pytest -k "agent_registry"              # Pattern match
pytest --cov=. --cov-report=term-missing  # With coverage
```

### Web Frontend (in `web/`)
```bash
npm run dev      # Dev server (localhost:3000)
npm run build    # Production build
npm run lint     # ESLint + Next.js lint
npm test         # Jest tests
npm run test:watch    # Watch mode
npm run test:coverage # With coverage
```

## Python Style

**Imports**: Stdlib → third-party → local, with `TYPE_CHECKING` guard.
```python
from typing import Any, Dict, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from agents.base import AnimalService

if TYPE_CHECKING:
    from services.cli_spawner import CLISpawner
```

**Naming**: Classes `PascalCase`, functions `snake_case`, constants `UPPER_SNAKE_CASE`, private `_underscore`.

**Pydantic**: Use `Field` with `description`, `field_validator`, `Enum`.
```python
class AgentTool(str, Enum):
    """Supported agent CLI tools."""
    OPENCODE = "opencode"
    CLAUDE = "claude"
    CODEX = "codex"
    CRUSH = "crush"
    OPENAI = "openai"

class AgentConfig(BaseModel):
    id: str = Field(..., description="Unique agent identifier")
    enabled: bool = Field(default=True)
    
    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not v.startswith("#") or len(v) not in (4, 7, 9):
            return "#666666"
        return v
```

**Async**: Use `async def`, `AsyncGenerator` for streams.

## TypeScript/React Style

**Imports**: Use `@/` path alias, order: React → third-party → local.
```typescript
import { useState } from "react";
import { motion } from "framer-motion";
import { Sidebar } from "@/components/layout/Sidebar";
```

**Components**: Functional with hooks, add `"use client"` directive.
```typescript
"use client";
interface Props { title: string; onAction: () => void; }
export default function Component({ title, onAction }: Props) { ... }
```

**Styling**: Use `cn()` from `lib/utils.ts`, cartoon theme (`bg-cartoon-primary`, `rounded-cartoon`, `shadow-cartoon`).

**Naming**: Components `PascalCase`, hooks `useCamelCase`, stores `camelCase`.

## Project Structure
```
agent-zoo/
├── main.py              # FastAPI entry point
├── core/               # Config, WebSocket, models
├── agents/             # AnimalService subclasses
├── services/           # Dispatcher, CLI spawner
├── api/routes.py       # FastAPI routes
├── tests/              # Pytest test files
└── web/                # Next.js (src/components/, src/stores/)
```

## Key Conventions

- **WebSocket**: JSON with `type` field, `AsyncGenerator` for streaming
- **Agent Discovery**: config/agents.yaml, h-agent (8080), OpenCode CLI, mDNS
- **Testing**: pytest-asyncio, fixtures in `conftest.py`, autouse for cache cleanup
- **Config**: Pydantic Settings, `.env`, YAML for agents

## Common Patterns

**New Agent**: Inherit `AnimalService`, implement `invoke`, `get_cli_command`, `transform_event`, register in `agents/__init__.py`.

**New API Route**: Add to `api/routes.py` with `APIRouter`, Pydantic models, `Depends()`.

**New Component**: `.tsx` in `components/`, `"use client"` if hooks, Tailwind cartoon theme.
