"""Zoo Multi-Agent System - Main Application Entry Point.

FastAPI application with WebSocket and HTTP endpoints for the animal collaboration system.

Animals:
- 雪球 (Xueqiu): 雪纳瑞 - opencode CLI - 主架构师
- 六六 (Liuliu): 虎皮鹦鹉(蓝) - claude CLI - Code Review
- 小黄 (Xiaohuang): 虎皮鹦鹉(黄绿) - crush CLI - 视觉设计
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api.routes import get_api_router
from api.dependencies import (
    get_invocation_tracker,
    get_a2a_router,
    get_callback_router,
    get_websocket_manager,
)
from core.config import get_config
from services.network_discovery import NetworkDiscoveryService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup/shutdown events.
    
    Handles:
    - Server startup: Initialize connections, load models
    - Server shutdown: Cleanup resources, close connections
    """
    # Startup: Initialize connections and resources
    config = get_config()
    
    # Network discovery service for mDNS advertisement
    network_discovery: Optional[NetworkDiscoveryService] = None
    
    # Initialize services
    try:
        invocation_tracker = get_invocation_tracker()
        a2a_router = get_a2a_router()
        callback_router = get_callback_router()
        websocket_manager = get_websocket_manager()
        
        # Start mDNS advertisement
        network_discovery = NetworkDiscoveryService()
        if network_discovery.register_service("agent-zoo", config.ws_port):
            print(f"🌐 mDNS: Advertising Agent Zoo on _agent._tcp.local. port {config.ws_port}")
        else:
            print(f"⚠️  mDNS: Network discovery not available (zeroconf may not be installed)")
        
        # Log startup info
        print(f"🚀 Zoo Multi-Agent System starting...")
        print(f"  App: {config.app_name}")
        print(f"  Debug: {config.debug}")
        print(f"  Animals: xueqiu, liuliu, xiaohuang")
        print(f"  CLI: opencode, claude, crush")

        # Load agents from h-agent (after local agents so they take precedence)
        from services.agent_loader import load_h_agent_agents
        load_h_agent_agents()
    except Exception as e:
        print(f"⚠️  Warning: Service initialization partial: {e}")
    
    yield
    
    # Shutdown: Cleanup resources
    try:
        websocket_manager = get_websocket_manager()
        await websocket_manager.close_all()
        
        # Unregister mDNS service
        if network_discovery is not None:
            network_discovery.unregister_service("agent-zoo")
            network_discovery.close()
        
        print("✅ Zoo Multi-Agent System shutdown complete")
    except Exception as e:
        print(f"⚠️  Warning during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Zoo Multi-Agent System",
    description="🐾 雪球、六六、小黄的协作空间",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
api_router = get_api_router()
app.include_router(api_router)


# Mount static files
# Static directory structure:
# web/static/
#   index.html
#   css/
#   js/
#   assets/
static_dir = Path(__file__).parent / "web" / "dist"
if static_dir.exists() and static_dir.is_dir():
    # Check if it's a symlink or real directory with content
    target_dir = static_dir.resolve() if static_dir.is_symlink() else static_dir
    if target_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True),
            name="static",
        )
        print(f"📦 Static files mounted at / → {static_dir}")
    else:
        print(f"⚠️  Static directory target not found: {target_dir}")
else:
    print(f"⚠️  Static directory not found: {static_dir}")


if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    print(f"🚀 Starting Zoo Multi-Agent System on {config.ws_host}:{config.ws_port}")
    print(f"📚 API docs available at http://localhost:{config.ws_port}/docs")
    
    uvicorn.run(
        app,
        host=config.ws_host,
        port=config.ws_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
