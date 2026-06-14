import json
import re
from pathlib import Path

# 读取notebook
notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# 查找run_smart_document_generation函数所在的单元格
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def run_smart_document_generation' in source:
            print("找到run_smart_document_generation函数")
            
            # 修改代码
            lines = cell['source']
            new_lines = []
            for line in lines:
                if 'mid_name = f\'mid_tpl{tid}_{safe_name}.docx\'' in line:
                    # 修改mid_name
                    new_line = '            mid_name = f\'mid_{template_name_safe}_{safe_name}.docx\''
                    print(f"修改mid_name行: {line.strip()} -> {new_line}")
                    new_lines.append(new_line)
                elif 'final_name = f\'report_tpl{tid}_{safe_name}.docx\'' in line:
                    # 修改final_name
                    new_line = '            final_name = f\'{template_name_safe}_{safe_name}.docx\''
                    print(f"修改final_name行: {line.strip()} -> {new_line}")
                    new_lines.append(new_line)
                elif 'tables = load_data_tables(data_dir, table_names)' in line:
                    # 在tables = load_data_tables之后添加获取template_name的代码
                    new_lines.append(line)
                    # 添加获取template_name的代码
                    new_lines.append('            # 获取模板名称')
                    new_lines.append('            template_info = relation_df[relation_df[\'template_id\'] == tid].iloc[0]')
                    new_lines.append('            template_name = template_info[\'template_name\']')
                    new_lines.append('            # 清理模板名称作为文件名前缀')
                    new_lines.append('            template_name_safe = re.sub(r\'[<>:"/\\\\|?*]\', \'_\', template_name)')
                    new_lines.append('            template_name_safe = re.sub(r\'\\s+\', \'_\', template_name_safe)')
                    new_lines.append('            template_name_safe = template_name_safe.strip(\'_\')')
                    print("添加template_name_safe代码")
                else:
                    new_lines.append(line)
            
            # 更新单元格
            cell['source'] = new_lines
            break

# 保存修改后的notebook
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=2, ensure_ascii=False)

print(f"已更新 {notebook_path}")