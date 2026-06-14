#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG猴子补丁模块 - 在不修改现有代码的情况下为word_gen_system添加RAG功能
"""
import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# 尝试导入RAG集成模块
try:
    from rag_integration import create_rag_manager, enhance_existing_render_prompt
    HAS_RAG = True
except ImportError as e:
    print(f"警告：无法导入RAG集成模块: {e}")
    print("RAG功能将被禁用")
    HAS_RAG = False

# 全局RAG管理器
_rag_manager = None

def init_rag_manager() -> bool:
    """
    初始化RAG管理器
    
    Returns:
        是否成功初始化
    """
    global _rag_manager
    
    if not HAS_RAG:
        print("RAG功能不可用，请安装必要依赖")
        return False
    
    try:
        _rag_manager = create_rag_manager()
        if _rag_manager:
            print(f"RAG管理器初始化成功")
            print(f"可用知识库: {_rag_manager.list_available_knowledge_bases()}")
            return True
        else:
            print("RAG管理器初始化失败")
            return False
    except Exception as e:
        print(f"初始化RAG管理器时出错: {e}")
        return False

def get_rag_manager():
    """获取RAG管理器（如果未初始化则尝试初始化）"""
    global _rag_manager
    
    if _rag_manager is not None:
        return _rag_manager
    
    # 尝试初始化
    if init_rag_manager():
        return _rag_manager
    else:
        return None

def monkey_patch_render_prompt():
    """
    猴子补丁render_prompt函数，添加RAG支持
    
    用法：在notebook中调用此函数后，原有的render_prompt函数将被增强
    """
    # 导入现有的render_prompt函数（假设在全局作用域中）
    try:
        # 尝试从全局命名空间获取render_prompt
        import __main__
        original_render_prompt = __main__.render_prompt
    except AttributeError:
        # 如果不在全局命名空间，尝试从当前模块导入
        try:
            from notebook_cell_sources import render_prompt as original_render_prompt
        except ImportError:
            print("警告：找不到原始的render_prompt函数")
            return False
    
    # 创建增强版本
    def enhanced_render_prompt(prompt_tpl: str, context: dict) -> str:
        """增强版render_prompt，支持RAG"""
        # 调用原始函数
        basic_prompt = original_render_prompt(prompt_tpl, context)
        
        # 获取RAG管理器
        rag_manager = get_rag_manager()
        
        # 如果prompt包含{kb:}标记，则进行增强
        if rag_manager and re.search(r'\{kb:[^}]+\}', basic_prompt):
            enhanced_prompt, _ = rag_manager.enhance_prompt_with_rag(basic_prompt, context)
            return enhanced_prompt
        
        return basic_prompt
    
    # 替换全局函数
    __main__.render_prompt = enhanced_render_prompt
    print("已成功猴子补丁render_prompt函数，添加RAG支持")
    return True

def monkey_patch_apply_ai_by_markers():
    """
    猴子补丁apply_ai_by_markers函数，在AI调用前进行RAG增强
    
    注意：这个函数需要访问doc_root, template_path, context, markers, client等参数
    """
    # 尝试从全局命名空间获取apply_ai_by_markers
    try:
        import __main__
        original_apply_ai_by_markers = __main__.apply_ai_by_markers
    except AttributeError:
        try:
            from notebook_cell_sources import apply_ai_by_markers as original_apply_ai_by_markers
        except ImportError:
            print("警告：找不到原始的apply_ai_by_markers函数")
            return False
    
    # 创建增强版本
    def enhanced_apply_ai_by_markers(doc_root, template_path, context, markers, client):
        """
        增强版apply_ai_by_markers，在调用AI前进行RAG增强
        """
        # 获取原始prompts
        from notebook_cell_sources import load_ai_prompts_from_template
        
        prompts = load_ai_prompts_from_template(template_path)
        results = []
        
        rag_manager = get_rag_manager()
        
        for i, marker in enumerate(markers):
            # 查找段落
            from notebook_cell_sources import _find_paragraph_contains, _paragraph_full_text, _replace_paragraph_text
            
            w_p = _find_paragraph_contains(doc_root, marker)
            if w_p is None:
                print(f'警告: 未找到含标记 {marker!r} 的段落，跳过该 AI 块')
                continue
            
            full = _paragraph_full_text(w_p)
            text_final = full.replace(marker, '').strip()
            prompt_tpl = prompts[i] if i < len(prompts) else ''
            
            # 渲染prompt
            from jinja2 import Environment, StrictUndefined
            env = Environment(undefined=StrictUndefined)
            prompt_final = env.from_string(prompt_tpl).render(context) if prompt_tpl else ''
            
            # RAG增强
            if rag_manager and prompt_final and re.search(r'\{kb:[^}]+\}', prompt_final):
                enhanced_prompt, _ = rag_manager.enhance_prompt_with_rag(prompt_final, context)
                if enhanced_prompt != prompt_final:
                    print(f"已对AI块 {marker} 进行RAG增强")
                    prompt_final = enhanced_prompt
            
            # 调用AI
            if client is not None and prompt_final:
                try:
                    ai_text = client.rewrite(text_final, prompt_final)
                except Exception as e:
                    print('DeepSeek 调用失败，保留原文:', e)
                    ai_text = text_final
            else:
                ai_text = text_final
            
            _replace_paragraph_text(w_p, ai_text)
            results.append((marker, prompt_final, ai_text))
        
        return results
    
    # 替换全局函数
    __main__.apply_ai_by_markers = enhanced_apply_ai_by_markers
    print("已成功猴子补丁apply_ai_by_markers函数，添加RAG支持")
    return True

def monkey_patch_finalize_rendered_document():
    """
    猴子补丁finalize_rendered_document函数，支持RAG
    
    这个函数会调用apply_ai_by_markers，所以如果已经补丁了apply_ai_by_markers，就不需要单独补丁
    但我们可以添加RAG管理器参数
    """
    # 尝试从全局命名空间获取finalize_rendered_document
    try:
        import __main__
        original_finalize = __main__.finalize_rendered_document
    except AttributeError:
        try:
            from notebook_cell_sources import finalize_rendered_document as original_finalize
        except ImportError:
            print("警告：找不到原始的finalize_rendered_document函数")
            return False
    
    # 创建增强版本
    def enhanced_finalize_rendered_document(
        rendered_docx: Path,
        template_docx: Path,
        context: dict,
        trace_map: Dict[str, Any],
        output_docx: Path,
        use_ai: bool,
        api_key: str | None,
        ai_markers: List[str] | None = None,
        rag_manager = None  # 新增参数
    ) -> Path:
        """
        增强版finalize_rendered_document，支持可选的RAG管理器
        """
        # 如果提供了rag_manager，将其设置为全局管理器
        if rag_manager:
            global _rag_manager
            _rag_manager = rag_manager
        
        # 调用原始函数（它会使用已经补丁的apply_ai_by_markers）
        return original_finalize(
            rendered_docx, template_docx, context, trace_map, 
            output_docx, use_ai, api_key, ai_markers
        )
    
    # 替换全局函数
    __main__.finalize_rendered_document = enhanced_finalize_rendered_document
    print("已成功猴子补丁finalize_rendered_document函数，支持RAG管理器参数")
    return True

def monkey_patch_run_smart_document_generation():
    """
    猴子补丁run_smart_document_generation函数，添加RAG支持
    """
    try:
        import __main__
        original_run = __main__.run_smart_document_generation
    except AttributeError:
        try:
            from notebook_cell_sources import run_smart_document_generation as original_run
        except ImportError:
            print("警告：找不到原始的run_smart_document_generation函数")
            return False
    
    def enhanced_run_smart_document_generation(
        template_ids: List[int],
        data_dir: Path | None = None,
        use_ai: bool = False,
        skip_confirm: bool = False,
        use_smart_marking: bool = True,
        use_rag: bool = True  # 新增参数
    ) -> List[Path]:
        """
        增强版run_smart_document_generation，支持RAG
        """
        # 如果启用RAG，初始化RAG管理器
        if use_rag:
            init_rag_manager()
        
        # 调用原始函数
        return original_run(
            template_ids, data_dir, use_ai, skip_confirm, use_smart_marking
        )
    
    # 替换全局函数
    __main__.run_smart_document_generation = enhanced_run_smart_document_generation
    print("已成功猴子补丁run_smart_document_generation函数，添加RAG支持")
    return True

def apply_all_monkey_patches():
    """应用所有猴子补丁"""
    print("开始应用RAG猴子补丁...")
    
    success_count = 0
    
    # 初始化RAG管理器
    if init_rag_manager():
        success_count += 1
    
    # 应用各个补丁
    if monkey_patch_render_prompt():
        success_count += 1
    
    if monkey_patch_apply_ai_by_markers():
        success_count += 1
    
    if monkey_patch_finalize_rendered_document():
        success_count += 1
    
    if monkey_patch_run_smart_document_generation():
        success_count += 1
    
    print(f"猴子补丁应用完成，成功应用 {success_count}/5 个补丁")
    return success_count >= 3  # 至少3个成功算基本成功

# 便捷函数：在notebook中直接运行
def setup_rag_for_notebook():
    """
    在notebook中设置RAG功能的便捷函数
    
    用法：在notebook的cell中运行 setup_rag_for_notebook()
    """
    print("正在为word_gen_system设置RAG功能...")
    
    # 检查依赖
    try:
        import sentence_transformers
        import numpy
        print("✓ 必要依赖已安装")
    except ImportError as e:
        print(f"✗ 缺少必要依赖: {e}")
        print("请运行: pip install sentence-transformers numpy scikit-learn")
        return False
    
    # 检查知识库
    kb_dir = Path("knowledge_bases")
    if not kb_dir.exists():
        print(f"✗ 知识库目录不存在: {kb_dir}")
        print("请先运行 create_puhui_knowledge_base.py 创建测试知识库")
        return False
    
    # 应用猴子补丁
    if apply_all_monkey_patches():
        print("\n✓ RAG功能设置成功！")
        print("\n使用方式:")
        print("1. 在Word模板批注中使用 {kb:知识库名称} 标记")
        print('   例如: prompt="基于{kb:puhui_daikou_buliang}知识库，分析风险情况"')
        print("2. 运行智能生成时，RAG功能会自动启用")
        print("3. 可用知识库:", get_rag_manager().list_available_knowledge_bases() if get_rag_manager() else "无")
        return True
    else:
        print("\n✗ RAG功能设置失败")
        return False

if __name__ == "__main__":
    # 直接运行测试
    setup_rag_for_notebook()