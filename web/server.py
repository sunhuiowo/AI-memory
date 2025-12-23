#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Web 服务：提供响应式多代理控制台与 REST API。

该模块实现了：
1. FastAPI Web服务器的配置和初始化
2. 响应式前端页面的渲染
3. 聊天API端点的实现
4. 多代理系统的集成
5. CORS中间件配置
6. 静态文件服务
"""

# 导入路径处理模块
from pathlib import Path
# 导入类型提示
from typing import Optional, List, Dict

# 导入FastAPI相关模块
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# 导入Pydantic用于数据验证
from pydantic import BaseModel

# 导入配置模块
from config.settings import Config
# 导入记忆管理器
from core.memory_manager import MemoryManager
# 导入聊天引擎
from core.chat_engine import ChatEngine
# 导入多代理控制器
from core.agent_controller import MultiAgentController

# 定义基础目录
BASE_DIR = Path(__file__).resolve().parent
# 定义静态文件目录
STATIC_DIR = BASE_DIR / "static"
# 定义模板文件目录
TEMPLATE_DIR = BASE_DIR / "templates"


class ChatRequest(BaseModel):
    """聊天请求数据模型。
    
    定义了前端发送到后端的聊天请求的结构。
    """
    message: str                         # 用户发送的消息内容
    user_id: Optional[str] = None        # 用户ID，可选
    session_id: Optional[str] = None     # 会话ID，可选
    agent_id: Optional[str] = None       # 智能体ID，可选
    target_agent: Optional[str] = None   # 允许用户直接指定与特定专家大脑交互


class ChatResponsePayload(BaseModel):
    """聊天响应数据模型。
    
    定义了后端返回给前端的聊天响应的结构。
    """
    content: str                              # 聊天响应内容
    project_summary: Optional[str]            # 项目摘要，可选
    specialists: List[Dict[str, str]]         # 参与响应的专家列表
    metadata: Dict[str, Optional[str]]        # 元数据信息


# 初始化记忆管理器
memory_manager = MemoryManager()
# 初始化聊天引擎
chat_engine = ChatEngine(memory_manager)
# 根据配置初始化多代理控制器（如果启用）
multi_agent_controller = (
    MultiAgentController(chat_engine) if Config.ENABLE_MULTI_AGENT else None
)

# 创建FastAPI应用实例
app = FastAPI(
    title="mem0 Project Brain Web",        # API标题
    description="多代理项目大脑控制台",    # API描述
    version="0.2.0",                       # API版本
)

# 添加CORS中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_headers=["*"],  # 允许所有头
    allow_methods=["*"],  # 允许所有方法
)

# 挂载静态文件目录（如果存在）
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 初始化Jinja2模板引擎
templates = Jinja2Templates(directory=TEMPLATE_DIR)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """渲染响应式页面。
    
    渲染前端页面，传递配置参数和智能体信息。
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        HTMLResponse: 渲染后的前端页面
    """
    # 分离项目大脑和专家大脑
    project_brain = {agent_id: profile for agent_id, profile in Config.AGENT_PROFILES.items() 
                    if profile.get('type') == 'orchestrator'}
    specialist_agents = {agent_id: profile for agent_id, profile in Config.AGENT_PROFILES.items() 
                        if profile.get('type') == 'specialist'}
    
    # 渲染模板并返回响应
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,               # 请求对象
            "default_user": Config.DEFAULT_USER_ID,  # 默认用户ID
            "default_session": Config.DEFAULT_SESSION_ID,  # 默认会话ID
            "agents": Config.AGENT_PROFILES,  # 所有智能体配置
            "project_brain": project_brain,   # 项目大脑配置
            "specialist_agents": specialist_agents,  # 专家智能体配置
            "multi_agent": Config.ENABLE_MULTI_AGENT,  # 是否启用多代理
        },
    )


@app.get("/health")
async def health():
    """健康检查端点。
    
    用于检查服务是否正常运行。
    
    Returns:
        dict: 包含服务状态的字典
    """
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponsePayload)
async def chat_endpoint(payload: ChatRequest):
    """统一 API，返回结构化结果供前端动态展示。
    
    处理前端的聊天请求，调用相应的服务生成响应，并返回结构化结果。
    
    Args:
        payload: ChatRequest对象，包含聊天请求数据
        
    Returns:
        ChatResponsePayload: 结构化的聊天响应数据
        
    Raises:
        HTTPException: 当请求参数无效或处理过程中出错时
    """
    # 去除消息前后的空格
    message = payload.message.strip()
    # 验证消息是否为空
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    # 设置默认值
    user_id = payload.user_id or Config.DEFAULT_USER_ID
    session_id = payload.session_id or Config.DEFAULT_SESSION_ID
    agent_id = payload.agent_id or Config.DEFAULT_AGENT_ID
    target_agent = payload.target_agent  # 用户直接指定的专家大脑
    
    try:
        # 初始化变量
        project_summary = None
        specialists: List[Dict[str, str]] = []
        
        # 如果启用了多代理功能且多代理控制器已初始化
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
            # 构建专家列表
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
            # 使用单代理模式生成响应
            response = chat_engine.generate_response(
                message,
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id
            )
        
        # 返回结构化响应
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
        # 重新抛出HTTP异常
        raise
    except Exception as exc:  # noqa: BLE001
        # 捕获其他异常并返回500错误
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def get_app() -> FastAPI:
    """获取FastAPI应用实例。
    
    用于在测试或其他场景中获取FastAPI应用实例。
    
    Returns:
        FastAPI: FastAPI应用实例
    """
    return app


if __name__ == "__main__":
    """主函数。
    
    当直接运行该文件时，启动Uvicorn服务器。
    """
    import uvicorn
    
    # 启动Uvicorn服务器
    uvicorn.run("web.server:app", host="0.0.0.0", port=8000, reload=True)

