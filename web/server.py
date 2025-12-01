#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Web 服务：提供响应式多代理控制台与 REST API。
"""

from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config.settings import Config
from core.memory_manager import MemoryManager
from core.chat_engine import ChatEngine
from core.agent_controller import MultiAgentController

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    target_agent: Optional[str] = None  # 允许用户直接指定与特定专家大脑交互


class ChatResponsePayload(BaseModel):
    content: str
    project_summary: Optional[str]
    specialists: List[Dict[str, str]]
    metadata: Dict[str, Optional[str]]


memory_manager = MemoryManager()
chat_engine = ChatEngine(memory_manager)
multi_agent_controller = (
    MultiAgentController(chat_engine) if Config.ENABLE_MULTI_AGENT else None
)

app = FastAPI(
    title="mem0 Project Brain Web",
    description="多代理项目大脑控制台",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATE_DIR)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """渲染响应式页面。"""
    # 分离项目大脑和专家大脑
    project_brain = {agent_id: profile for agent_id, profile in Config.AGENT_PROFILES.items() 
                    if profile.get('type') == 'orchestrator'}
    specialist_agents = {agent_id: profile for agent_id, profile in Config.AGENT_PROFILES.items() 
                        if profile.get('type') == 'specialist'}
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_user": Config.DEFAULT_USER_ID,
            "default_session": Config.DEFAULT_SESSION_ID,
            "agents": Config.AGENT_PROFILES,
            "project_brain": project_brain,
            "specialist_agents": specialist_agents,
            "multi_agent": Config.ENABLE_MULTI_AGENT,
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponsePayload)
async def chat_endpoint(payload: ChatRequest):
    """统一 API，返回结构化结果供前端动态展示。"""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    user_id = payload.user_id or Config.DEFAULT_USER_ID
    session_id = payload.session_id or Config.DEFAULT_SESSION_ID
    agent_id = payload.agent_id or Config.DEFAULT_AGENT_ID
    target_agent = payload.target_agent  # 用户直接指定的专家大脑
    
    try:
        project_summary = None
        specialists: List[Dict[str, str]] = []
        
        if Config.ENABLE_MULTI_AGENT and multi_agent_controller:
            # 如果用户指定了目标专家，直接与该专家交互；否则使用项目大脑的多代理流程
            ma_result = multi_agent_controller.process_user_message(
                message,
                user_id,
                session_id,
                target_agent=target_agent
            )
            response = ma_result.final_response
            project_summary = ma_result.project_summary
            specialists = [
                {
                    "agent_id": specialist.agent_id,
                    "agent_name": Config.AGENT_PROFILES.get(
                        specialist.agent_id, {}
                    ).get("name", specialist.agent_id),
                    "content": specialist.content,
                }
                for specialist in ma_result.specialist_outputs
            ]
        else:
            response = chat_engine.generate_response(
                message,
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id
            )
        
        return ChatResponsePayload(
            content=response.content,
            project_summary=project_summary,
            specialists=specialists,
            metadata={
                "user_id": response.user_id,
                "agent_id": response.agent_id,
                "session_id": response.session_id,
                "memories_count": str(response.memories_count),
                "memory_used": "true" if response.memory_used else "false",
                "collaborators": ", ".join(response.collaborators) if response.collaborators else "",
                "target_agent": target_agent or "",
                "expert_domain": response.expert_domain or "" if hasattr(response, 'expert_domain') else "",
            }
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def get_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("web.server:app", host="0.0.0.0", port=8000, reload=True)

