#!/usr/bin/env python3
"""
最终修复脚本：为word_gen_system_demo_with_marking.ipynb添加中文支持
"""

import json
import re
from pathlib import Path

def fix_get_template_tables(cell_source):
    """修复get_template_tables函数以正确处理中文表名"""
    lines = cell_source.split('\n')
    
    # 查找函数开始
    start_idx = None
    for i, line in enumerate(lines):
        if 'def get_template_tables(' in line:
            start_idx = i
            break
    
    if start_idx is None:
        return cell_source
    
    # 查找函数结束
    func_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    end_idx = start_idx
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() and (len(line) - len(line.lstrip()) < func_indent):
            # 检查是否是另一个定义
            if ('def ' in line and line.strip().startswith('def ')) or ('class ' in line and line.strip().startswith('class ')):
                end_idx = i - 1
                break
            # 或者是顶级语句
            end_idx = i - 1
            break
        end_idx = i
    
    # 构建新函数
    new_func = '''def get_template_tables(relation_df: pd.DataFrame, template_id: int, 
                       translation_maps: Optional[Dict[str, Dict]] = None) -> Tuple[str, List[str], str]:
    """
    获取某模板所需表名列表，并返回 main 表名（支持中文映射）。
    
    Args:
        relation_df: 关联表
        template_id: 模板ID
        translation_maps: 翻译映射字典（可选），如果不提供则直接使用表名字段
    Returns:
        (template_file, table_names, main_table)
    """
    sub = relation_df[relation_df['template_id'] == template_id]
    if sub.empty:
        raise ValueError(f'未找到 template_id={template_id} 的配置')
    
    # 获取模板文件（支持中文文件名）
    template_file = sub['template_file'].iloc[0]
    
    # 获取表名列表（如果提供了翻译映射，优先使用中文表名）
    table_names = []
    for _, row in sub.iterrows():
        table_name = str(row['table_name']).strip()
        table_name_chinese = str(row['table_name_chinese']).strip() if pd.notna(row.get('table_name_chinese', '')) else ''
        
        # 如果提供了翻译映射，优先使用中文表名
        if translation_maps and table_name_chinese:
            # 检查中文表名是否在映射中
            en_table = translation_maps['table_cn_to_en'].get(table_name_chinese)
            if en_table:
                table_names.append(en_table)
            else:
                table_names.append(table_name)
        else:
            table_names.append(table_name)
    
    # 去重
    table_names = list(set(table_names))
    
    # 获取主表
    main_rows = sub[sub['role'].astype(str).str.lower() == 'main']
    if len(main_rows) != 1:
        raise ValueError('关联表中 role=main 必须且只能有一条，用于绑定 data 别名')
    
    main_table = main_rows['table_name'].iloc[0]
    
    # 如果提供了翻译映射，并且主表有中文名，检查是否需要使用中文名
    if translation_maps:
        main_table_chinese = str(main_rows['table_name_chinese'].iloc[0]).strip() if 'table_name_chinese' in main_rows.columns and pd.notna(main_rows['table_name_chinese'].iloc[0]) else ''
        if main_table_chinese:
            # 检查中文表名是否在映射中
            en_main_table = translation_maps['table_cn_to_en'].get(main_table_chinese)
            if en_main_table:
                main_table = en_main_table
    
    return template_file, table_names, main_table'''
    
    # 替换函数
    lines[start_idx:end_idx+1] = new_func.split('\n')
    return '\n'.join(lines)

