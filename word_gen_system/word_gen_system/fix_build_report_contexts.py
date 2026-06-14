import json
import re
from pathlib import Path

def fix_build_report_contexts():
    notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Find the cell containing build_report_contexts
    for cell in nb['cells']:
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            if 'def build_report_contexts(' in source:
                print("Found build_report_contexts function, fixing...")
                
                # First, let's see the current state
                lines = source.split('\n')
                
                # We need to replace from "def build_report_contexts(" to the end of function
                # Find start index
                start_idx = None
                for i, line in enumerate(lines):
                    if 'def build_report_contexts(' in line:
                        start_idx = i
                        break
                
                if start_idx is None:
                    print("Could not find function start")
                    return
                
                # Find the end of the function (look for 'return out' and then lines with less indentation)
                # First, get the indentation of the function definition
                func_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
                
                # Look for 'return out' line
                return_idx = None
                for i in range(start_idx, len(lines)):
                    if 'return out' in lines[i].strip():
                        return_idx = i
                        break
                
                if return_idx is None:
                    print("Could not find 'return out' line")
                    return
                
                # Find the line after return that has less indentation than the function
                end_idx = return_idx
                for i in range(return_idx + 1, len(lines)):
                    line = lines[i]
                    if line.strip():  # non-empty line
                        line_indent = len(line) - len(line.lstrip())
                        if line_indent <= func_indent and not line.lstrip().startswith('#'):
                            # This line is at same or less indentation, and not a comment
                            # Check if it's another function definition
                            if 'def ' in line and line.strip().startswith('def '):
                                end_idx = i - 1
                                break
                            elif line_indent < func_indent:
                                end_idx = i - 1
                                break
                
                # Now we have start_idx to end_idx inclusive
                print(f"Function spans lines {start_idx} to {end_idx}")
                
                # Build the new function
                new_function = '''def build_report_contexts(
    schema_df: pd.DataFrame,
    tables: Dict[str, pd.DataFrame],
    main_table: str,
    alias_map: Dict[str, str] | None = None,
    template_path: Path | None = None,
    template_text: str | None = None,
    translation_maps: Optional[Dict[str, Dict]] = None,
) -> List[Tuple[dict, Dict[str, Any]]]:
    """
    按主表主键逐行生成报告；主表一行则仅一份。
    辅表：与主键同名列则过滤；单行 dict，多行 list；Trace 含 products.i.field。
    
    新增参数:
        template_path: Word模板路径（用于提取条件表达式）
        template_text: 模板文本（如果template_path未提供）
        translation_maps: 中英文翻译映射字典（如果提供，将创建中文别名）
    """
    if alias_map is None:
        alias_map = {t: t for t in tables.keys()}

    pk_field = get_primary_key_field(schema_df, main_table)
    if pk_field not in tables[main_table].columns:
        raise ValueError(f'主表 {main_table} 缺少主键列 {pk_field}')

    out: List[Tuple[dict, Dict[str, Any]]] = []
    for idx, row in tables[main_table].iterrows():
        pk_val = row[pk_field]
        context: dict = {}
        trace: Dict[str, Any] = {}

        # 处理主表数据（data别名）
        main_data = row.to_dict()
        context['data'] = main_data
        
        # 如果提供了翻译映射，并且主表有中文名，也创建中文data别名
        main_table_cn = None
        if translation_maps:
            main_table_cn = translation_maps['table_en_to_cn'].get(main_table)
            if main_table_cn:
                # 创建中文字段名的主表数据
                cn_main_data = {}
                field_map = translation_maps['field_en_to_cn_by_table'].get(main_table, {})
                for en_field, cn_field in field_map.items():
                    if en_field in main_data:
                        cn_main_data[cn_field] = main_data[en_field]
                # 如果创建了中文数据，添加到上下文
                if cn_main_data:
                    context[main_table_cn] = cn_main_data
        
        # 为主表每个字段创建trace
        for k, v in main_data.items():
            var = f'data.{k}'
            trace[var] = TraceItem(
                var=var, table=main_table, field=k, value=v, pk=pk_val,
                row_index=int(idx), source_file=f'{main_table}.xlsx',
            )

        for tname, df in tables.items():
            if tname == main_table:
                continue
            alias = alias_map.get(tname, tname)
            sub = df[df[pk_field] == pk_val] if pk_field in df.columns else df

            if len(sub) == 1:
                obj = sub.iloc[0].to_dict()
                context[alias] = obj
                ri = int(sub.index[0])
                for k, v in obj.items():
                    var = f'{alias}.{k}'
                    trace[var] = TraceItem(
                        var=var, table=tname, field=k, value=v, pk=pk_val,
                        row_index=ri, source_file=f'{tname}.xlsx',
                    )
                
                # 如果提供了翻译映射，并且该表有中文名，创建中文别名
                if translation_maps:
                    table_cn = translation_maps['table_en_to_cn'].get(tname)
                    if table_cn:
                        # 创建中文字段名的数据
                        cn_obj = {}
                        field_map = translation_maps['field_en_to_cn_by_table'].get(tname, {})
                        for en_field, cn_field in field_map.items():
                            if en_field in obj:
                                cn_obj[cn_field] = obj[en_field]
                        # 如果创建了中文数据，添加到上下文
                        if cn_obj:
                            context[table_cn] = cn_obj
                        
                        # 为中文字段创建trace（指向相同的值和源表）
                        for en_field, cn_field in field_map.items():
                            if en_field in obj:
                                var_cn = f'{table_cn}.{cn_field}'
                                trace[var_cn] = TraceItem(
                                    var=var_cn, table=tname, field=en_field, value=obj[en_field], pk=pk_val,
                                    row_index=ri, source_file=f'{tname}.xlsx',
                                )
            else:
                lst = sub.to_dict(orient='records')
                context[alias] = lst
                
                # 如果提供了翻译映射，并且该表有中文名，创建中文别名列表
                cn_lst = None
                field_map = None
                if translation_maps:
                    table_cn = translation_maps['table_en_to_cn'].get(tname)
                    if table_cn:
                        field_map = translation_maps['field_en_to_cn_by_table'].get(tname, {})
                        if field_map:
                            cn_lst = []
                            for rec in lst:
                                cn_rec = {}
                                for en_field, cn_field in field_map.items():
                                    if en_field in rec:
                                        cn_rec[cn_field] = rec[en_field]
                                cn_lst.append(cn_rec)
                            if cn_lst:
                                context[table_cn] = cn_lst
                
                for row_i, rec in enumerate(lst):
                    ri = int(sub.index[row_i]) if row_i < len(sub.index) else None
                    for k, v in rec.items():
                        var = f'{alias}.{row_i}.{k}'
                        trace[var] = TraceItem(
                            var=var, table=tname, field=k, value=v, pk=pk_val,
                            row_index=ri, source_file=f'{tname}.xlsx',
                        )
                    
                    # 为中文字段创建trace（如果存在）
                    if cn_lst and field_map and row_i < len(cn_lst):
                        cn_rec = cn_lst[row_i]
                        for en_field, cn_field in field_map.items():
                            if en_field in rec:
                                var_cn = f'{table_cn}.{row_i}.{cn_field}'
                                trace[var_cn] = TraceItem(
                                    var=var_cn, table=tname, field=en_field, value=rec[en_field], pk=pk_val,
                                    row_index=ri, source_file=f'{tname}.xlsx',
                                )

        # 添加条件表达式溯源（通用，支持任意条件表达式）
        add_condition_traces(
            context=context,
            trace_map=trace,
            pk_val=pk_val,
            template_path=template_path,
            template_text=template_text
        )
        
        out.append((context, trace))

    return out'''
                
                # Replace the function lines
                new_lines = lines[:start_idx] + new_function.split('\n') + lines[end_idx+1:]
                
                # Update the cell source
                cell['source'] = '\n'.join(new_lines)
                print("Fixed build_report_contexts function")
                break
    
    # Save the modified notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    print("Notebook saved successfully")

if __name__ == '__main__':
    fix_build_report_contexts()