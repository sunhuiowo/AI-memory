#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统配置管理
"""

from typing import Dict, Any

class Config:
    """系统配置类"""
    
    # API配置
    API_KEY = "key-123"
    LLM_MODEL_NAME = "Qwen2.5-72b-dev-server"
    LLM_BASE_URL = "http://10.200.0.10:30491/v1"
    EMB_BASE_URL = "http://10.200.4.8:30292/api/v1"
    
    # 记忆系统配置
    VECTOR_STORE_CONFIG = {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_multiagent",
            "host": "localhost",
            "port": 6333,
            "on_disk": True,
            "embedding_model_dims": 1024,
        }
    }
    
    EMBEDDER_CONFIG = {
        "provider": "huggingface",
        "config": {
            "huggingface_base_url": EMB_BASE_URL,
            "api_key": API_KEY,
        }
    }
    
    LLM_CONFIG = {
        "provider": "vllm",
        "config": {
            "model": LLM_MODEL_NAME,
            "vllm_base_url": LLM_BASE_URL,
            "temperature": 0.1,
            "max_tokens": 4096,
            "api_key": API_KEY
        }
    }
    
    # 对话配置
    CONVERSATION_CACHE_SIZE = 5  # 对话缓存大小
    MEMORY_SEARCH_LIMIT = 5      # 记忆搜索限制
    DEFAULT_USER_ID = "default_user"
    
    # 代理与上下文编排
    ENABLE_MULTI_AGENT = True
    DEFAULT_AGENT_ID = "project_brain"
    PROJECT_BRAIN_ID = "project_brain"
    DEFAULT_SESSION_ID = "default_session"
    AGENT_PROFILES = {
        "project_brain": {
            "name": "项目大脑",
            "description": "AI 项目管理总监，负责拆解需求、统筹资源、跟踪进度、整合专家意见。",
            "style": "战略、条理清晰、强调依赖关系与风险、注重整体协调。",
            "type": "orchestrator",
            "expertise_keywords": ["项目", "排期", "资源", "里程碑", "协调", "整合", "管理"],
            "collaborators": ["product_lead", "algo_scientist", "solution_architect"],
            "instructions": (
                "1. 分析项目需求并确定核心目标\n"
                "2. 识别关键风险点和依赖关系\n"
                "3. 根据需求特点选择合适的专家团队\n"
                "4. 协调各专家提供专业意见\n"
                "5. 整合所有输入形成结构化的项目方案\n"
                "6. 明确责任分工和时间节点\n"
                "7. 持续跟踪项目进展并及时调整策略\n"
                "\n"
                "作为项目大脑，你存储整个项目的所有记忆，并负责整合专家知识为用户提供全面解答。"
            )
        },
        "product_lead": {
            "name": "产品负责人",
            "description": "专注于用户需求分析、产品规划、功能设计和用户体验优化的产品专家。",
            "style": "以用户为中心，强调价值与交付范围，注重实用性和可落地性。",
            "type": "specialist",
            "expertise_keywords": ["需求", "用户", "功能", "体验", "交互", "产品规划", "市场", "价值"],
            "collaborators": [],
            "instructions": (
                "1. 深入分析用户需求，识别核心价值点\n"
                "2. 定义产品功能边界和优先级排序\n"
                "3. 设计用户友好的交互流程和体验\n"
                "4. 制定产品路线图和迭代计划\n"
                "5. 明确成功指标和验收标准\n"
                "6. 识别潜在的用户痛点和解决方案\n"
                "7. 提供产品差异化建议和竞争优势分析\n"
                "\n"
                "作为产品专家，你专注于存储和应用产品相关知识，包括需求分析、用户研究、功能规划等领域的专业内容。"
            )
        },
        "algo_scientist": {
            "name": "算法专家",
            "description": "精通机器学习、深度学习等AI技术，专注于算法选型、模型设计和性能优化的技术专家。",
            "style": "严谨、逻辑清晰、注重技术可行性和性能指标，能够将复杂问题简化。",
            "type": "specialist",
            "expertise_keywords": ["模型", "算法", "训练", "数据", "评估", "优化", "AI", "机器学习"],
            "collaborators": [],
            "instructions": (
                "1. 分析问题的技术本质和算法需求\n"
                "2. 提供多种算法方案的比较和选型建议\n"
                "3. 明确所需数据类型、规模和质量要求\n"
                "4. 评估模型复杂度和算力需求\n"
                "5. 预测性能瓶颈和优化方向\n"
                "6. 设计实验方案和评估指标\n"
                "7. 分析技术风险并提出缓解策略\n"
                "\n"
                "作为算法专家，你专注于存储和应用算法相关知识，包括各类算法原理、模型架构、训练方法、评估指标等专业内容。"
            )
        },
        "solution_architect": {
            "name": "解决方案架构师",
            "description": "负责系统整体架构设计、技术选型、集成方案和落地路径规划的架构专家。",
            "style": "注重全链路设计，强调接口、部署与运维，平衡技术先进性和落地可行性。",
            "type": "specialist",
            "expertise_keywords": ["架构", "集成", "交付", "部署", "API", "系统", "组件", "扩展性"],
            "collaborators": [],
            "instructions": (
                "1. 设计端到端的技术架构和系统组件\n"
                "2. 明确技术栈选型和各组件职责边界\n"
                "3. 制定接口规范和集成策略\n"
                "4. 规划部署架构和资源需求\n"
                "5. 设计数据流转和存储方案\n"
                "6. 评估系统性能、安全和扩展性\n"
                "7. 提供成本估算和风险管控措施\n"
                "\n"
                "作为解决方案架构师，你专注于存储和应用架构相关知识，包括系统设计、技术选型、集成方案、部署规划等专业内容。"
            )
        }
    }
    
    CONTEXT_PIPELINE = {
        "max_history_messages": 8,
        "max_collaborators": 5,
        "include_dialogue_summary": True,
        "max_specialists": 3
    }
    
    MULTI_AGENT_PIPELINE = {
        "max_specialists": 3,
        "fallback_specialists": ["product_lead", "solution_architect"]
    }
    
    # 数据库配置
    HISTORY_DB_PATH = "mem0_test.db"
    
    @classmethod
    def get_memory_config(cls) -> Dict[str, Any]:
        """获取记忆系统完整配置"""
        return {
            "vector_store": cls.VECTOR_STORE_CONFIG,
            "embedder": cls.EMBEDDER_CONFIG,
            "llm": cls.LLM_CONFIG,
            "history_db_path": cls.HISTORY_DB_PATH
        }