def fix_render_prompt(cell_source):
    """修复render_prompt函数以支持中文变量名"""
    lines = cell_source.split('\n')
    
    # 查找函数开始
    start_idx = None
    for i, line in enumerate(lines):
        if 'def render_prompt(' in line:
            start_idx = i
            break
    
    if start_idx is None:
        return cell_source
    
    # 查找函数结束
    func_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    end_idx = start_idx
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() and (len(line) - len(line.lstrip()) < func_indent):
            # 检查是否是另一个定义
            if ('def ' in line and line.strip().startswith('def ')) or ('class ' in line and line.strip().startswith('class ')):
                end_idx = i - 1
                break
            # 或者是顶级语句
            end_idx = i - 1
            break
        end_idx = i
    
    # 构建新函数
    new_func = '''def render_prompt(prompt_tpl: str, context: dict, 
                       translation_maps: Optional[Dict[str, Dict]] = None) -> str:
    """
    渲染 prompt 模板中的变量（支持中文变量名）。
    
    Args:
        prompt_tpl: prompt 模板字符串，可能包含 {{变量.字段}} 或 {{中文表名.中文字段名}}
        context: 渲染上下文（包含英文别名和可能的英文别名）
        translation_maps: 翻译映射字典（可选），用于处理中文变量名
    
    Returns:
        渲染后的 prompt 字符串
    """
    if not prompt_tpl:
        return ''
    
    result = prompt_tpl
    
    # 先处理中文变量名（如果提供了翻译映射）
    if translation_maps:
        # 查找所有变量模式：{{表名.字段名}} 或 {{表名.数字.字段名}}
        variable_pattern = r'\{\{\s*([^{}]+?)\s*\}\}'
        for match in re.finditer(variable_pattern, prompt_tpl):
            var_expr = match.group(1).strip()
            
            # 解析变量表达式：可能是 "表名.字段名" 或 "表名.数字.字段名"
            parts = var_expr.split('.')
            if len(parts) >= 2:
                table_part = parts[0]
                field_part = parts[-1]
                
                # 检查是否是中文表名
                if table_part in translation_maps['table_cn_to_en']:
                    # 中文表名，需要翻译
                    en_table = translation_maps['table_cn_to_en'][table_part]
                    
                    # 检查是否是中文字段名
                    if en_table in translation_maps['field_en_to_cn_by_table']:
                        cn_to_en_fields = {}
                        for en_field, cn_field in translation_maps['field_en_to_cn_by_table'][en_table].items():
                            cn_to_en_fields[cn_field] = en_field
                        
                        if field_part in cn_to_en_fields:
                            # 中文字段名，需要翻译
                            en_field = cn_to_en_fields[field_part]
                            
                            # 重建变量表达式
                            if len(parts) == 2:
                                new_var_expr = f'{en_table}.{en_field}'
                            else:
                                # 处理类似 "表名.数字.字段名" 的情况
                                middle_parts = parts[1:-1]
                                new_var_expr = f'{en_table}.{".".join(middle_parts)}.{en_field}'
                            
                            # 替换变量
                            old_var = f'{{{{{var_expr}}}}}'
                            new_var = f'{{{{{new_var_expr}}}}}'
                            result = result.replace(old_var, new_var)
    
    # 使用Jinja2渲染（支持英文变量）
    from jinja2 import Environment, StrictUndefined
    env = Environment(undefined=StrictUndefined)
    
    try:
        template = env.from_string(result)
        rendered = template.render(**context)
        return rendered
    except Exception as e:
        print(f'渲染 prompt 时出错: {e}')
        # 回退到简单替换
        return _simple_render_prompt(result, context, translation_maps)

def _simple_render_prompt(prompt_tpl: str, context: dict, 
                         translation_maps: Optional[Dict[str, Dict]] = None) -> str:
    """
    简单渲染 prompt 模板（回退方法）。
    """
    result = prompt_tpl
    
    # 查找所有变量模式
    variable_pattern = r'\{\{\s*([^{}]+?)\s*\}\}'
    
    for match in re.finditer(variable_pattern, prompt_tpl):
        var_expr = match.group(1).strip()
        
        # 尝试从上下文中获取值
        value = None
        try:
            # 支持点号访问嵌套结构
            parts = var_expr.split('.')
            obj = context
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part)
                elif isinstance(obj, list) and part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(obj):
                        obj = obj[idx]
                    else:
                        obj = None
                        break
                else:
                    obj = None
                    break
            value = obj
        except:
            value = None
        
        if value is not None:
            # 格式化值
            if isinstance(value, (int, float)):
                str_value = str(value)
            elif isinstance(value, str):
                str_value = value
            else:
                str_value = str(value)
            
            # 替换
            old_var = f'{{{{{var_expr}}}}}'
            result = result.replace(old_var, str_value)
    
    return result'''
    
    # 替换函数
    lines[start_idx:end_idx+1] = new_func.split('\n')
    return '\n'.join(lines)

