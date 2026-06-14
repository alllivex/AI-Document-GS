import json
import re

# 读取notebook
with open('word_gen_system_demo_with_marking.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# 找到run_smart_document_generation函数
for cell_idx, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def run_smart_document_generation' in source:
            print(f'修复 Cell {cell_idx}')
            lines = cell['source']
            
            # 检查是否已经有import re
            has_import_re = False
            for line in lines:
                if 'import re' in line:
                    has_import_re = True
                    break
            
            # 如果没有，在函数开头添加
            new_lines = []
            func_started = False
            for i, line in enumerate(lines):
                new_lines.append(line)
                
                # 在def行之后添加import re
                if not has_import_re and line.strip().startswith('def run_smart_document_generation'):
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + 'import re')
                    print('添加import re')
                    has_import_re = True
                
                # 在tables = load_data_tables行之后添加template_info代码
                if 'tables = load_data_tables(data_dir, table_names)' in line:
                    # 先添加这一行
                    # 然后添加template_info代码
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + '            # 获取模板名称')
                    new_lines.append(' ' * indent + '            template_info = relation_df[relation_df[\'template_id\'] == tid].iloc[0]')
                    new_lines.append(' ' * indent + '            template_name = template_info[\'template_name\']')
                    new_lines.append(' ' * indent + '            # 清理模板名称作为文件名前缀')
                    new_lines.append(' ' * indent + '            template_name_safe = re.sub(r\'[<>:\"/\\\\|?*]\', \'_\', template_name)')
                    new_lines.append(' ' * indent + '            template_name_safe = re.sub(r\'\\s+\', \'_\', template_name_safe)')
                    new_lines.append(' ' * indent + '            template_name_safe = template_name_safe.strip(\'_\')')
                    print('添加template_info代码')
            
            # 替换mid_name和final_name行
            final_lines = []
            for line in new_lines:
                if 'mid_name = f\'mid_tpl{tid}_{safe_name}.docx\'' in line:
                    # 替换为新的mid_name
                    indent = len(line) - len(line.lstrip())
                    new_line = ' ' * indent + '            mid_name = f\'mid_{template_name_safe}_{safe_name}.docx\''
                    print(f'替换mid_name: {line.strip()} -> {new_line.strip()}')
                    final_lines.append(new_line)
                elif 'final_name = f\'report_tpl{tid}_{safe_name}.docx\'' in line:
                    # 替换为新的final_name
                    indent = len(line) - len(line.lstrip())
                    new_line = ' ' * indent + '            final_name = f\'{template_name_safe}_{safe_name}.docx\''
                    print(f'替换final_name: {line.strip()} -> {new_line.strip()}')
                    final_lines.append(new_line)
                else:
                    final_lines.append(line)
            
            # 更新单元格
            cell['source'] = final_lines
            break

# 保存notebook
with open('word_gen_system_demo_with_marking.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=2, ensure_ascii=False)

print('修复完成')