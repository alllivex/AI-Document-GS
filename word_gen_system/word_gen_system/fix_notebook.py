#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复word_gen_system_demo_with_marking.ipynb中的run_smart_document_generation函数
将if use_smart_marking:块替换为安全的方案C
"""

import json
import os
import sys
from pathlib import Path

def fix_notebook(notebook_path: Path):
    """修复笔记本文件中的run_smart_document_generation函数"""
    
    print(f"读取笔记本文件: {notebook_path}")
    with open(notebook_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 查找包含run_smart_document_generation函数的cell
    cells = data['cells']
    for cell_idx, cell in enumerate(cells):
        if cell.get('cell_type') == 'code':
            lines = cell.get('source', [])
            
            # 查找run_smart_document_generation函数
            for i, line in enumerate(lines):
                if 'def run_smart_document_generation(' in line:
                    print(f"在Cell {cell_idx+1}中找到run_smart_document_generation函数")
                    
                    # 查找if use_smart_marking:块
                    for j in range(i, len(lines)):
                        if 'if use_smart_marking:' in lines[j]:
                            print(f"在行{j+1}找到if use_smart_marking:")
                            
                            # 查找else:位置
                            else_line = -1
                            for k in range(j+1, len(lines)):
                                if 'else:' in lines[k]:
                                    else_line = k
                                    break
                            
                            if else_line != -1:
                                print(f"else:在行{else_line+1}")
                                
                                # 构建修复后的代码块
                                fixed_block = '''            if use_smart_marking:
                print("注意: 智能标记系统当前仅支持批注，文档渲染使用原方式")
                # 使用原方式渲染文档
                render_docx_template(tpl_path, ctx, mid_path)
                
                # 智能标记仅用于批注（需要后续完善）
                position_mappings = None  # 暂时不提供位置映射
                
                # 使用增强的最终文档处理函数（支持智能批注）
                finalize_rendered_document_enhanced(
                    mid_path,
                    tpl_path,
                    ctx,
                    trace,
                    final_path,
                    use_ai=use_ai,
                    api_key=api_key,
                    ai_markers=list(AI_BLOCK_MARKERS),
                    use_smart_marking=True,
                    position_mappings=position_mappings
                )'''
                                
                                # 替换代码块（从if use_smart_marking:到else:之前）
                                # 我们需要将多行替换为新的块
                                # 首先计算新块的行数
                                new_lines = fixed_block.splitlines(keepends=True)
                                
                                # 替换原始行
                                lines[j:else_line] = new_lines
                                
                                print(f"已修复Cell {cell_idx+1}中的if use_smart_marking:块")
                                
                                # 更新cell内容
                                cell['source'] = lines
                                
                                # 保存修复后的文件
                                backup_path = notebook_path.with_suffix('.ipynb.backup_fixed')
                                fixed_path = notebook_path
                                
                                # 先备份原文件
                                import shutil
                                shutil.copy2(notebook_path, backup_path)
                                print(f"已备份原文件到: {backup_path}")
                                
                                # 保存修复后的文件
                                with open(fixed_path, 'w', encoding='utf-8') as fout:
                                    json.dump(data, fout, ensure_ascii=False, indent=2)
                                
                                print(f"已保存修复后的文件到: {fixed_path}")
                                return True
                    
                    # 如果没找到if use_smart_marking:，可能是其他问题
                    print("警告: 在run_smart_document_generation函数中未找到if use_smart_marking:块")
                    return False
    
    print("错误: 未找到run_smart_document_generation函数")
    return False

def main():
    notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
    
    if not notebook_path.exists():
        print(f"错误: 文件不存在: {notebook_path}")
        return 1
    
    try:
        success = fix_notebook(notebook_path)
        if success:
            print("修复成功!")
            return 0
        else:
            print("修复失败!")
            return 1
    except Exception as e:
        print(f"修复过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())