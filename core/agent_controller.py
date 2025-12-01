#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多代理协作控制器：负责项目大脑与专家大脑的编排。
"""

from typing import Dict, List, Optional, Any

from config.settings import Config
from core.chat_engine import ChatEngine
from models.data_models import MultiAgentResult, SpecialistResult, ChatResponse


class AgentSelector:
    """基于关键词打分的简单专家路由器。"""
    
    def __init__(self, agent_profiles: Dict[str, Dict]):
        self.agent_profiles = agent_profiles
        pipeline_conf = Config.MULTI_AGENT_PIPELINE
        self.max_specialists = pipeline_conf.get("max_specialists", 3)
        self.fallback_specialists = pipeline_conf.get("fallback_specialists", [])
    
    def select_specialists(self, message: str) -> List[str]:
        """根据用户输入选择合适的专家代理。"""
        lowered = message.lower()
        scored: List[tuple[str, int]] = []
        for agent_id, profile in self.agent_profiles.items():
            if profile.get("type") != "specialist":
                continue
            keywords = profile.get("expertise_keywords", [])
            score = sum(lowered.count(keyword.lower()) for keyword in keywords)
            scored.append((agent_id, score))
        
        scored.sort(key=lambda item: item[1], reverse=True)
        selected = [agent_id for agent_id, score in scored if score > 0][: self.max_specialists]
        
        if not selected:
            selected = self.fallback_specialists[: self.max_specialists]
        
        return selected


class MultiAgentController:
    """封装 AI 项目管理流程，负责驱动项目大脑 + 专家大脑。"""
    
    def __init__(self, chat_engine: ChatEngine):
        self.chat_engine = chat_engine
        self.selector = AgentSelector(Config.AGENT_PROFILES)
        self.project_brain_id = Config.PROJECT_BRAIN_ID
    
    def process_user_message(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        target_agent: Optional[str] = None
    ) -> MultiAgentResult:
        """执行消息处理流程，支持直接调用特定专家大脑或使用项目大脑整合流程。"""
        # 直接调用专家大脑模式
        if target_agent and target_agent != self.project_brain_id and target_agent in Config.AGENT_PROFILES:
            # 获取专家特定的记忆上下文
            extra_context = self._get_expert_memory_context(user_id, target_agent)
            
            # 构建专家prompt
            prompt = self._build_specialist_prompt(target_agent, user_message, "")
            
            # 调用专家代理
            response = self._call_agent(
                agent_id=target_agent,
                prompt=prompt,
                user_id=user_id,
                session_id=session_id,
                persist_history=True,
                extra_context=extra_context,
                memory_type="expert"  # 指定为专家记忆
            )
            
            # 包装为MultiAgentResult以保持接口一致性
            return MultiAgentResult(
                project_summary="",
                selected_agents=[target_agent],
                specialist_outputs=[SpecialistResult(agent_id=target_agent, content=response.content)],
                final_response=response
            )
        
        # 默认使用项目大脑整合流程
        # 获取项目记忆上下文
        project_memory_context = self._get_project_memory_context(user_id, self.project_brain_id)
        
        project_summary_resp = self._call_agent(
            agent_id=self.project_brain_id,
            prompt=self._build_project_brain_prompt(user_message),
            user_id=user_id,
            session_id=session_id,
            persist_history=False,
            extra_context=project_memory_context,
            memory_type="project"
        )
        project_summary = project_summary_resp.content
        
        specialist_ids = self.selector.select_specialists(user_message)
        specialist_outputs: List[SpecialistResult] = []
        for agent_id in specialist_ids:
            # 获取专家特定的记忆上下文
            expert_memory_context = self._get_expert_memory_context(user_id, agent_id)
            
            specialist_resp = self._call_agent(
                agent_id=agent_id,
                prompt=self._build_specialist_prompt(agent_id, user_message, project_summary),
                user_id=user_id,
                session_id=session_id,
                persist_history=False,
                extra_context=f"{project_summary}\n{expert_memory_context}",
                memory_type="expert"
            )
            specialist_outputs.append(SpecialistResult(agent_id=agent_id, content=specialist_resp.content))
        
        final_prompt = self._build_final_prompt(user_message, project_summary, specialist_outputs)
        final_response = self._call_agent(
            agent_id=self.project_brain_id,
            prompt=final_prompt,
            user_id=user_id,
            session_id=session_id,
            persist_history=True,
            extra_context=f"{project_summary}\n{project_memory_context}",
            memory_type="project"
        )
        
        return MultiAgentResult(
            project_summary=project_summary,
            selected_agents=specialist_ids,
            specialist_outputs=specialist_outputs,
            final_response=final_response
        )
    
    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的专家代理信息。"""
        available_agents = {}
        for agent_id, profile in Config.AGENT_PROFILES.items():
            available_agents[agent_id] = {
                "id": agent_id,
                "name": profile.get("name", agent_id),
                "description": profile.get("description", ""),
                "expertise": profile.get("expertise_keywords", []),
                "is_project_brain": agent_id == self.project_brain_id,
                "type": profile.get("type", "specialist")
            }
        return available_agents
    
    def _get_expert_memory_context(self, user_id: str, agent_id: str) -> str:
        """获取专家相关的记忆上下文。"""
        # 这里假设ChatEngine或底层有相应的方法支持按代理类型获取记忆
        # 实际实现可能需要根据记忆系统的具体实现调整
        return f"[专家领域相关记忆]"  # 占位符，实际实现时需要从记忆系统获取
    
    def _get_project_memory_context(self, user_id: str, agent_id: str) -> str:
        """获取项目相关的记忆上下文。"""
        return f"[项目相关记忆]"  # 占位符，实际实现时需要从记忆系统获取
    
    def _call_agent(
        self,
        *,
        agent_id: str,
        prompt: str,
        user_id: str,
        session_id: str,
        persist_history: bool,
        extra_context: Optional[str],
        memory_type: Optional[str] = None
    ) -> ChatResponse:
        """统一的代理调用封装，支持不同的记忆类型。"""
        try:
            # 构建记忆元数据，标识记忆类型
            memory_metadata = {}
            if memory_type:
                memory_metadata["memory_type"] = memory_type
                memory_metadata["expert_domain"] = agent_id if memory_type == "expert" else None
            
            # 打印调用信息以调试
            print(f"\n调试 - 调用代理: {agent_id}, 记忆类型: {memory_type}")
            print(f"调试 - 提示内容: {prompt[:100]}...")
            
            response = self.chat_engine.generate_response(
                prompt,
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id,
                persist_history=persist_history,
                store_memory=True,
                extra_context=extra_context,
                memory_metadata=memory_metadata  # 传递记忆元数据
            )
            
            # 不抛出异常，而是记录错误并返回响应，这样可以看到更多调试信息
            if response.error:
                print(f"警告 - 代理 {agent_id} 生成回复出错: {response.error}")
                # 尝试为响应内容设置一个默认值，以便测试可以继续
                if not response.content:
                    response.content = f"[代理 {agent_id} 生成回复时出错: {response.error}]"
            
            return response
            
        except Exception as e:
            # 捕获所有异常并返回带有详细错误信息的响应
            print(f"_call_agent执行异常: {str(e)}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            # 返回一个包含错误信息的响应，而不是抛出异常
            return ChatResponse(
                content=f"[代理 {agent_id} 执行异常: {str(e)}]",
                user_id=user_id,
                agent_id=agent_id,
                session_id=session_id,
                error=str(e)
            )
    
    def _build_project_brain_prompt(self, user_message: str) -> str:
        profile = Config.AGENT_PROFILES.get(self.project_brain_id, {})
        instructions = profile.get("instructions", "")
        name = profile.get("name", "项目大脑")
        description = profile.get("description", "")
        
        return (
            f"你是 {name}，{description}\n"
            "作为项目大脑，你需要整合所有专家意见，协调各方面资源。\n"
            "请输出：\n"
            "1. 项目目标摘要\n"
            "2. 关键风险/依赖\n"
            "3. 需要协调的专家领域\n"
            "请使用分点形式，语言简练。\n\n"
            f"[内部执行手册]\n{instructions}\n\n"
            f"[用户输入]\n{user_message}"
        )
    
    def _build_specialist_prompt(
        self,
        agent_id: str,
        user_message: str,
        project_summary: str
    ) -> str:
        """为特定专家构建专业prompt"""
        profile = Config.AGENT_PROFILES.get(agent_id, {})
        instructions = profile.get("instructions", "")
        name = profile.get("name", agent_id)
        style = profile.get("style", "专业、清晰")
        
        # 根据不同专家类型使用特定的prompt模板
        if agent_id == "product_lead":
            return self._build_product_expert_prompt(name, instructions, style, project_summary, user_message)
        elif agent_id == "algo_scientist":
            return self._build_algo_expert_prompt(name, instructions, style, project_summary, user_message)
        elif agent_id == "solution_architect":
            return self._build_architecture_expert_prompt(name, instructions, style, project_summary, user_message)
        else:
            # 默认专家prompt模板
            return (
                f"你是 {name}，负责给出专业建议。\n"
                "请结合项目大脑提供的摘要与用户需求，输出你的专业分析和建议。\n"
                f"表达风格：{style}\n\n"
                f"[专家工作守则]\n{instructions}\n\n"
                f"[项目大脑摘要]\n{project_summary}\n\n"
                f"[用户输入]\n{user_message}"
            )
            
    def _build_product_expert_prompt(self, name, instructions, style, project_summary, user_message):
        """产品专家专属prompt模板"""
        return (
            f"你是 {name}，一位资深产品专家。\n"
            "请基于用户需求和项目摘要，从产品角度进行深入分析并提供专业建议。\n"
            "请重点关注：\n"
            "1. 用户需求的核心价值点和潜在痛点\n"
            "2. 功能范围界定和优先级排序\n"
            "3. 用户体验设计和交互流程建议\n"
            "4. 产品路线图和迭代计划\n"
            "5. 成功指标和验收标准\n"
            f"表达风格：{style}\n\n"
            f"[产品专家工作指南]\n{instructions}\n\n"
            f"[项目概述]\n{project_summary}\n\n"
            f"[用户需求]\n{user_message}\n\n"
            "请提供详细、可操作的产品建议，帮助团队明确产品方向和具体实现路径。"
        )
        
    def _build_algo_expert_prompt(self, name, instructions, style, project_summary, user_message):
        """算法专家专属prompt模板"""
        return (
            f"你是 {name}，一位资深算法专家。\n"
            "请基于用户需求和项目摘要，从算法和技术角度进行深入分析并提供专业建议。\n"
            "请重点关注：\n"
            "1. 问题的算法本质和技术路径\n"
            "2. 多种算法方案的比较和选型建议\n"
            "3. 数据需求分析和质量要求\n"
            "4. 模型复杂度和算力评估\n"
            "5. 性能瓶颈预测和优化方向\n"
            "6. 实验设计和评估指标\n"
            f"表达风格：{style}\n\n"
            f"[算法专家工作指南]\n{instructions}\n\n"
            f"[项目概述]\n{project_summary}\n\n"
            f"[用户需求]\n{user_message}\n\n"
            "请提供严谨、科学的算法解决方案，包括技术选型依据和实施建议。"
        )
        
    def _build_architecture_expert_prompt(self, name, instructions, style, project_summary, user_message):
        """架构师专属prompt模板"""
        return (
            f"你是 {name}，一位资深解决方案架构师。\n"
            "请基于用户需求和项目摘要，从系统架构和技术实现角度进行深入分析并提供专业建议。\n"
            "请重点关注：\n"
            "1. 端到端系统架构设计\n"
            "2. 技术栈选型和组件划分\n"
            "3. 接口规范和集成策略\n"
            "4. 部署架构和资源规划\n"
            "5. 数据流转和存储方案\n"
            "6. 性能、安全和扩展性评估\n"
            f"表达风格：{style}\n\n"
            f"[架构师工作指南]\n{instructions}\n\n"
            f"[项目概述]\n{project_summary}\n\n"
            f"[用户需求]\n{user_message}\n\n"
            "请提供全面、可落地的架构方案，确保系统的可行性、可扩展性和可维护性。"
        )
    
    def _build_final_prompt(
        self,
        user_message: str,
        project_summary: str,
        specialist_outputs: List[SpecialistResult]
    ) -> str:
        specialist_section = "\n\n".join(
            f"- {self._get_agent_name(output.agent_id)} 专家反馈：{output.content}"
            for output in specialist_outputs
        ) or "暂无专家反馈。"
        
        profile = Config.AGENT_PROFILES.get(self.project_brain_id, {})
        name = profile.get("name", "项目大脑")
        
        return (
            f"你是 {name}，需要整合所有专家意见，对用户给出结构化的项目方案。\n"
            "请输出：\n"
            "1. 总体策略/路线\n"
            "2. 按角色分配的行动项与里程碑\n"
            "3. 风险与待澄清问题\n"
            "必须引用具体专家结论或记忆来源。\n\n"
            f"[项目大脑摘要]\n{project_summary}\n\n"
            f"[专家反馈汇总]\n{specialist_section}\n\n"
            f"[用户输入]\n{user_message}"
        )
    
    def _get_agent_name(self, agent_id: str) -> str:
        """获取代理的名称。"""
        profile = Config.AGENT_PROFILES.get(agent_id, {})
        return profile.get("name", agent_id)

