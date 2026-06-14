#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG功能集成模块 - 将知识库检索功能集成到现有Word生成系统中
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import re

# 导入现有的知识库模块
from rag_module import KBManager, process_kb_references

class RAGIntegrationManager:
    """RAG集成管理器，用于将知识库功能集成到现有系统中"""
    
    def __init__(self, kb_base_dir: Path | str = "knowledge_bases"):
        """
        初始化RAG集成管理器
        
        Args:
            kb_base_dir: 知识库目录路径
        """
        self.kb_base_dir = Path(kb_base_dir)
        self.kb_manager = None
        self._initialize_kb_manager()
    
    def _initialize_kb_manager(self) -> bool:
        """初始化知识库管理器"""
        try:
            if not self.kb_base_dir.exists():
                print(f"警告：知识库目录不存在: {self.kb_base_dir}")
                print(f"将创建知识库目录: {self.kb_base_dir}")
                self.kb_base_dir.mkdir(parents=True, exist_ok=True)
                return False
            
            self.kb_manager = KBManager(self.kb_base_dir)
            
            # 列出可用的知识库
            kb_names = self.kb_manager.get_all_kb_names()
            if kb_names:
                print(f"已加载知识库管理器，可用知识库: {', '.join(kb_names)}")
            else:
                print("已加载知识库管理器，但未找到任何知识库")
            
            return True
        except Exception as e:
            print(f"初始化知识库管理器失败: {e}")
            self.kb_manager = None
            return False
    
    def enhance_prompt_with_rag(self, original_prompt: str, context: Dict[str, Any] = None) -> Tuple[str, bool]:
        """
        使用RAG增强Prompt，处理{kb:知识库名称}标记
        
        Args:
            original_prompt: 原始prompt文本
            context: 渲染上下文（可选）
            
        Returns:
            (增强后的prompt, 是否成功进行了RAG增强)
        """
        if not self.kb_manager:
            print("警告：知识库管理器未初始化，跳过RAG增强")
            return original_prompt, False
        
        # 检查是否有{kb:}标记
        if not re.search(r'\{kb:[^}]+\}', original_prompt):
            return original_prompt, False
        
        try:
            enhanced_prompt = process_kb_references(original_prompt, self.kb_manager)
            
            # 记录处理情况
            original_has_kb = re.search(r'\{kb:[^}]+\}', original_prompt) is not None
            enhanced_has_kb = re.search(r'\{kb:[^}]+\}', enhanced_prompt) is not None
            
            if original_has_kb and not enhanced_has_kb:
                print(f"已处理知识库引用，注入了相关上下文")
            elif original_has_kb and enhanced_has_kb:
                print(f"警告：知识库引用处理可能不完整")
            
            return enhanced_prompt, True
        except Exception as e:
            print(f"处理知识库引用时出错: {e}")
            return original_prompt, False
    
    def render_prompt_with_rag(self, prompt_template: str, context: Dict[str, Any], 
                              jinja_env=None) -> Tuple[str, bool]:
        """
        完整的Prompt渲染流程：Jinja2渲染 + RAG增强
        
        Args:
            prompt_template: Jinja2模板字符串
            context: 渲染上下文
            jinja_env: Jinja2环境（可选）
            
        Returns:
            (渲染后的prompt, 是否使用了RAG)
        """
        from jinja2 import Environment, StrictUndefined
        
        # 第一步：Jinja2渲染
        if jinja_env is None:
            jinja_env = Environment(undefined=StrictUndefined)
        
        try:
            basic_prompt = jinja_env.from_string(prompt_template).render(context)
        except Exception as e:
            print(f"Jinja2渲染失败: {e}")
            basic_prompt = prompt_template
        
        # 第二步：RAG增强
        enhanced_prompt, used_rag = self.enhance_prompt_with_rag(basic_prompt, context)
        
        return enhanced_prompt, used_rag
    
    def list_available_knowledge_bases(self) -> List[str]:
        """列出可用的知识库"""
        if not self.kb_manager:
            return []
        return self.kb_manager.get_all_kb_names()
    
    def search_knowledge_base(self, kb_name: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """直接搜索知识库"""
        if not self.kb_manager:
            print("知识库管理器未初始化")
            return []
        
        try:
            return self.kb_manager.search_kb(kb_name, query, top_k=top_k)
        except Exception as e:
            print(f"搜索知识库失败: {e}")
            return []


# 与现有系统兼容的函数
def create_rag_manager() -> Optional[RAGIntegrationManager]:
    """
    创建RAG集成管理器（兼容现有系统调用）
    
    Returns:
        RAG集成管理器实例，如果失败则返回None
    """
    try:
        # 检查必要的依赖
        import sentence_transformers
        import numpy
        
        rag_manager = RAGIntegrationManager()
        if rag_manager.kb_manager:
            return rag_manager
        else:
            print("RAG功能可用，但知识库管理器初始化失败")
            return None
    except ImportError as e:
        print(f"缺少RAG依赖: {e}")
        print("请安装: pip install sentence-transformers numpy scikit-learn")
        return None
    except Exception as e:
        print(f"创建RAG管理器失败: {e}")
        return None


def enhance_existing_render_prompt(prompt_template: str, context: Dict[str, Any], 
                                  rag_manager: Optional[RAGIntegrationManager] = None) -> str:
    """
    增强现有的render_prompt函数，支持RAG功能
    
    这是现有系统中render_prompt函数的直接替代品
    """
    from jinja2 import Environment, StrictUndefined
    
    # 创建Jinja2环境
    env = Environment(undefined=StrictUndefined)
    
    # 基本渲染
    try:
        basic_prompt = env.from_string(prompt_template).render(context)
    except Exception as e:
        print(f"Jinja2渲染失败: {e}")
        basic_prompt = prompt_template
    
    # 如果有RAG管理器且prompt包含{kb:}标记，则进行增强
    if rag_manager and re.search(r'\{kb:[^}]+\}', basic_prompt):
        enhanced_prompt, _ = rag_manager.enhance_prompt_with_rag(basic_prompt, context)
        return enhanced_prompt
    
    return basic_prompt


def test_rag_integration():
    """测试RAG集成功能"""
    print("=== 测试RAG集成功能 ===\n")
    
    # 创建RAG管理器
    rag_manager = create_rag_manager()
    
    if not rag_manager:
        print("无法创建RAG管理器，跳过测试")
        return False
    
    # 测试用例
    test_cases = [
        {
            "template": "基于当前不良率{{data.bad_mom}}，请分析风险情况。",
            "context": {"data": {"bad_mom": 0.12}},
            "expect_rag": False
        },
        {
            "template": "基于{kb:puhui_daikou_buliang}知识库，分析当前风险情况。",
            "context": {"data": {"bad_mom": 0.12}},
            "expect_rag": True
        },
        {
            "template": "请结合{kb:puhui_daikou_buliang:不良贷款处置方式}，给出建议。",
            "context": {"data": {"bad_mom": 0.12}},
            "expect_rag": True
        },
        {
            "template": "基于{kb:puhui_daikou_buliang}知识库和{kb:puhui_daikou_buliang:风险缓释措施}，制定方案。",
            "context": {"data": {"bad_mom": 0.12, "branch_name": "A支行"}},
            "expect_rag": True
        }
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试用例 {i}:")
        print(f"  模板: {test_case['template'][:50]}...")
        print(f"  期望RAG: {test_case['expect_rag']}")
        
        result, used_rag = rag_manager.render_prompt_with_rag(
            test_case['template'], test_case['context']
        )
        
        # 检查结果
        success = (used_rag == test_case['expect_rag'])
        
        if success:
            print(f"  ✓ 通过")
        else:
            print(f"  ✗ 失败: used_rag={used_rag}, expected={test_case['expect_rag']}")
            all_passed = False
        
        # 显示部分结果
        if used_rag:
            print(f"  结果预览: {result[:100]}...")
        else:
            print(f"  结果: {result[:100]}...")
        
        print()
    
    # 测试知识库列表
    print("测试知识库列表:")
    kb_list = rag_manager.list_available_knowledge_bases()
    if kb_list:
        print(f"  ✓ 可用知识库: {', '.join(kb_list)}")
    else:
        print("  ✗ 未找到知识库")
        all_passed = False
    
    return all_passed


if __name__ == "__main__":
    # 直接运行测试
    success = test_rag_integration()
    if success:
        print("RAG集成测试通过！")
    else:
        print("RAG集成测试部分失败")
    
    # 显示使用示例
    print("\n=== 使用示例 ===")
    print("""
在现有系统中使用RAG功能：

1. 导入模块：
   from rag_integration import create_rag_manager, enhance_existing_render_prompt

2. 创建RAG管理器：
   rag_manager = create_rag_manager()

3. 在Word模板批注中使用：
   prompt="基于{kb:puhui_daikou_buliang}知识库，分析风险情况。"

4. 渲染时自动增强：
   enhanced_prompt = enhance_existing_render_prompt(prompt_template, context, rag_manager)

5. 或者使用新函数：
   result, used_rag = rag_manager.render_prompt_with_rag(prompt_template, context)
    """)