#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义

该模块定义了应用程序中使用的所有数据模型，包括：
1. 聊天消息模型
2. 对话统计信息模型
3. 聊天响应模型
4. 上下文内容模型
5. 专家结果模型
6. 多代理结果模型
7. 对话缓存管理类
"""

# 导入必要的类型和工具
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque

@dataclass
class ChatMessage:
    """聊天消息数据模型
    
    表示对话中的一条消息，包含角色、内容和可选的时间戳。
    """
    role: str                      # 角色，如 user, assistant, system
    content: str                   # 消息内容
    timestamp: Optional[str] = None  # 时间戳，可选
    
    def to_dict(self) -> Dict[str, str]:
        """将消息转换为字典格式
        
        用于序列化或与其他系统交互。
        
        Returns:
            Dict[str, str]: 包含角色和内容的字典
        """
        return {"role": self.role, "content": self.content}

@dataclass
class ConversationStats:
    """对话统计信息
    
    包含对话的统计数据，如缓存的对话数量、缓存最大大小等。
    """
    user_id: str                    # 用户ID
    cached_conversations: int       # 缓存的对话数量
    cache_max_size: int             # 缓存的最大大小
    total_memories: Optional[int] = None  # 总记忆数量，可选

@dataclass
class ChatResponse:
    """聊天响应数据模型
    
    表示智能体对用户消息的响应，包含响应内容、元数据和状态信息。
    """
    content: str                     # 响应内容
    user_id: str                     # 用户ID
    agent_id: Optional[str] = None   # 智能体ID，可选
    session_id: Optional[str] = None  # 会话ID，可选
    memory_used: bool = False        # 是否使用了记忆
    memories_count: int = 0          # 使用的记忆数量
    collaborators: List[str] = field(default_factory=list)  # 协作的智能体列表
    error: Optional[str] = None      # 错误信息，可选

@dataclass
class ContextPayload:
    """
    LLM 上下文内容，用于统一封装系统提示、对话历史和记忆状态。
    
    为LLM提供完整的上下文信息，包括消息历史、记忆使用情况等。
    """
    messages: List[Dict[str, str]]   # 消息列表，包含系统提示和对话历史
    memory_used: bool                # 是否使用了记忆
    memories_count: int              # 使用的记忆数量
    agent_id: str                    # 智能体ID
    session_id: str                  # 会话ID
    collaborators: List[str]         # 协作的智能体列表

@dataclass
class SpecialistResult:
    """单个专家代理在某次项目任务中的输出。
    
    表示一个专家智能体的输出结果。
    """
    agent_id: str                    # 专家智能体ID
    content: str                     # 专家智能体的输出内容

@dataclass
class MultiAgentResult:
    """多代理协作的整体汇总。
    
    表示多个智能体协作完成任务的结果。
    """
    project_summary: str              # 项目摘要
    selected_agents: List[str]        # 选中的智能体列表
    specialist_outputs: List[SpecialistResult]  # 专家智能体的输出列表
    final_response: ChatResponse      # 最终响应

class ConversationCache:
    """对话缓存管理
    
    用于管理和存储用户对话的缓存系统，支持按用户ID隔离缓存，
    使用双端队列实现，支持固定大小和自动淘汰最旧消息。
    """
    
    def __init__(self, max_size: int = 5):
        """初始化对话缓存
        
        Args:
            max_size: 每个用户缓存的最大消息数，超过此大小会自动淘汰最旧的消息
        """
        self._cache = {}  # 存储用户ID到其消息队列的映射
        self.max_size = max_size  # 每个用户的最大缓存大小
    
    def get_user_cache(self, user_id: str) -> deque:
        """获取用户对话缓存
        
        根据用户ID获取对应的消息队列，如果不存在则创建新的队列。
        
        Args:
            user_id: 用户ID，用于标识唯一用户
            
        Returns:
            deque: 用户的消息队列，包含该用户的对话历史
        """
        if user_id not in self._cache:
            # 如果用户缓存不存在，创建新的双端队列
            self._cache[user_id] = deque(maxlen=self.max_size)
        return self._cache[user_id]
    
    def add_message(self, user_id: str, message: ChatMessage):
        """添加消息到缓存
        
        将用户的新消息添加到其对应的缓存队列中。
        
        Args:
            user_id: 用户ID，用于标识唯一用户
            message: 要添加的聊天消息对象
        """
        cache = self.get_user_cache(user_id)
        # 将消息转换为字典格式后添加到队列
        cache.append(message.to_dict())
    
    def get_messages(self, user_id: str) -> List[Dict[str, str]]:
        """获取用户所有缓存消息
        
        获取用户缓存中的所有消息，按时间顺序排列（最旧到最新）。
        
        Args:
            user_id: 用户ID，用于标识唯一用户
            
        Returns:
            List[Dict[str, str]]: 用户的所有缓存消息列表
        """
        return list(self.get_user_cache(user_id))
    
    def get_recent_messages(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """获取指定数量的最新消息，用于构建上下文窗口。
        
        根据指定的限制获取用户最近的消息，常用于构建LLM的上下文窗口。
        
        Args:
            user_id: 用户ID，用于标识唯一用户
            limit: 要获取的最新消息数量，如果为None或<=0则返回所有消息
            
        Returns:
            List[Dict[str, str]]: 用户的最新消息列表，按时间顺序排列（最旧到最新）
        """
        messages = self.get_messages(user_id)
        if limit is None or limit <= 0:
            return messages
        return messages[-limit:]  # 返回最后N条消息
    
    def clear(self, user_id: str):
        """清空用户缓存
        
        删除指定用户的所有缓存消息。
        
        Args:
            user_id: 用户ID，用于标识唯一用户
        """
        if user_id in self._cache:
            self._cache[user_id].clear()
    
    def get_stats(self, user_id: str) -> ConversationStats:
        """获取缓存统计
        
        获取指定用户的缓存统计信息，包括缓存的对话数量等。
        
        Args:
            user_id: 用户ID，用于标识唯一用户
            
        Returns:
            ConversationStats: 包含用户缓存统计信息的对象
        """
        cache = self.get_user_cache(user_id)
        return ConversationStats(
            user_id=user_id,
            cached_conversations=len(cache),  # 当前缓存的消息数量
            cache_max_size=self.max_size  # 缓存的最大大小
        )