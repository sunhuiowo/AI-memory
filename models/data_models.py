#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque

@dataclass
class ChatMessage:
    """聊天消息数据模型"""
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {"role": self.role, "content": self.content}

@dataclass
class ConversationStats:
    """对话统计信息"""
    user_id: str
    cached_conversations: int
    cache_max_size: int
    total_memories: Optional[int] = None

@dataclass
class ChatResponse:
    """聊天响应数据模型"""
    content: str
    user_id: str
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    memory_used: bool = False
    memories_count: int = 0
    collaborators: List[str] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class ContextPayload:
    """
    LLM 上下文内容，用于统一封装系统提示、对话历史和记忆状态。
    """
    messages: List[Dict[str, str]]
    memory_used: bool
    memories_count: int
    agent_id: str
    session_id: str
    collaborators: List[str]

@dataclass
class SpecialistResult:
    """单个专家代理在某次项目任务中的输出。"""
    agent_id: str
    content: str

@dataclass
class MultiAgentResult:
    """多代理协作的整体汇总。"""
    project_summary: str
    selected_agents: List[str]
    specialist_outputs: List[SpecialistResult]
    final_response: ChatResponse

class ConversationCache:
    """对话缓存管理"""
    
    def __init__(self, max_size: int = 5):
        self._cache = {}
        self.max_size = max_size
    
    def get_user_cache(self, user_id: str) -> deque:
        """获取用户对话缓存"""
        if user_id not in self._cache:
            self._cache[user_id] = deque(maxlen=self.max_size)
        return self._cache[user_id]
    
    def add_message(self, user_id: str, message: ChatMessage):
        """添加消息到缓存"""
        cache = self.get_user_cache(user_id)
        cache.append(message.to_dict())
    
    def get_messages(self, user_id: str) -> List[Dict[str, str]]:
        """获取用户所有缓存消息"""
        return list(self.get_user_cache(user_id))
    
    def get_recent_messages(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取指定数量的最新消息，用于构建上下文窗口。
        """
        messages = self.get_messages(user_id)
        if limit is None or limit <= 0:
            return messages
        return messages[-limit:]
    
    def clear(self, user_id: str):
        """清空用户缓存"""
        if user_id in self._cache:
            self._cache[user_id].clear()
    
    def get_stats(self, user_id: str) -> ConversationStats:
        """获取缓存统计"""
        cache = self.get_user_cache(user_id)
        return ConversationStats(
            user_id=user_id,
            cached_conversations=len(cache),
            cache_max_size=self.max_size
        )