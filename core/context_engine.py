#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文编排器：负责将长期记忆、协作代理洞见以及近期对话组合成统一提示。
"""

from typing import List, Dict, Optional

from config.settings import Config
from models.data_models import ContextPayload
from core.memory_manager import MemoryManager


class ContextOrchestrator:
    """负责上下文工程的核心类。"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.max_history = Config.CONTEXT_PIPELINE.get(
            "max_history_messages",
            Config.CONVERSATION_CACHE_SIZE
        )
        self.include_summary = Config.CONTEXT_PIPELINE.get(
            "include_dialogue_summary",
            True
        )
        self.max_collaborators = Config.CONTEXT_PIPELINE.get("max_collaborators", 0)
    
    def build_payload(
        self,
        user_id: str,
        agent_id: str,
        session_id: str,
        user_message: str,
        cached_messages: List[Dict[str, str]],
        extra_context: Optional[str] = None,
        memory_type: Optional[str] = None,  # 新增参数
        memory_metadata: Optional[Dict] = None,  # 新增参数
        expert_domain: Optional[str] = None  # 专家领域参数
    ) -> ContextPayload:
        """
        构建LLM上下文内容
        
        Args:
            user_id: 用户ID
            agent_id: 智能体ID
            session_id: 会话ID
            user_message: 用户消息
            cached_messages: 缓存的对话历史消息
            extra_context: 额外上下文
            memory_type: 记忆类型（user/expert/project）
            memory_metadata: 记忆元数据
            expert_domain: 专家领域（从代理配置获取默认值）
            
        Returns:
            上下文载体对象
        """
        try:
            # 打印调试信息
            print(f"调试 - 构建上下文: agent_id={agent_id}, memory_type={memory_type}")
            
            # 获取代理配置以确定专家领域
            agent_config = self._get_agent_config(agent_id)
            expert_domain = expert_domain or agent_config.get("domain")
            
            # 构建系统提示
            system_prompt = self._compose_system_prompt(
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id,
                expert_domain=expert_domain,
                memory_metadata=memory_metadata
            )
            
            # 获取代理配置
            agent_profile = Config.AGENT_PROFILES.get(agent_id, {"name": agent_id})
            expert_domain = expert_domain or agent_profile.get("expert_domain")
            collaborators = agent_profile.get("collaborators", [])
            
            if self.max_collaborators > 0:
                collaborators = collaborators[: self.max_collaborators]
            
            # 组合记忆上下文
            memory_context = ""
            
            # 获取用户记忆上下文
            user_memory_context = self._get_user_memory_context(user_id, user_message)
            if user_memory_context:
                memory_context += f"用户记忆信息:\n{user_memory_context}\n\n"
            
            # 根据记忆类型获取不同的记忆上下文
            if memory_type == "expert" and expert_domain:
                # 获取专家特定记忆
                expert_memory_context = self._get_expert_memory_context(
                    user_id=user_id,
                    agent_id=agent_id,
                    query=user_message,
                    expert_domain=expert_domain,
                    memory_metadata=memory_metadata
                )
                if expert_memory_context:
                    memory_context += f"专家领域相关记忆:\n{expert_memory_context}\n\n"
            elif memory_type == "project":
                # 获取项目记忆
                project_memory_context = self._get_project_memory_context(
                    user_id=user_id,
                    session_id=session_id,
                    query=user_message
                )
                if project_memory_context:
                    memory_context += f"项目相关记忆:\n{project_memory_context}\n\n"
            
            # 获取协作上下文（仅对项目大脑）
            collaborative_context = ""
            if agent_id == "project_brain":
                collaborators = [agent for agent in Config.AGENT_PROFILES.keys() 
                               if agent != "project_brain"]
                collaborative_context = self._get_collaborative_context(
                    query=user_message,
                    user_id=user_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    collaborators=collaborators,
                    expert_domain=expert_domain
                )
            
            # 裁剪对话历史并验证消息格式
            trimmed_history = self._trim_history(cached_messages)
            
            # 构建消息列表
            messages = []
            
            # 系统提示消息
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # 如果有记忆上下文，添加到消息中
            if memory_context:
                messages.append({"role": "system", "content": f"<记忆上下文>\n{memory_context}</记忆上下文>"})
            
            # 如果有协作上下文，添加到消息中
            if collaborative_context:
                messages.append({"role": "system", "content": f"<协作上下文>\n{collaborative_context}</协作上下文>"})
            
            # 添加额外上下文
            if extra_context:
                messages.append({"role": "system", "content": extra_context})
            
            # 添加裁剪后的历史消息（确保每条消息都有role字段）
            for msg in trimmed_history:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append(msg)
                else:
                    print(f"警告 - 忽略格式错误的历史消息: {msg}")
            
            # 添加用户当前消息
            messages.append({"role": "user", "content": user_message})
            
            # 验证所有消息格式
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    print(f"严重错误 - 消息 {i} 不是字典类型: {type(msg)}")
                    # 替换为有效的消息
                    messages[i] = {"role": "system", "content": str(msg)}
                elif 'role' not in msg:
                    print(f"严重错误 - 消息 {i} 缺少'role'字段: {msg}")
                    # 修复消息
                    messages[i] = {"role": "system", "content": msg.get('content', '')}
                elif 'content' not in msg:
                    print(f"严重错误 - 消息 {i} 缺少'content'字段: {msg}")
                    # 修复消息
                    messages[i]['content'] = ''
            
            print(f"调试 - 最终消息数量: {len(messages)}")
            
            # 创建上下文载体
            return ContextPayload(
                messages=messages,
                memory_used=bool(memory_context),
                memories_count=len(memory_context.split("\n\n")) if memory_context else 0,
                agent_id=agent_id,
                session_id=session_id,
                collaborators=collaborators
            )
        except Exception as e:
            # 捕获所有异常并打印详细信息
            print(f"构建上下文时发生异常: {str(e)}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            
            # 返回一个最小化的有效上下文，以便系统可以继续运行
            minimal_messages = [
                {"role": "system", "content": f"智能体 {agent_id} 的上下文构建失败，但仍需响应。"},
                {"role": "user", "content": user_message}
            ]
            
            return ContextPayload(
                messages=minimal_messages,
                memory_used=False,
                memories_count=0,
                agent_id=agent_id,
                session_id=session_id,
                collaborators=[]
            )
    
    def _compose_system_prompt(
        self,
        user_id: str,
        agent_id: str,
        session_id: str,
        expert_domain: Optional[str] = None,
        memory_metadata: Optional[Dict] = None
    ) -> str:
        """
        组合系统提示
        
        Args:
            user_id: 用户ID
            agent_id: 智能体ID
            session_id: 会话ID
            expert_domain: 专家领域
            memory_metadata: 记忆元数据
            
        Returns:
            系统提示字符串
        """
        try:
            agent_config = self._get_agent_config(agent_id)
            
            # 基本信息 - 使用get方法安全访问字段
            system_prompt = []
            # 安全获取name和role字段，提供默认值
            agent_name = agent_config.get('name', agent_id)
            agent_role = agent_config.get('role', '智能助手')
            system_prompt.append(f"你是{agent_name}，{agent_role}")
            
            # 安全获取instruction字段
            if agent_config.get('instruction'):
                system_prompt.append(agent_config.get('instruction'))
            
            # 添加专家领域相关信息
            if expert_domain:
                system_prompt.append(f"\n## 专业领域")
                system_prompt.append(f"你专注于{expert_domain}领域的专业知识。")
                
                # 根据专家类型添加特定回复准则
                if "product" in expert_domain.lower():
                    system_prompt.append("\n## 回复准则")
                    system_prompt.append("- 注重用户体验和产品价值")
                    system_prompt.append("- 提供具体、可落地的产品建议")
                    system_prompt.append("- 考虑市场和商业价值")
                elif "algorithm" in expert_domain.lower():
                    system_prompt.append("\n## 回复准则")
                    system_prompt.append("- 注重算法的可行性和效率")
                    system_prompt.append("- 提供技术细节和实现思路")
                    system_prompt.append("- 考虑计算资源和性能优化")
                elif "architecture" in expert_domain.lower():
                    system_prompt.append("\n## 回复准则")
                    system_prompt.append("- 注重系统的可扩展性和稳定性")
                    system_prompt.append("- 提供整体架构设计和组件划分")
                    system_prompt.append("- 考虑技术栈选型和集成方案")
            
            # 添加记忆相关信息
            if memory_metadata:
                memory_type = memory_metadata.get('memory_type')
                if memory_type == 'expert':
                    system_prompt.append("\n## 记忆访问")
                    system_prompt.append("你可以访问特定领域的专家记忆，这些记忆可以帮助你提供更专业的回答。")
                elif memory_type == 'project':
                    system_prompt.append("\n## 记忆访问")
                    system_prompt.append("你可以访问项目相关记忆，了解项目历史和上下文。")
            
            # 添加通用回复格式要求
            system_prompt.append("\n## 回复格式")
            system_prompt.append("请提供结构化、条理清晰的回复，使用适当的标题和列表。")
            
            return "\n".join(system_prompt)
        except Exception as e:
            print(f"组合系统提示时发生异常: {str(e)}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            # 返回一个安全的默认系统提示
            return f"你是{agent_id}，一个智能助手。请根据用户的问题提供专业、有用的回答。"
    
    def _trim_history(self, cached_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """裁剪对话历史，避免提示超限，并确保每条消息都有'role'字段。"""
        if self.max_history <= 0:
            trimmed = cached_messages
        else:
            trimmed = cached_messages[-self.max_history :]
        
        # 确保每条消息都有'role'字段
        validated_messages = []
        for message in trimmed:
            if isinstance(message, dict):
                if 'role' not in message:
                    # 为缺少role字段的消息设置默认值
                    message = message.copy()
                    message['role'] = 'system'  # 默认设为system角色
                validated_messages.append(message)
        
        return validated_messages
    
    def _summarize_dialogue(self, cached_messages: List[Dict[str, str]]) -> str:
        """将最近对话转换为要点，帮助 LLM 快速把握主题。"""
        if not cached_messages:
            return "暂无历史上下文。"
        
        recent = cached_messages[-self.max_history :]
        lines = []
        for message in recent:
            role = "用户" if message.get("role") == "user" else "助手"
            content = message.get("content", "").strip()
            if content:
                lines.append(f"- {role}: {content}")
        return "\n".join(lines) if lines else "暂无历史上下文。"
    
    def _get_agent_config(self, agent_id: str) -> Dict[str, str]:
        """
        获取代理配置
        
        Args:
            agent_id: 代理ID
            
        Returns:
            代理配置字典
        """
        return Config.AGENT_PROFILES.get(agent_id, {
            "name": agent_id,
            "role": "智能助手",
            "instruction": """你是一个专业的AI助手，帮助用户解决问题。"""
        })
    
    def _get_user_memory_context(self, user_id: str, query: str) -> str:
        """
        获取用户相关记忆上下文
        
        Args:
            user_id: 用户ID
            query: 用户查询
            
        Returns:
            格式化的用户记忆上下文字符串
        """
        try:
            # 改回使用search_memories方法
            user_memories = self.memory_manager.search_memories(
                user_id=user_id,
                query=query,
                memory_type="user",
                limit=Config.MEMORY_SEARCH_LIMIT
            )
            
            if not user_memories:
                return ""
            
            # 检查user_memories类型并处理
            memories_to_process = []
            if isinstance(user_memories, dict):
                # 如果是字典，提取其值作为记忆列表
                memories_to_process = list(user_memories.values())
            elif isinstance(user_memories, list):
                # 如果是列表，直接使用
                memories_to_process = user_memories
            else:
                # 其他类型，尝试转换为字符串列表
                try:
                    memories_to_process = [str(user_memories)]
                except:
                    print(f"警告: 无法处理的用户记忆类型: {type(user_memories)}")
                    return ""
            
            # 格式化用户记忆，最多返回3条
            memory_lines = []
            for i, memory in enumerate(memories_to_process[:3], 1):  # 最多返回3条
                # 确保memory是字典类型
                if isinstance(memory, dict):
                    content = memory.get('content', '')
                    timestamp = memory.get('created_at', '')
                    if content:
                        memory_lines.append(f"{i}. {content}")
                        if timestamp:
                            memory_lines[-1] += f" (时间: {timestamp})"
                else:
                    # 如果不是字典，尝试将整个对象作为内容
                    try:
                        memory_lines.append(f"{i}. {str(memory)}")
                    except:
                        pass
            
            return "\n".join(memory_lines)
        except Exception as e:
            print(f"获取用户记忆上下文时发生异常: {str(e)}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            return ""
    
    def _get_expert_memory_context(
        self,
        user_id: str,
        agent_id: str,
        query: str,
        expert_domain: str,
        memory_metadata: Optional[Dict] = None
    ) -> str:
        """
        获取专家领域相关记忆上下文
        
        Args:
            user_id: 用户ID
            agent_id: 智能体ID
            query: 查询内容
            expert_domain: 专家领域
            memory_metadata: 记忆元数据
            
        Returns:
            格式化的专家记忆字符串
        """
        expert_memories = self.memory_manager.search_memories(
            user_id=user_id,
            query=query,
            agent_id=agent_id,
            memory_type="expert",
            expert_domain=expert_domain,
            metadata=memory_metadata,
            limit=Config.MEMORY_SEARCH_LIMIT
        )
        
        if not expert_memories:
            return ""
        
        # 格式化专家记忆
        memory_lines = []
        for i, memory in enumerate(expert_memories[:5], 1):  # 最多返回5条
            content = memory.get('content', '')
            if content:
                memory_lines.append(f"{i}. {content}")
        
        return "\n".join(memory_lines)
    
    def _get_project_memory_context(self, user_id: str, session_id: str, query: str) -> str:
        """
        获取项目相关记忆上下文
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            query: 查询内容
            
        Returns:
            格式化的项目记忆字符串
        """
        project_memories = self.memory_manager.search_memories(
            user_id=user_id,
            session_id=session_id,
            query=query,
            agent_id="project_brain",
            memory_type="project",
            limit=Config.MEMORY_SEARCH_LIMIT
        )
        
        if not project_memories:
            return ""
        
        # 格式化项目记忆
        memory_lines = []
        for i, memory in enumerate(project_memories[:5], 1):  # 最多返回5条
            content = memory.get('content', '')
            if content:
                memory_lines.append(f"{i}. {content}")
        
        return "\n".join(memory_lines)
    
    def _get_collaborative_context(
        self,
        query: str,
        user_id: str,
        agent_id: str,
        session_id: str,
        collaborators: List[str],
        expert_domain: Optional[str] = None
    ) -> str:
        """
        获取协作上下文
        
        Args:
            query: 查询内容
            user_id: 用户ID
            agent_id: 智能体ID
            session_id: 会话ID
            collaborators: 协作者列表
            expert_domain: 专家领域（可选，用于过滤）
            
        Returns:
            格式化的协作上下文字符串
        """
        collaborative_data = self.memory_manager.get_collaborative_context(
            query=query,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            collaborators=collaborators,
            limit=Config.MEMORY_SEARCH_LIMIT
        )
        
        # 如果指定了专家领域，过滤相关记忆
        if expert_domain and collaborative_data.get('formatted'):
            # 简单实现：过滤包含专家领域关键词的记忆
            filtered_lines = []
            keywords = expert_domain.lower().split()
            for line in collaborative_data['formatted'].split('\n'):
                if any(keyword in line.lower() for keyword in keywords):
                    filtered_lines.append(line)
            return '\n'.join(filtered_lines)
        
        return collaborative_data.get('formatted', '')