def fix_build_trace_annotation_pairs(cell_source):
    """修复build_trace_annotation_pairs函数以显示中文表名和字段名"""
    lines = cell_source.split('\n')
    
    # 查找函数开始
    start_idx = None
    for i, line in enumerate(lines):
        if 'def build_trace_annotation_pairs(' in line:
            start_idx = i
            break
    
    if start_idx is None:
        return cell_source
    
    # 查找函数结束
    func_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    end_idx = start_idx
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() and (len(line) - len(line.lstrip()) < func_indent):
            # 检查是否是另一个定义
            if ('def ' in line and line.strip().startswith('def ')) or ('class ' in line and line.strip().startswith('class ')):
                end_idx = i - 1
                break
            # 或者是顶级语句
            end_idx = i - 1
            break
        end_idx = i
    
    # 构建新函数
    new_func = '''def build_trace_annotation_pairs(trace_map: Dict[str, Any], 
                         translation_maps: Optional[Dict[str, Dict]] = None) -> List[Tuple[str, str]]:
    """
    生成 (显示字符串, 批注内容) 列表，显示字符串按长度降序，减少短词匹配。
    支持TraceItem及条件表达式字典格式。
    如果提供了翻译映射，批注内容会显示中文表名和字段名。
    """
    pairs: List[Tuple[str, str]] = []
    for _k, ti in trace_map.items():
        # 获取显示值
        if hasattr(ti, 'value'):
            disp = format_display_value(ti.value)
        elif isinstance(ti, dict) and 'value' in ti:
            disp = format_display_value(ti['value'])
        else:
            continue

        if disp == '':
            continue

        # 构建批注内容
        if isinstance(ti, dict) and ti.get('_is_condition'):
            # 条件表达式批注
            condition = ti.get('field', '')
            expr_info = ti.get('_expression_info', {})
            variables = expr_info.get('variables', [])
            table = ti.get('table', '__condition__')
            
            # 如果有翻译映射，尝试显示中文表名
            table_display = table
            if translation_maps:
                cn_table = translation_maps['table_en_to_cn'].get(table, table)
                table_display = cn_table
            
            # 构建详细批注内容
            var_desc = f"条件表达式: {condition}"
            if variables:
                # 如果有翻译映射，尝试显示中文变量名
                if translation_maps:
                    cn_vars = []
                    for var in variables:
                        # 解析变量：可能是 "表名.字段名" 或 "表名.数字.字段名"
                        parts = var.split('.')
                        if len(parts) >= 2:
                            table_part = parts[0]
                            field_part = parts[-1]
                            
                            # 翻译表名
                            cn_table_part = translation_maps['table_en_to_cn'].get(table_part, table_part)
                            
                            # 翻译字段名
                            cn_field_part = field_part
                            if table_part in translation_maps['field_en_to_cn_by_table']:
                                cn_field_part = translation_maps['field_en_to_cn_by_table'][table_part].get(field_part, field_part)
                            
                            # 重建变量
                            if len(parts) == 2:
                                cn_var = f'{cn_table_part}.{cn_field_part}'
                            else:
                                middle_parts = parts[1:-1]
                                cn_var = f'{cn_table_part}.{".".join(middle_parts)}.{cn_field_part}'
                            cn_vars.append(cn_var)
                        else:
                            cn_vars.append(var)
                    var_desc += f" (变量: {', '.join(cn_vars)})"
                else:
                    var_desc += f" (变量: {', '.join(variables)})"

            body = f"[数据来源] 表={table_display} 字段={condition} 值={disp} | 路径={var_desc} | 主键={ti.get('pk', '')}"

            # 添加表达式解析信息
            if expr_info.get('parsed'):
                parsed = expr_info['parsed']
                operator_map = {'lt': '<', 'le': '<=', 'gt': '>', 'ge': '>=', 'eq': '==', 'ne': '!=', 'in': 'in', 'not_in': 'not in'}
                op_symbol = operator_map.get(parsed.get('operator', ''), parsed.get('operator', ''))
                
                # 如果有翻译映射，尝试显示中文变量名
                left_display = parsed.get('left', '')
                right_display = parsed.get('right', '')
                
                if translation_maps:
                    # 尝试翻译左侧表达式中的变量
                    for var in variables:
                        if var in left_display:
                            # 解析变量
                            parts = var.split('.')
                            if len(parts) >= 2:
                                table_part = parts[0]
                                field_part = parts[-1]
                                
                                # 翻译表名
                                cn_table_part = translation_maps['table_en_to_cn'].get(table_part, table_part)
                                
                                # 翻译字段名
                                cn_field_part = field_part
                                if table_part in translation_maps['field_en_to_cn_by_table']:
                                    cn_field_part = translation_maps['field_en_to_cn_by_table'][table_part].get(field_part, field_part)
                                
                                # 重建变量
                                if len(parts) == 2:
                                    cn_var = f'{cn_table_part}.{cn_field_part}'
                                else:
                                    middle_parts = parts[1:-1]
                                    cn_var = f'{cn_table_part}.{".".join(middle_parts)}.{cn_field_part}'
                                
                                left_display = left_display.replace(var, cn_var)
                
                body += f" | 表达式: {left_display} {op_symbol} {right_display}"
        else:
            # 普通数据字段的批注
            table = ti.table if hasattr(ti, 'table') else ti.get('table', '')
            field = ti.field if hasattr(ti, 'field') else ti.get('field', '')
            var = ti.var if hasattr(ti, 'var') else ti.get('var', '')
            pk = ti.pk if hasattr(ti, 'pk') else ti.get('pk', '')
            
            # 如果有翻译映射，显示中文表名和字段名
            table_display = table
            field_display = field
            
            if translation_maps:
                cn_table = translation_maps['table_en_to_cn'].get(table, table)
                table_display = cn_table
                
                # 获取中文字段名
                if table in translation_maps['field_en_to_cn_by_table']:
                    cn_field = translation_maps['field_en_to_cn_by_table'][table].get(field, field)
                    field_display = cn_field
            
            body = f"[数据来源] 表={table_display} 字段={field_display} 值={disp} | 路径={var} | 主键={pk}"

        pairs.append((disp, body))
    
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs'''
    
    # 替换函数
    lines[start_idx:end_idx+1] = new_func.split('\n')
    return '\n'.join(lines)

