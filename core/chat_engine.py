#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天引擎核心逻辑

该模块实现了聊天引擎的核心功能，负责：
1. 初始化LLM客户端并与大语言模型交互
2. 管理对话历史和缓存
3. 协调上下文的构建和管理
4. 生成智能回复
5. 处理记忆的存储和检索
"""

# 导入OpenAI客户端
from openai import OpenAI as OpenAIClient
# 导入日志模块
import logging
# 导入类型提示
from typing import Dict, List, Optional

# 导入配置模块
from config.settings import Config
# 导入数据模型
from models.data_models import ChatMessage, ChatResponse, ConversationCache, SpecialistResult, MultiAgentResult
# 导入记忆管理器
from core.memory_manager import MemoryManager
# 导入上下文协调器
from core.context_engine import ContextOrchestrator

# 配置日志记录器
logger = logging.getLogger(__name__)

class ChatEngine:
    """聊天引擎
    
    该类是聊天系统的核心组件，负责处理用户输入、生成响应并管理对话流程。
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """初始化聊天引擎。
        
        Args:
            memory_manager: 记忆管理器实例，用于处理长期记忆的存储和检索
        """
        # 存储记忆管理器实例
        self.memory_manager = memory_manager
        # 初始化LLM客户端
        self.llm_client = self._initialize_llm_client()
        # 初始化对话缓存
        self.conversation_cache = ConversationCache(Config.CONVERSATION_CACHE_SIZE)
        # 初始化上下文协调器
        self.context_orchestrator = ContextOrchestrator(memory_manager)
        # 记录初始化成功日志
        logger.info("聊天引擎初始化成功")
    
    def _initialize_llm_client(self) -> OpenAIClient:
        """初始化LLM客户端。
        
        Returns:
            OpenAIClient实例，用于与大语言模型交互
            
        Raises:
            Exception: 当LLM客户端初始化失败时抛出
        """
        try:
            # 使用配置文件中的参数初始化OpenAI客户端
            return OpenAIClient(
                base_url=Config.LLM_BASE_URL,  # LLM服务的基础URL
                api_key=Config.API_KEY          # API密钥
            )
        except Exception as e:
            # 记录错误日志并重新抛出异常
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
        """生成智能回复。
        
        该方法是聊天引擎的核心接口，负责处理用户消息并生成智能回复。
        它协调了上下文构建、LLM调用和记忆管理等功能。
        
        Args:
            message: 用户消息内容
            user_id: 用户ID，默认为配置文件中的默认用户ID
            agent_id: 智能体ID，默认为配置文件中的默认智能体ID
            session_id: 会话ID，默认为配置文件中的默认会话ID
            persist_history: 是否持久化对话历史到缓存，默认True
            store_memory: 是否将交互内容存储到长期记忆，默认True
            extra_context: 额外提供的上下文信息
            cached_messages_override: 覆盖缓存的消息列表
            memory_type: 记忆类型（user/expert/project）
            memory_metadata: 记忆元数据，包含领域信息等
            
        Returns:
            ChatResponse对象，包含生成的回复内容和相关元数据
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
        """调用LLM生成回复。
        
        Args:
            messages: 消息列表，每个消息包含role和content字段
            
        Returns:
            大语言模型生成的回复内容
        """
        try:
            # 打印调试信息
            print(f"调试 - 输入_call_llm的消息数量: {len(messages)}")
            
            # 验证并修复消息格式
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
            
            # 打印修复后的消息信息
            for i, msg in enumerate(valid_messages):
                print(f"修复后消息 {i}: role={msg.get('role')}, content长度={len(str(msg.get('content', '')))} ")
            
            # 调用大语言模型生成回复
            response = self.llm_client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,  # 使用的模型名称
                messages=valid_messages,       # 消息列表
                temperature=0.7,               # 温度参数，控制生成文本的随机性
                max_tokens=1024                # 最大生成令牌数
            )
            
            # 返回生成的回复内容
            return response.choices[0].message.content
            
        except Exception as e:
            # 捕获并打印详细错误信息
            print(f"调用LLM时发生异常: {str(e)}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            # 尝试返回一个简单的错误响应
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
        """完成交互处理。
        
        该方法负责：
        1. 更新对话缓存
        2. 将交互内容存储到长期记忆
        3. 根据记忆类型和元数据进行分类存储
        
        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            user_id: 用户ID
            agent_id: 智能体ID
            session_id: 会话ID
            persist_history: 是否持久化对话历史
            store_memory: 是否存储记忆
            memory_type: 记忆类型（user/expert/project）
            memory_metadata: 记忆元数据，包含领域信息等
        """
        # 更新对话缓存
        if persist_history:
            # 创建用户消息对象
            user_msg = ChatMessage(role="user", content=user_message)
            # 创建助手回复对象
            assistant_msg = ChatMessage(role="assistant", content=assistant_response)
            # 添加到对话缓存
            self.conversation_cache.add_message(user_id, user_msg)
            self.conversation_cache.add_message(user_id, assistant_msg)
        
        # 存储到长期记忆
        if store_memory:
            # 根据不同的记忆类型进行分类存储
            if memory_type == "expert" and memory_metadata:
                """专家记忆：存储专家代理的交互内容"""
                self.memory_manager.store_memory(
                    content=f"用户提问: {user_message}\n专家回复: {assistant_response}",
                    user_id=user_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    memory_type=memory_type,
                    metadata=memory_metadata
                )
            elif memory_type == "project":
                """项目记忆：存储项目相关的交互内容"""
                self.memory_manager.store_memory(
                    content=f"用户提问: {user_message}\n系统回复: {assistant_response}",
                    user_id=user_id,
                    agent_id="project_brain",  # 项目记忆的代理ID固定为project_brain
                    session_id=session_id,
                    memory_type=memory_type,
                    metadata=memory_metadata or {}
                )
            else:
                """默认用户记忆：存储普通用户交互内容"""
                self.memory_manager.store_memory(
                    content=f"用户提问: {user_message}\n系统回复: {assistant_response}",
                    user_id=user_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    memory_type="user",  # 默认记忆类型为user
                    metadata={}
                )
    
    def clear_conversation_cache(self, user_id: str):
        """清空指定用户的对话缓存。
        
        Args:
            user_id: 用户ID
        """
        self.conversation_cache.clear(user_id)
        logger.info(f"用户 {user_id} 的对话缓存已清空")
    
    def get_conversation_stats(self, user_id: str) -> Dict[str, any]:
        """获取指定用户的对话统计信息。
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含对话统计信息的字典
        """
        # 获取对话统计并转换为字典格式返回
        return self.conversation_cache.get_stats(user_id).__dict__