#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体记忆隔离与协作功能测试脚本
"""

import sys
import os
from typing import Dict, List

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory_manager import MemoryManager
from core.agent_controller import MultiAgentController
from core.chat_engine import ChatEngine
from config.settings import Config

def test_expert_memory_isolation():
    """测试专家大脑的记忆隔离功能"""
    print("=== 测试1: 专家大脑记忆隔离功能 ===")
    
    # 初始化组件
    memory_manager = MemoryManager()
    chat_engine = ChatEngine(memory_manager)
    agent_controller = MultiAgentController(chat_engine)
    
    test_user_id = "test_user_001"
    test_session_id = "test_session_001"
    
    # 1. 与产品专家交互
    print("\n1. 与产品专家交互...")
    try:
        product_result = agent_controller.process_user_message(
            "我需要一个AI推荐系统的产品规划，重点关注用户体验。",
            test_user_id,
            test_session_id,
            target_agent="product_lead"
        )
        print(f"产品专家回复: {product_result.final_response.content[:100]}...")
    except Exception as e:
        import traceback
        print(f"详细错误信息: {str(e)}")
        print(f"错误堆栈:\n{traceback.format_exc()}")
        # 继续执行，不中断测试
    
    # 2. 与算法专家交互
    print("\n2. 与算法专家交互...")
    algo_result = agent_controller.process_user_message(
        "我需要优化推荐算法的准确率，当前使用的是协同过滤。",
        test_user_id,
        test_session_id,
        target_agent="algo_scientist"
    )
    print(f"算法专家回复: {algo_result.final_response.content[:100]}...")
    
    # 3. 与架构师交互
    print("\n3. 与架构师交互...")
    arch_result = agent_controller.process_user_message(
        "我需要设计一个高并发的推荐系统架构，支持百万级用户。",
        test_user_id,
        test_session_id,
        target_agent="solution_architect"
    )
    print(f"架构师回复: {arch_result.final_response.content[:100]}...")
    
    # 4. 验证记忆隔离
    print("\n4. 验证记忆隔离...")
    
    # 获取产品专家的记忆
    product_memories = memory_manager.get_all_memories(test_user_id, agent_id="product_lead", memory_type="expert")
    # 检查返回值类型并正确处理
    if isinstance(product_memories, dict):
        # 提取字典中的值部分
        mem_values = list(product_memories.values())
        print(f"产品专家记忆数量: {len(mem_values)}")
        for i, mem in enumerate(mem_values[:3]):
            # 根据不同类型进行处理
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")
    else:
        # 假设是列表的情况
        print(f"产品专家记忆数量: {len(product_memories)}")
        for i, mem in enumerate(product_memories[:3]):
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")
    
    # 获取算法专家的记忆
    algo_memories = memory_manager.get_all_memories(test_user_id, agent_id="algo_scientist", memory_type="expert")
    # 检查返回值类型并正确处理
    if isinstance(algo_memories, dict):
        # 提取字典中的值部分
        mem_values = list(algo_memories.values())
        print(f"算法专家记忆数量: {len(mem_values)}")
        for i, mem in enumerate(mem_values[:3]):
            # 根据不同类型进行处理
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")
    else:
        # 假设是列表的情况
        print(f"算法专家记忆数量: {len(algo_memories)}")
        for i, mem in enumerate(algo_memories[:3]):
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")
    
    # 获取架构专家记忆
    arch_memories = memory_manager.get_all_memories(test_user_id, agent_id="solution_architect", memory_type="expert")
    # 检查返回值类型并正确处理
    if isinstance(arch_memories, dict):
        # 提取字典中的值部分
        mem_values = list(arch_memories.values())
        print(f"架构专家记忆数量: {len(mem_values)}")
        for i, mem in enumerate(mem_values[:3]):
            # 根据不同类型进行处理
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")
    else:
        # 假设是列表的情况
        print(f"架构专家记忆数量: {len(arch_memories)}")
        for i, mem in enumerate(arch_memories[:3]):
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")
    
    # 获取用户记忆
    user_memories = memory_manager.get_all_memories(test_user_id)
    # 检查返回值类型并正确处理
    if isinstance(user_memories, dict):
        # 提取字典中的值部分
        mem_values = list(user_memories.values())
        print(f"用户记忆数量: {len(mem_values)}")
        for i, mem in enumerate(mem_values[:3]):
            # 根据不同类型进行处理
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")
    else:
        # 假设是列表的情况
        print(f"用户记忆数量: {len(user_memories)}")
        for i, mem in enumerate(user_memories[:3]):
            if isinstance(mem, str):
                print(f"  - {mem[:50]}...")
            elif isinstance(mem, dict):
                print(f"  - {mem.get('content', '')[:50]}...")
            else:
                print(f"  - {str(mem)[:50]}...")

def test_project_brain_integration():
    """测试项目大脑的整合功能"""
    print("\n\n=== 测试2: 项目大脑整合功能 ===")
    
    # 初始化组件
    memory_manager = MemoryManager()
    chat_engine = ChatEngine(memory_manager)
    agent_controller = MultiAgentController(chat_engine)
    
    test_user_id = "test_user_002"
    test_session_id = "test_session_002"
    
    # 使用项目大脑进行综合查询
    print("\n1. 使用项目大脑处理综合请求...")
    project_result = agent_controller.process_user_message(
        "我想开发一个AI驱动的个性化推荐系统，请提供完整的项目方案，包括产品设计、算法选择和系统架构。",
        test_user_id,
        test_session_id
    )
    
    print(f"\n项目大脑最终回复: {project_result.final_response.content[:150]}...")
    
    # 检查专家调用情况
    print(f"\n参与的专家数量: {len(project_result.specialist_outputs)}")
    for specialist in project_result.specialist_outputs:
        print(f"\n专家: {specialist.agent_id}")
        print(f"回复摘要: {specialist.content[:100]}...")
    
    # 获取项目大脑的协作上下文
    print("\n2. 获取项目协作上下文...")
    collaborative_context = memory_manager.get_collaborative_context(
        query="推荐系统",
        user_id=test_user_id,
        agent_id="project_brain",
        session_id=test_session_id,
        collaborators=["product_lead", "algo_scientist", "solution_architect"],
        limit=5
    )
    
    print(f"协作记忆数量: {collaborative_context['memories_count']}")
    print(f"记忆内容: {collaborative_context['formatted'][:150]}...")

def test_memory_persistence_across_interactions():
    """测试跨交互的记忆持久化功能"""
    print("\n\n=== 测试3: 记忆持久化与跨交互访问 ===")
    
    # 初始化组件
    memory_manager = MemoryManager()
    chat_engine = ChatEngine(memory_manager)
    agent_controller = MultiAgentController(chat_engine)
    
    test_user_id = "test_user_003"
    test_session_id = "test_session_003"
    
    # 第一次交互
    print("\n1. 第一次交互 - 提供系统信息...")
    agent_controller.process_user_message(
        "我们的系统目前有100万用户，日均请求量500万次，响应时间要求小于200ms。",
        test_user_id,
        test_session_id,
        target_agent="solution_architect"
    )
    
    # 第二次交互 - 检查记忆是否保留
    print("\n2. 第二次交互 - 引用之前的信息...")
    second_result = agent_controller.process_user_message(
        "基于我之前提供的系统规模，请推荐合适的部署架构。",
        test_user_id,
        test_session_id,
        target_agent="solution_architect"
    )
    
    print(f"架构师回复: {second_result.final_response.content[:150]}...")
    
    # 验证是否引用了之前的信息
    if "100万" in second_result.final_response.content or "500万" in second_result.final_response.content:
        print("✓ 成功: 架构师引用了之前提供的系统规模信息")
    else:
        print("✗ 失败: 架构师未能引用之前提供的系统规模信息")
    
    # 3. 切换到项目大脑，检查是否能访问专家记忆
    print("\n3. 切换到项目大脑，检查记忆共享...")
    project_result = agent_controller.process_user_message(
        "总结一下我们系统的技术架构需求和挑战。",
        test_user_id,
        test_session_id
    )
    
    print(f"项目大脑回复: {project_result.final_response.content[:150]}...")
    
    if "100万" in project_result.final_response.content or "500万" in project_result.final_response.content:
        print("✓ 成功: 项目大脑能够访问专家记忆中的系统规模信息")
    else:
        print("✗ 失败: 项目大脑未能访问专家记忆中的系统规模信息")

def main():
    """运行所有测试"""
    print("开始多智能体记忆隔离与协作功能测试...\n")
    
    try:
        # 运行各项测试
        test_expert_memory_isolation()
        test_project_brain_integration()
        test_memory_persistence_across_interactions()
        
        print("\n\n=== 测试完成 ===")
        print("所有测试用例已执行完毕！")
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()