def fix_finalize_rendered_document(cell_source):
    """修复finalize_rendered_document函数以传递translation_maps参数"""
    lines = cell_source.split('\n')
    modified = False
    
    # 查找annotate_values_in_document调用
    for i, line in enumerate(lines):
        if 'annotate_values_in_document(' in line:
            # 检查是否已经传递了translation_maps
            if 'translation_maps' not in line:
                # 查找build_trace_annotation_pairs调用
                for j in range(max(0, i-10), min(len(lines), i+10)):
                    if 'build_trace_annotation_pairs(' in lines[j]:
                        # 修改这个调用以包含translation_maps
                        if 'translation_maps' not in lines[j]:
                            lines[j] = lines[j].replace('build_trace_annotation_pairs(trace_map)', 
                                                       'build_trace_annotation_pairs(trace_map, translation_maps=translation_maps)')
                            modified = True
    
    if modified:
        return '\n'.join(lines)
    return cell_source

def fix_run_smart_document_generation(cell_source):
    """修复run_smart_document_generation函数以传递translation_maps参数"""
    lines = cell_source.split('\n')
    modified = False
    
    # 查找build_report_contexts调用
    for i, line in enumerate(lines):
        if 'build_report_contexts(' in line and 'translation_maps' not in line:
            # 修改这个调用以包含translation_maps
            if 'template_path=tpl_path' in line:
                # 在template_path参数后添加translation_maps
                lines[i] = lines[i].replace('template_path=tpl_path', 'template_path=tpl_path, translation_maps=translation_maps')
                modified = True
            else:
                # 尝试在其他位置添加
                lines[i] = lines[i].replace(')', ', translation_maps=translation_maps)')
                modified = True
    
    # 查找render_prompt调用
    for i, line in enumerate(lines):
        if 'render_prompt(' in line and 'translation_maps' not in line:
            # 修改这个调用以包含translation_maps
            lines[i] = lines[i].replace('render_prompt(', 'render_prompt(prompt_tpl, context, translation_maps=translation_maps)')
            # 需要更精确的替换
            if 'prompt_tpl,' in line and 'context' in line:
                parts = line.split('render_prompt(')
                if len(parts) > 1:
                    inner = parts[1].split(')')[0]
                    if ',' in inner:
                        new_inner = inner + ', translation_maps=translation_maps'
                        lines[i] = lines[i].replace(f'render_prompt({inner})', f'render_prompt({new_inner})')
                        modified = True
    
    # 查找finalize_rendered_document调用
    for i, line in enumerate(lines):
        if 'finalize_rendered_document(' in line and 'translation_maps' not in line:
            # 在参数列表中添加translation_maps
            if 'ai_markers=' in line:
                # 在ai_markers参数前添加translation_maps
                lines[i] = lines[i].replace('ai_markers=', 'translation_maps=translation_maps, ai_markers=')
                modified = True
            elif 'use_smart_marking' in line:
                # 在use_smart_marking参数前添加translation_maps
                lines[i] = lines[i].replace('use_smart_marking=', 'translation_maps=translation_maps, use_smart_marking=')
                modified = True
    
    # 查找finalize_rendered_document_enhanced调用
    for i, line in enumerate(lines):
        if 'finalize_rendered_document_enhanced(' in line and 'translation_maps' not in line:
            # 在参数列表中添加translation_maps
            if 'position_mappings' in line:
                # 在position_mappings参数前添加translation_maps
                lines[i] = lines[i].replace('position_mappings=', 'translation_maps=translation_maps, position_mappings=')
                modified = True
    
    if modified:
        return '\n'.join(lines)
    return cell_source

