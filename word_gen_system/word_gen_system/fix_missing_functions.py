#!/usr/bin/env python3
"""
修复 word_gen_system_demo_with_marking.ipynb 中缺失的函数
"""

import json
import os
from pathlib import Path

def fix_notebook():
    """修复notebook中缺失的函数"""
    notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
    
    if not notebook_path.exists():
        print(f"Notebook文件不存在: {notebook_path}")
        return False
    
    # 读取notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # 查找 run_smart_document_generation 函数所在的cell
    target_cell_idx = None
    for i, cell in enumerate(nb['cells']):
        if cell.get('cell_type') == 'code':
            source = ''.join(cell.get('source', []))
            if 'def run_smart_document_generation' in source:
                target_cell_idx = i
                break
    
    if target_cell_idx is None:
        print("未找到 run_smart_document_generation 函数")
        return False
    
    print(f"找到 run_smart_document_generation 在 cell {target_cell_idx}")
    
    # 创建新的cell，包含缺失的函数定义
    new_cell_content = '''# Cell 12.5: 缺失的函数定义 - 文档最终化与批注处理

def annotate_values_in_document(
    docx_path: Path,
    trace_map: Dict[str, Any],
    api_key: str | None = None,
    ai_markers: List[str] | None = None,
    use_ai: bool = False,
) -> None:
    """
    为文档中的值添加批注（基于trace_map）。
    
    Args:
        docx_path: Word文档路径
        trace_map: 溯源映射
        api_key: DeepSeek API密钥
        ai_markers: AI块标记列表
        use_ai: 是否调用AI
    """
    try:
        # 导入Annotator
        from smart_marking_system import Annotator
        
        # 创建批注器
        annotator = Annotator()
        
        # 构建批注对
        annotation_pairs = []
        for key, item in trace_map.items():
            if hasattr(item, 'var') and hasattr(item, 'value'):
                # 这是TraceItem对象
                var = item.var
                value = item.value
                table = getattr(item, 'table', '')
                field = getattr(item, 'field', '')
                pk = getattr(item, 'pk', '')
                row_index = getattr(item, 'row_index', None)
                source_file = getattr(item, 'source_file', '')
                
                # 创建批注文本
                annotation_text = f"[数据来源] 表={table} 字段={field} 值={value}"
                if pk:
                    annotation_text += f" | 主键={pk}"
                if row_index is not None:
                    annotation_text += f" | 行索引={row_index}"
                if source_file:
                    annotation_text += f" | 文件={source_file}"
                
                # 添加批注对
                annotation_pairs.append({
                    'text': str(value),
                    'comment': annotation_text,
                    'var_path': var
                })
            elif isinstance(item, dict):
                # 这是字典格式的trace项
                var = item.get('var', '')
                value = item.get('value', '')
                table = item.get('table', '')
                field = item.get('field', '')
                pk = item.get('pk', '')
                row_index = item.get('row_index', None)
                source_file = item.get('source_file', '')
                
                if var and value is not None:
                    # 创建批注文本
                    annotation_text = f"[数据来源] 表={table} 字段={field} 值={value}"
                    if pk:
                        annotation_text += f" | 主键={pk}"
                    if row_index is not None:
                        annotation_text += f" | 行索引={row_index}"
                    if source_file:
                        annotation_text += f" | 文件={source_file}"
                    
                    # 添加批注对
                    annotation_pairs.append({
                        'text': str(value),
                        'comment': annotation_text,
                        'var_path': var
                    })
        
        # 添加批注
        if annotation_pairs:
            annotator.annotate_document(str(docx_path), annotation_pairs)
            print(f"已添加 {len(annotation_pairs)} 条批注")
        else:
            print("未找到需要批注的数据项")
            
    except Exception as e:
        print(f"批注过程中出错: {e}")
        import traceback
        traceback.print_exc()


def finalize_rendered_document(
    mid_docx: Path,
    template_docx: Path,
    context: Dict[str, Any],
    trace_map: Dict[str, Any],
    final_docx: Path,
    use_ai: bool = False,
    api_key: str | None = None,
    ai_markers: List[str] | None = None,
) -> None:
    """
    最终化渲染的文档：添加批注，可选调用AI改写。
    
    Args:
        mid_docx: 中间文档路径
        template_docx: 模板文档路径
        context: 渲染上下文
        trace_map: 溯源映射
        final_docx: 最终文档路径
        use_ai: 是否调用AI
        api_key: DeepSeek API密钥
        ai_markers: AI块标记列表
    """
    # 首先复制中间文档到最终文档
    import shutil
    shutil.copy2(mid_docx, final_docx)
    
    # 添加批注
    annotate_values_in_document(
        docx_path=final_docx,
        trace_map=trace_map,
        api_key=api_key,
        ai_markers=ai_markers,
        use_ai=use_ai,
    )
    
    # 如果有AI标记且需要AI处理
    if use_ai and api_key and ai_markers:
        try:
            from notebook_cell_sources import DeepSeekClient
            
            # 创建AI客户端
            client = DeepSeekClient(api_key=api_key)
            
            # 读取文档内容
            from docx import Document
            doc = Document(final_docx)
            
            # 查找并处理AI块
            for marker in ai_markers:
                # 这里应该实现更复杂的AI块处理逻辑
                print(f"注意: AI块处理逻辑需要完善，检测到标记: {marker}")
                
            print("AI处理完成")
        except Exception as e:
            print(f"AI处理过程中出错: {e}")
            import traceback
            traceback.print_exc()


def finalize_rendered_document_enhanced(
    mid_docx: Path,
    template_docx: Path,
    context: Dict[str, Any],
    trace_map: Dict[str, Any],
    final_docx: Path,
    use_ai: bool = False,
    api_key: str | None = None,
    ai_markers: List[str] | None = None,
    use_smart_marking: bool = False,
    position_mappings: Dict[str, Any] | None = None,
) -> None:
    """
    增强的最终文档处理函数（支持智能标记）。
    
    Args:
        mid_docx: 中间文档路径
        template_docx: 模板文档路径
        context: 渲染上下文
        trace_map: 溯源映射
        final_docx: 最终文档路径
        use_ai: 是否调用AI
        api_key: DeepSeek API密钥
        ai_markers: AI块标记列表
        use_smart_marking: 是否使用智能标记
        position_mappings: 位置映射（智能标记使用）
    """
    # 首先复制中间文档到最终文档
    import shutil
    shutil.copy2(mid_docx, final_docx)
    
    # 添加批注
    annotate_values_in_document(
        docx_path=final_docx,
        trace_map=trace_map,
        api_key=api_key,
        ai_markers=ai_markers,
        use_ai=use_ai,
    )
    
    # 如果有AI标记且需要AI处理
    if use_ai and api_key and ai_markers:
        try:
            from notebook_cell_sources import DeepSeekClient
            
            # 创建AI客户端
            client = DeepSeekClient(api_key=api_key)
            
            # 读取文档内容
            from docx import Document
            doc = Document(final_docx)
            
            # 查找并处理AI块
            for marker in ai_markers:
                # 这里应该实现更复杂的AI块处理逻辑
                print(f"注意: AI块处理逻辑需要完善，检测到标记: {marker}")
                
            print("AI处理完成")
        except Exception as e:
            print(f"AI处理过程中出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 智能标记系统增强处理（待完善）
    if use_smart_marking:
        print("智能标记系统已启用，但具体实现需要后续完善")
        if position_mappings:
            print(f"收到位置映射: {len(position_mappings)} 条")
'''
    
    # 创建新cell
    new_cell = {
        "cell_type": "code",
        "execution_count": None,
        "id": "missing_functions_fix",
        "metadata": {},
        "outputs": [],
        "source": new_cell_content.split('\n')
    }
    
    # 在新cell前插入（在run_smart_document_generation之前）
    nb['cells'].insert(target_cell_idx, new_cell)
    
    # 保存notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    
    print(f"已在 cell {target_cell_idx} 前插入缺失的函数定义")
    return True

if __name__ == '__main__':
    if fix_notebook():
        print("修复成功!")
    else:
        print("修复失败!")