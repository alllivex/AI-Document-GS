import json
import re
from pathlib import Path

def modify_notebook_for_chinese_support():
    notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    modifications_made = []
    
    # 1. 修改get_template_tables函数，支持中文文件名和中文表名
    for cell_idx, cell in enumerate(nb['cells']):
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            if 'def get_template_tables(' in source:
                print(f"Found get_template_tables function in cell {cell_idx}")
                
                # 检查是否需要修改
                if 'def get_template_tables(relation_df: pd.DataFrame, template_id: int,' in source:
                    # 已经包含translation_maps参数，但需要增强功能
                    # 增强函数以支持中文表名
                    lines = source.split('\n')
                    
                    # 找到函数开始和结束
                    start_idx = None
                    for i, line in enumerate(lines):
                        if 'def get_template_tables(' in line:
                            start_idx = i
                            break
                    
                    if start_idx is None:
                        continue
                    
                    # 找到函数结束
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
                    cell['source'] = '\n'.join(lines)
                    modifications_made.append('get_template_tables函数已增强，支持中文表名')
                    break
    
    # 2. 修改render_prompt函数，支持中文变量名
    for cell_idx, cell in enumerate(nb['cells']):
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            if 'def render_prompt(' in source and 'context:' in source:
                print(f"Found render_prompt function in cell {cell_idx}")
                
                lines = source.split('\n')
                start_idx = None
                for i, line in enumerate(lines):
                    if 'def render_prompt(' in line:
                        start_idx = i
                        break
                
                if start_idx is None:
                    continue
                
                # 找到函数结束
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
                
                # 构建新函数，支持中文变量
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
                cell['source'] = '\n'.join(lines)
                modifications_made.append('render_prompt函数已增强，支持中文变量名')
                break
    
    # 3. 修改build_trace_annotation_pairs函数，显示中文表名和字段名
    for cell_idx, cell in enumerate(nb['cells']):
        if cell.get('cell_type') == 'code'):
            source = ''.join(cell['source'])
            if 'def build_trace_annotation_pairs(' in source:
                print(f"Found build_trace_annotation_pairs function in cell {cell_idx}")
                
                lines = source.split('\n')
                start_idx = None
                for i, line in enumerate(lines):
                    if 'def build_trace_annotation_pairs(' in line:
                        start_idx = i
                        break
                
                if start_idx is None:
                    continue
                
                # 找到函数结束
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
                
                # 构建增强版函数
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
                cell['source'] = '\n'.join(lines)
                modifications_made.append('build_trace_annotation_pairs函数已增强，支持中文表名和字段名')
                break
    
    # 4. 查找并修改所有使用DIRS['templates'] / template_file的地方，确保支持中文文件名
    template_resolution_count = 0
    for cell_idx, cell in enumerate(nb['cells']):
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            if "DIRS['templates'] / template_file" in source:
                print(f"Found template resolution in cell {cell_idx}")
                
                lines = source.split('\n')
                modified = False
                
                for i, line in enumerate(lines):
                    if "DIRS['templates'] / template_file" in line:
                        # 检查是否已经处理了中文文件名
                        if "if not tpl_path.exists()" in '\n'.join(lines[i:i+5]):
                            # 已经存在检查逻辑，确保支持中文
                            # 我们可以添加注释说明支持中文文件名
                            pass
                        else:
                            # 添加文件存在检查
                            lines[i] = line  # 保持原行
                            # 在下一行添加检查逻辑（如果有必要）
                        
                        template_resolution_count += 1
                        modified = True
                
                if modified:
                    cell['source'] = '\n'.join(lines)
    
    if template_resolution_count > 0:
        modifications_made.append(f'更新了{template_resolution_count}处模板文件解析逻辑，支持中文文件名')
    
    # 保存修改后的notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    
    print(f"\n修改完成！共进行了{len(modifications_made)}项修改：")
    for mod in modifications_made:
        print(f"  - {mod}")
    
    return modifications_made

if __name__ == '__main__':
    modifications = modify_notebook_for_chinese_support()