def main():
    notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
    
    # 创建备份
    backup_path = notebook_path.with_suffix('.ipynb.bak')
    if not backup_path.exists():
        import shutil
        shutil.copy2(notebook_path, backup_path)
        print(f"已创建备份: {backup_path}")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    modifications = []
    
    for cell_idx, cell in enumerate(nb['cells']):
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            original_source = source
            
            # 1. 修复get_template_tables
            if 'def get_template_tables(' in source:
                new_source = fix_get_template_tables(source)
                if new_source != source:
                    cell['source'] = new_source.split('\n')
                    modifications.append(f'cell {cell_idx}: 修复get_template_tables函数')
            
            # 2. 修复render_prompt
            elif 'def render_prompt(' in source:
                new_source = fix_render_prompt(source)
                if new_source != source:
                    cell['source'] = new_source.split('\n')
                    modifications.append(f'cell {cell_idx}: 修复render_prompt函数')
            
            # 3. 修复build_trace_annotation_pairs
            elif 'def build_trace_annotation_pairs(' in source:
                new_source = fix_build_trace_annotation_pairs(source)
                if new_source != source:
                    cell['source'] = new_source.split('\n')
                    modifications.append(f'cell {cell_idx}: 修复build_trace_annotation_pairs函数')
            
            # 4. 修复finalize_rendered_document
            elif 'def finalize_rendered_document(' in source:
                new_source = fix_finalize_rendered_document(source)
                if new_source != source:
                    cell['source'] = new_source.split('\n')
                    modifications.append(f'cell {cell_idx}: 修复finalize_rendered_document函数')
            
            # 5. 修复run_smart_document_generation
            elif 'def run_smart_document_generation(' in source:
                new_source = fix_run_smart_document_generation(source)
                if new_source != source:
                    cell['source'] = new_source.split('\n')
                    modifications.append(f'cell {cell_idx}: 修复run_smart_document_generation函数')
    
    # 保存修改后的notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    
    print(f"\n修改完成！共进行了{len(modifications)}项修改：")
    for mod in modifications:
        print(f"  - {mod}")
    
    print("\n重要提醒：")
    print("1. 系统现在支持中文模板文件名（如'证券化内部尽调报告中文模板.docx'）")
    print("2. 模板中的变量可以使用中文表名和中文字段名，例如：{{借款人数据表.借款人姓名}}")
    print("3. config/template_relation.xlsx中的template_file字段可以使用中文文件名")
    print("4. 批注中会显示中文表名和字段名")
    print("5. 确保config/entity_schema.xlsx中有正确的table_name_chinese和field_name_chinese映射")

if __name__ == '__main__':
    main()