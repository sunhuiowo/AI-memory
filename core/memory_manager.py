#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统管理
"""
# pylint: disable=broad-except

import inspect
import logging
from mem0 import Memory
from typing import Dict, List, Any, Optional, Iterable, Tuple

from config.settings import Config

logger = logging.getLogger(__name__)

class MemoryManager:
    """记忆系统管理器"""
    
    def __init__(self):
        self.memory = self._initialize_memory()
        self.capabilities = self._detect_capabilities()
        logger.info("记忆管理器初始化成功")
    
    def _initialize_memory(self) -> Memory:
        """初始化记忆系统"""
        try:
            memory_config = Config.get_memory_config()
            return Memory.from_config(memory_config)
        except Exception as exc:  # noqa: BLE001 - 底层可能抛出任意异常
            logger.error("记忆系统初始化失败: %s", exc)
            raise
    
    def _detect_capabilities(self) -> Dict[str, bool]:
        """探测当前 mem0 版本是否支持 agent/session 关键字。"""
        return {
            "search_agent": self._supports_parameter(self.memory.search, "agent_id"),
            "search_session": self._supports_parameter(self.memory.search, "session_id"),
            "add_agent": self._supports_parameter(self.memory.add, "agent_id"),
            "add_session": self._supports_parameter(self.memory.add, "session_id"),
            "get_all_agent": self._supports_parameter(self.memory.get_all, "agent_id"),
            "get_all_session": self._supports_parameter(self.memory.get_all, "session_id")
        }
    
    @staticmethod
    def _supports_parameter(method, parameter_name: str) -> bool:
        """检查方法签名中是否包含指定参数。"""
        try:
            signature = inspect.signature(method)
            return parameter_name in signature.parameters
        except (ValueError, TypeError):
            return False
    
    def search_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        expert_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        搜索相关记忆，支持按记忆类型和专家领域过滤
        
        Args:
            query: 搜索查询
            user_id: 用户ID
            limit: 返回结果数量限制
            agent_id: 代理ID
            session_id: 会话ID
            memory_type: 记忆类型过滤，可选值: 'user', 'expert', 'project', 'general'
            expert_domain: 专家领域过滤，可选值: 'product', 'algorithm', 'architecture'
            
        Returns:
            记忆搜索结果
        """
        try:
            params = {
                "query": query,
                "user_id": user_id,
                "limit": limit
            }
            if agent_id and self.capabilities["search_agent"]:
                params["agent_id"] = agent_id
            if session_id and self.capabilities["search_session"]:
                params["session_id"] = session_id
            
            # 构建过滤条件
            filters = {}
            if memory_type:
                filters["metadata.memory_type"] = memory_type
            if expert_domain:
                filters["metadata.expert_domain"] = expert_domain
            
            # 添加过滤条件到params（如果支持）
            if filters and hasattr(self.memory.search, '__code__') and 'filters' in inspect.signature(self.memory.search).parameters:
                params["filters"] = filters
            
            search_results = self.memory.search(**params)
            
            # 检查返回结果格式，确保它是预期的字典格式
            if isinstance(search_results, dict):
                # 确保results键存在且为列表
                if "results" not in search_results:
                    search_results["results"] = []
                return search_results
            else:
                # 如果返回格式不是字典，转换为标准格式
                logger.warning("搜索结果格式不符合预期，进行转换")
                # 尝试将结果转换为标准格式
                if isinstance(search_results, list):
                    return {"results": search_results}
                return {"results": []}
                
        except Exception as exc:  # noqa: BLE001
            logger.error("记忆搜索失败: %s", exc)
            # 尝试使用备选搜索方法或参数
            try:
                # 尝试简化查询参数
                simplified_params = {
                    "query": query,
                    "user_id": user_id
                }
                fallback_results = self.memory.search(**simplified_params)
                if isinstance(fallback_results, dict) and "results" in fallback_results:
                    return fallback_results
                return {"results": [] if not isinstance(fallback_results, list) else fallback_results}
            except Exception as fallback_exc:
                logger.error("备选搜索也失败: %s", fallback_exc)
                return {"results": []}
    
    def add_conversation(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: str = "general"
    ) -> bool:
        """
        添加对话到记忆
        
        Args:
            messages: 消息列表
            user_id: 用户ID
            agent_id: 代理ID
            session_id: 会话ID
            memory_type: 记忆类型，可选值: 'general', 'user', 'expert', 'project'
            
        Returns:
            是否成功添加
        """
        success = False
        
        # 根据agent_id和memory_type自动确定记忆类型
        final_memory_type = memory_type
        if not final_memory_type:
            if agent_id == "project_brain":
                final_memory_type = "project"
            elif agent_id in Config.AGENT_PROFILES:
                final_memory_type = "expert"
            else:
                final_memory_type = "user"
        
        # 始终以“用户级”维度存储，确保记忆与代理解耦
        success |= self._store_memory(messages, user_id=user_id, session_id=session_id, memory_type=final_memory_type)
        
        # 仅在底层支持、且明确指定代理时，再写入代理专属记忆
        if agent_id and self.capabilities["add_agent"]:
            success |= self._store_memory(
                messages,
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id,
                memory_type=final_memory_type
            )
        return success
        
    def add_user_memory(self, messages: List[Dict[str, str]], user_id: str, session_id: Optional[str] = None) -> bool:
        """
        添加用户专属记忆
        
        Args:
            messages: 消息列表
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            是否成功添加
        """
        return self.add_conversation(messages, user_id=user_id, session_id=session_id, memory_type="user")
        
    def add_expert_memory(self, messages: List[Dict[str, str]], user_id: str, expert_id: str, session_id: Optional[str] = None) -> bool:
        """
        添加专家专属记忆
        
        Args:
            messages: 消息列表
            user_id: 用户ID
            expert_id: 专家ID
            session_id: 会话ID
            
        Returns:
            是否成功添加
        """
        return self.add_conversation(messages, user_id=user_id, agent_id=expert_id, session_id=session_id, memory_type="expert")
        
    def add_project_memory(self, messages: List[Dict[str, str]], user_id: str, project_id: str, session_id: Optional[str] = None) -> bool:
        """
        添加项目专属记忆
        
        Args:
            messages: 消息列表
            user_id: 用户ID
            project_id: 项目ID
            session_id: 会话ID
            
        Returns:
            是否成功添加
        """
        return self.add_conversation(messages, user_id=user_id, agent_id=project_id, session_id=session_id, memory_type="project")
    
    def _store_memory(
        self,
        messages: List[Dict[str, str]],
        *,
        user_id: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: str = "general"
    ) -> bool:
        """封装底层 add 调用，按需附加 agent/session 和记忆类型标识。"""
        try:
            params = {"user_id": user_id}
            if agent_id:
                params["agent_id"] = agent_id
            if session_id and self.capabilities["add_session"]:
                params["session_id"] = session_id
            
            # 添加记忆类型标识和专家领域信息
            metadata = {
                "role": "user",  # 默认角色
                "user_id": user_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "memory_type": memory_type
            }
            
            # 根据不同的角色和记忆类型添加额外的metadata
            if agent_id == "project_brain":
                metadata["is_project_memory"] = True
            elif agent_id in Config.AGENT_PROFILES:
                metadata["is_expert_memory"] = True
                # 记录专家类型
                if agent_id == "product_lead":
                    metadata["expert_domain"] = "product"
                elif agent_id == "algo_scientist":
                    metadata["expert_domain"] = "algorithm"
                elif agent_id == "solution_architect":
                    metadata["expert_domain"] = "architecture"
            
            # 处理单个消息的情况，确保格式正确
            if len(messages) == 1 and isinstance(messages[0], dict):
                # 对于单个消息，使用正确的格式以避免向量验证错误
                memory_data = {
                    "text": messages[0].get("content", ""),
                    "metadata": {**metadata, "role": messages[0].get("role", "user")}
                }
                self.memory.add(memory_data, **params)
            else:
                # 对于多条消息，为每条消息添加metadata
                enriched_messages = []
                for msg in messages:
                    enriched_msg = {
                        "text": msg.get("content", ""),
                        "metadata": {**metadata, "role": msg.get("role", "user")}
                    }
                    enriched_messages.append(enriched_msg)
                self.memory.add(enriched_messages, **params)
            
            scope = f"user={user_id}, agent={agent_id or 'user_scope'}, type={memory_type}"
            logger.info("记忆已写入 (%s)", scope)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("记忆保存失败 (%s): %s", agent_id or "user_scope", exc)
            # 尝试使用更简单的格式作为备选方案
            try:
                # 尝试使用简化的格式
                simple_memory = {
                    "text": " ".join([msg.get("content", "") for msg in messages]),
                    "metadata": {"memory_type": memory_type, "agent_id": agent_id}
                }
                self.memory.add(simple_memory, **params)
                logger.info("使用简化格式成功保存记忆 (%s)", scope)
                return True
            except Exception as fallback_exc:
                logger.error("备选方案也失败: %s", fallback_exc)
                return False
    
    def get_memory_context(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        expert_domain: Optional[str] = None
    ) -> str:
        """
        获取记忆上下文字符串，支持按记忆类型和专家领域过滤
        
        Args:
            query: 查询内容
            user_id: 用户ID
            limit: 记忆数量限制
            agent_id: 代理ID
            session_id: 会话ID
            memory_type: 记忆类型过滤
            expert_domain: 专家领域过滤
            
        Returns:
            格式化的记忆上下文
        """
        memories = self.search_memories(
            query=query,
            user_id=user_id,
            limit=limit,
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type,
            expert_domain=expert_domain
        )
        
        if memories["results"]:
            memory_parts = []
            for idx, entry in enumerate(memories["results"]):
                # 尝试获取不同格式的记忆内容
                content = entry.get("memory") or entry.get("content") or entry.get("text") or ""
                
                # 获取元数据信息
                metadata = entry.get("metadata", {})
                memory_type_str = metadata.get("memory_type", "general")
                agent_info = metadata.get("agent_id", "")
                domain_info = metadata.get("expert_domain", "")
                
                # 构建记忆标签
                tags = []
                if memory_type_str != "general":
                    tags.append(memory_type_str)
                if agent_info:
                    tags.append(f"agent:{agent_info}")
                if domain_info:
                    tags.append(f"domain:{domain_info}")
                
                tag_str = f"[{', '.join(tags)}]" if tags else ""
                memory_parts.append(f"- {tag_str} {content}")
            
            memories_str = "\n".join(memory_parts)
            
            # 添加上下文标题
            context_title = "相关记忆"
            if memory_type:
                context_title += f" ({memory_type}类型)"
            if agent_id:
                context_title += f" - {agent_id}"
            
            return f"{context_title}：\n{memories_str}"
        else:
            return "暂无相关记忆"
            
    def get_user_memory_context(self, query: str, user_id: str, limit: int = 5) -> str:
        """
        获取用户专属记忆上下文
        
        Args:
            query: 查询内容
            user_id: 用户ID
            limit: 记忆数量限制
            
        Returns:
            格式化的用户记忆上下文
        """
        return self.get_memory_context(
            query=query,
            user_id=user_id,
            limit=limit,
            memory_type="user"
        )
        
    def get_expert_memory_context(self, query: str, user_id: str, expert_id: str, limit: int = 5) -> str:
        """
        获取专家专属记忆上下文
        
        Args:
            query: 查询内容
            user_id: 用户ID
            expert_id: 专家ID
            limit: 记忆数量限制
            
        Returns:
            格式化的专家记忆上下文
        """
        # 根据专家ID确定领域
        expert_domain = None
        if expert_id == "product_lead":
            expert_domain = "product"
        elif expert_id == "algo_scientist":
            expert_domain = "algorithm"
        elif expert_id == "solution_architect":
            expert_domain = "architecture"
            
        return self.get_memory_context(
            query=query,
            user_id=user_id,
            agent_id=expert_id,
            limit=limit,
            memory_type="expert",
            expert_domain=expert_domain
        )
        
    def get_project_memory_context(self, query: str, user_id: str, project_id: str, limit: int = 5) -> str:
        """
        获取项目专属记忆上下文
        
        Args:
            query: 查询内容
            user_id: 用户ID
            project_id: 项目ID
            limit: 记忆数量限制
            
        Returns:
            格式化的项目记忆上下文
        """
        return self.get_memory_context(
            query=query,
            user_id=user_id,
            agent_id=project_id,
            limit=limit,
            memory_type="project"
        )
    
    def get_all_memories(
        self,
        user_id: str,
        limit: int = 100,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        expert_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户所有记忆，支持按记忆类型和专家领域过滤
        
        Args:
            user_id: 用户ID
            limit: 返回结果数量限制
            agent_id: 代理ID
            session_id: 会话ID
            memory_type: 记忆类型过滤
            expert_domain: 专家领域过滤
            
        Returns:
            记忆列表结果
        """
        try:
            params = {"user_id": user_id, "limit": limit}
            if agent_id and self.capabilities["get_all_agent"]:
                params["agent_id"] = agent_id
            if session_id and self.capabilities["get_all_session"]:
                params["session_id"] = session_id
            
            # 构建过滤条件
            filters = {}
            if memory_type:
                filters["metadata.memory_type"] = memory_type
            if expert_domain:
                filters["metadata.expert_domain"] = expert_domain
            
            # 添加过滤条件到params（如果支持）
            if filters and hasattr(self.memory.get_all, '__code__') and 'filters' in inspect.signature(self.memory.get_all).parameters:
                params["filters"] = filters
            
            all_memories = self.memory.get_all(**params)
            
            # 检查返回结果格式，确保它是预期的字典格式
            if isinstance(all_memories, dict):
                # 确保results键存在且为列表
                if "results" not in all_memories:
                    all_memories["results"] = []
                return all_memories
            else:
                # 如果返回格式不是字典，转换为标准格式
                logger.warning("获取所有记忆结果格式不符合预期，进行转换")
                # 尝试将结果转换为标准格式
                if isinstance(all_memories, list):
                    return {"results": all_memories}
                return {"results": []}
                
        except Exception as exc:  # noqa: BLE001
            logger.error("获取记忆列表失败: %s", exc)
            # 尝试使用备选方法
            try:
                # 尝试简化参数
                simplified_params = {"user_id": user_id}
                fallback_memories = self.memory.get_all(**simplified_params)
                if isinstance(fallback_memories, dict) and "results" in fallback_memories:
                    return fallback_memories
                return {"results": [] if not isinstance(fallback_memories, list) else fallback_memories}
            except Exception as fallback_exc:
                logger.error("备选获取方法也失败: %s", fallback_exc)
                return {"results": []}

    def get_collaborative_context(
        self,
        query: str,
        user_id: str,
        agent_id: str,
        session_id: Optional[str],
        collaborators: Optional[Iterable[str]],
        limit: int
    ) -> Dict[str, Any]:
        """
        组合主代理与协作代理的记忆，用于上下文工程，支持按记忆类型组织。
        """
        memory_sections: List[str] = []
        total_hits = 0
        
        # 先检索用户专属记忆
        user_results = self.search_memories(query, user_id, limit, None, session_id, memory_type="user")
        section_text, hits = self._format_memory_results("用户", user_results.get("results", []))
        if hits:
            memory_sections.append(section_text)
            total_hits += hits
        
        # 主代理记忆（根据代理类型使用相应的记忆类型）
        memory_type = "project" if agent_id == "project_brain" else "expert"
        primary_results = self.search_memories(query, user_id, limit, agent_id, session_id, memory_type=memory_type)
        section_text, hits = self._format_memory_results(agent_id, primary_results.get("results", []))
        if hits:
            memory_sections.append(section_text)
            total_hits += hits
        
        # 按专家领域分组协作者记忆
        domain_memories = {
            "product": {"name": "产品专家", "results": []},
            "algorithm": {"name": "算法专家", "results": []},
            "architecture": {"name": "架构师", "results": []},
            "general": {"name": "其他专家", "results": []}
        }
        
        if collaborators:
            for collaborator in collaborators:
                # 确定专家领域
                domain = "general"
                if collaborator == "product_lead":
                    domain = "product"
                elif collaborator == "algo_scientist":
                    domain = "algorithm"
                elif collaborator == "solution_architect":
                    domain = "architecture"
                
                # 获取专家记忆
                collaborator_results = self.search_memories(
                    query,
                    user_id,
                    limit,
                    collaborator,
                    session_id,
                    memory_type="expert"
                )
                
                # 添加到对应领域
                domain_memories[domain]["results"].extend(collaborator_results.get("results", []))
        
        # 按领域格式化协作者记忆
        expert_sections = []
        for domain, info in domain_memories.items():
            if info["results"]:
                section_text, hits = self._format_memory_results(info["name"], info["results"])
                expert_sections.append(section_text)
                total_hits += hits
        
        # 添加专家部分到记忆章节
        if expert_sections:
            memory_sections.append("### 专家见解汇总：")
            memory_sections.extend(expert_sections)
        
        # 生成综合建议
        comprehensive_results = self.search_memories(
            query,
            user_id,
            limit * 2,  # 获取更多结果用于综合
            None,  # 不限制特定代理
            session_id
        )
        
        if comprehensive_results.get("results", []):
            # 提取最相关的见解作为综合建议
            suggestions = []
            seen_content = set()
            for entry in comprehensive_results["results"][:limit]:
                content = entry.get("memory") or entry.get("content") or ""
                if content and content not in seen_content:
                    seen_content.add(content)
                    suggestions.append(content)
            
            if suggestions:
                memory_sections.append("\n### 综合建议：")
                memory_sections.extend([f"- {suggestion}" for suggestion in suggestions])
        
        formatted = "\n\n".join(memory_sections) if memory_sections else "暂无相关记忆"
        return {
            "formatted": formatted,
            "memory_used": total_hits > 0,
            "memories_count": total_hits
        }
    
    def _format_memory_results(self, agent_id: str, results: List[Dict[str, Any]]) -> Tuple[str, int]:
        """
        将指定代理的记忆结果格式化为文本块，增强元数据展示。
        """
        if not results:
            return "", 0
        
        lines = [
            f"### {agent_id} 的记忆片段："
        ]
        
        # 按相关性排序（如果有score字段）
        sorted_results = sorted(
            results,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        for entry in sorted_results:
            # 获取记忆内容，尝试多种可能的字段名
            memory_text = entry.get("memory") or entry.get("content") or entry.get("text") or ""
            if not memory_text:
                continue
            
            # 获取元数据信息
            metadata = entry.get("metadata", {})
            memory_type = metadata.get("memory_type", "general")
            score = entry.get("score", "")
            
            # 构建标签
            tags = []
            if memory_type != "general":
                tags.append(f"[{memory_type}]")
            if score and isinstance(score, (int, float)):
                tags.append(f"[相关度: {score:.2f}]")
            
            tag_str = " ".join(tags)
            lines.append(f"- {tag_str} {memory_text}")
            
        return "\n".join(lines), len(results)

    def store_memory(
        self,
        content: str,
        user_id: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: str = "general",
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        公共方法：存储记忆内容
        
        Args:
            content: 记忆内容
            user_id: 用户ID
            agent_id: 代理ID
            session_id: 会话ID
            memory_type: 记忆类型
            metadata: 额外元数据
            
        Returns:
            是否成功存储
        """
        try:
            # 创建标准消息格式
            message = {
                "role": "assistant",  # 默认角色
                "content": content
            }
            
            # 调用私有方法_store_memory处理实际存储
            result = self._store_memory(
                messages=[message],
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id,
                memory_type=memory_type
            )
            
            # 如果提供了额外metadata，这里可以添加处理逻辑
            if metadata and result:
                logger.info("记忆存储成功，并附加了额外元数据")
            
            return result
        except Exception as e:
            logger.error(f"调用store_memory时发生异常: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return False