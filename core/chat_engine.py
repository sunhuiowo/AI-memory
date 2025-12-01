#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天引擎核心逻辑
"""

from openai import OpenAI as OpenAIClient
import logging
from typing import Dict, List, Optional

from config.settings import Config
from models.data_models import ChatMessage, ChatResponse, ConversationCache, SpecialistResult, MultiAgentResult
from core.memory_manager import MemoryManager
from core.context_engine import ContextOrchestrator

logger = logging.getLogger(__name__)

class ChatEngine:
    """聊天引擎"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.llm_client = self._initialize_llm_client()
        self.conversation_cache = ConversationCache(Config.CONVERSATION_CACHE_SIZE)
        self.context_orchestrator = ContextOrchestrator(memory_manager)
        logger.info("聊天引擎初始化成功")
    
    def _initialize_llm_client(self) -> OpenAIClient:
        """初始化LLM客户端"""
        try:
            return OpenAIClient(
                base_url=Config.LLM_BASE_URL,
                api_key=Config.API_KEY
            )
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {e}")
            raise
    
    def generate_response(
        self,
        message: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        *, 
        persist_history: bool = True,
        store_memory: bool = True,
        extra_context: Optional[str] = None,
        cached_messages_override: Optional[List[Dict[str, str]]] = None,
        memory_type: Optional[str] = None,  # 新增参数
        memory_metadata: Optional[Dict] = None  # 新增参数
    ) -> ChatResponse:
        """
        生成智能回复
        
        Args:
            message: 用户消息
            user_id: 用户ID
            agent_id: 智能体ID
            session_id: 会话ID
            persist_history: 是否持久化对话历史
            store_memory: 是否存储记忆
            extra_context: 额外上下文
            cached_messages_override: 覆盖缓存消息
            memory_type: 记忆类型（user/expert/project）
            memory_metadata: 记忆元数据，包含领域信息等
            
        Returns:
            聊天响应对象
        """
        user_id = user_id or Config.DEFAULT_USER_ID
        agent_id = agent_id or Config.DEFAULT_AGENT_ID
        session_id = session_id or Config.DEFAULT_SESSION_ID
        
        try:
            if cached_messages_override is not None:
                cached_messages = cached_messages_override
            else:
                cached_messages = self.conversation_cache.get_recent_messages(
                    user_id,
                    Config.CONTEXT_PIPELINE.get("max_history_messages")
                )
            context_payload = self.context_orchestrator.build_payload(
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id,
                user_message=message,
                cached_messages=cached_messages,
                extra_context=extra_context,
                memory_type=memory_type,  # 传递记忆类型
                memory_metadata=memory_metadata  # 传递记忆元数据
            )
            
            assistant_response = self._call_llm(context_payload.messages)
            
            self._finalize_interaction(
                message,
                assistant_response,
                user_id,
                agent_id,
                session_id,
                persist_history,
                store_memory,
                memory_type=memory_type,  # 传递记忆类型
                memory_metadata=memory_metadata  # 传递记忆元数据
            )
            
            return ChatResponse(
                content=assistant_response,
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id,
                memory_used=context_payload.memory_used,
                memories_count=context_payload.memories_count,
                collaborators=context_payload.collaborators
            )
            
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            return ChatResponse(
                content="抱歉，我现在无法处理您的请求，请稍后再试。",
                user_id=user_id,
                error=str(e),
                agent_id=agent_id,
                session_id=session_id
            )
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用LLM生成回复"""
        try:
            # 打印消息列表以调试（不使用logger，确保输出可见）
            print(f"调试 - 输入_call_llm的消息数量: {len(messages)}")
            
            # 确保消息列表中的每个元素都是包含'role'和'content'的字典
            valid_messages = []
            for i, msg in enumerate(messages):
                # 检查是否为字典类型
                if not isinstance(msg, dict):
                    print(f"错误 - 消息 {i} 不是字典: {type(msg)}")
                    # 尝试转换为字典
                    valid_messages.append({'role': 'system', 'content': str(msg)})
                    continue
                
                # 检查必需字段
                if 'role' not in msg:
                    print(f"错误 - 消息 {i} 缺少'role'字段: {msg}")
                    msg = msg.copy()
                    msg['role'] = 'system'
                
                if 'content' not in msg:
                    print(f"错误 - 消息 {i} 缺少'content'字段: {msg}")
                    msg = msg.copy()
                    msg['content'] = ''
                
                valid_messages.append(msg)
            
            # 再次检查所有消息
            for i, msg in enumerate(valid_messages):
                print(f"修复后消息 {i}: role={msg.get('role')}, content长度={len(str(msg.get('content', '')))}")
            
            # 调用LLM
            response = self.llm_client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,
                messages=valid_messages,
                temperature=0.7,
                max_tokens=1024
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # 捕获并打印详细错误信息
            print(f"调用LLM时发生异常: {str(e)}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            # 尝试返回一个简单的响应
            return f"生成回复时发生错误: {str(e)}"
    
    def _finalize_interaction(
        self,
        user_message: str,
        assistant_response: str,
        user_id: str,
        agent_id: str,
        session_id: str,
        persist_history: bool,
        store_memory: bool,
        memory_type: Optional[str] = None,  # 新增参数
        memory_metadata: Optional[Dict] = None  # 新增参数
    ):
        """
        完成交互处理
        
        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            user_id: 用户ID
            agent_id: 智能体ID
            session_id: 会话ID
            persist_history: 是否持久化对话历史
            store_memory: 是否存储记忆
            memory_type: 记忆类型
            memory_metadata: 记忆元数据
        """
        # 更新对话缓存
        if persist_history:
            user_msg = ChatMessage(role="user", content=user_message)
            assistant_msg = ChatMessage(role="assistant", content=assistant_response)
            self.conversation_cache.add_message(user_id, user_msg)
            self.conversation_cache.add_message(user_id, assistant_msg)
        
        # 存储到长期记忆
        if store_memory:
            # 为不同类型的交互设置不同的记忆类型和元数据
            if memory_type == "expert" and memory_metadata:
                # 专家记忆
                self.memory_manager.store_memory(
                    content=f"用户提问: {user_message}\n专家回复: {assistant_response}",
                    user_id=user_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    memory_type=memory_type,
                    metadata=memory_metadata
                )
            elif memory_type == "project":
                # 项目记忆
                self.memory_manager.store_memory(
                    content=f"用户提问: {user_message}\n系统回复: {assistant_response}",
                    user_id=user_id,
                    agent_id="project_brain",
                    session_id=session_id,
                    memory_type=memory_type,
                    metadata=memory_metadata or {}
                )
            else:
                # 默认用户记忆
                self.memory_manager.store_memory(
                    content=f"用户提问: {user_message}\n系统回复: {assistant_response}",
                    user_id=user_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    memory_type="user",
                    metadata={}
                )
    
    def clear_conversation_cache(self, user_id: str):
        """清空对话缓存"""
        self.conversation_cache.clear(user_id)
        logger.info(f"用户 {user_id} 的对话缓存已清空")
    
    def get_conversation_stats(self, user_id: str) -> Dict[str, any]:
        """获取对话统计"""
        return self.conversation_cache.get_stats(user_id).__dict__