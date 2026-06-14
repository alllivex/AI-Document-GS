import json
import re
from pathlib import Path

def modify_build_report_contexts():
    notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Find the cell containing build_report_contexts
    for cell in nb['cells']:
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            if 'def build_report_contexts(' in source:
                print("Found build_report_contexts function")
                # Replace the function with enhanced version
                # We'll replace the entire function content
                lines = source.split('\n')
                new_lines = []
                i = 0
                while i < len(lines):
                    if lines[i].strip().startswith('def build_report_contexts('):
                        # Start of function, we'll replace from here
                        new_lines.append(lines[i])
                        i += 1
                        # Skip until we find the docstring end
                        while i < len(lines) and ('"""' not in lines[i] and "'''" not in lines[i]):
                            new_lines.append(lines[i])
                            i += 1
                        # Add the docstring lines
                        if i < len(lines):
                            new_lines.append(lines[i])  # Contains opening quotes
                            i += 1
                            # Skip docstring content
                            while i < len(lines) and ('"""' not in lines[i] and "'''" not in lines[i]):
                                i += 1
                            if i < len(lines):
                                new_lines.append(lines[i])  # Closing quotes
                                i += 1
                        
                        # Now replace the rest of the function with our enhanced version
                        enhanced_func = '''    if alias_map is None:
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
                        
                        # Add the enhanced function body
                        for line in enhanced_func.split('\n'):
                            new_lines.append(line)
                        
                        # Skip the original function body
                        # Find the line with 'return out'
                        while i < len(lines) and not lines[i].strip().startswith('return out'):
                            i += 1
                        if i < len(lines):
                            # Skip the return line
                            i += 1
                        # Skip until we reach a line with less indentation (end of function)
                        while i < len(lines) and (lines[i].startswith(' ') or lines[i].startswith('\t')):
                            i += 1
                    else:
                        new_lines.append(lines[i])
                        i += 1
                
                # Update the cell source
                cell['source'] = '\n'.join(new_lines)
                print("Updated build_report_contexts function")
                break
    
    # Save the modified notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    print("Notebook saved successfully")

if __name__ == '__main__':
    modify_build_report_contexts()