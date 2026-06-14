import json
from pathlib import Path

def analyze_notebook():
    notebook_path = Path('word_gen_system_demo_with_marking.ipynb')
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Find all cells with key functions
    key_functions = [
        'load_template_relation',
        'get_template_tables', 
        'build_trace_annotation_pairs',
        'render_docx_template',
        'render_docx_template_with_markers',
        'render_prompt'
    ]
    
    for cell in nb['cells']:
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            for func_name in key_functions:
                if f'def {func_name}(' in source:
                    print(f'\n=== Found {func_name}() ===')
                    lines = source.split('\n')
                    start = None
                    for i, line in enumerate(lines):
                        if f'def {func_name}(' in line:
                            start = i
                            break
                    
                    if start is not None:
                        # Find end of function
                        func_indent = len(lines[start]) - len(lines[start].lstrip())
                        end = start
                        for i in range(start + 1, len(lines)):
                            line = lines[i]
                            if line.strip() and (len(line) - len(line.lstrip()) < func_indent):
                                # Check if this is another definition
                                if ('def ' in line and line.strip().startswith('def ')) or ('class ' in line and line.strip().startswith('class ')):
                                    end = i - 1
                                    break
                                # Or if it's a top-level statement
                                end = i - 1
                                break
                            end = i
                        
                        # Print function
                        for j in range(start, end + 1):
                            print(f'{j:3}: {lines[j]}')
                    break
    
    # Also look for where template_path is constructed from template_file
    print('\n=== Searching for template file resolution logic ===')
    for cell in nb['cells']:
        if cell.get('cell_type') == 'code':
            source = ''.join(cell['source'])
            if 'DIRS[\'templates\'] / template_file' in source:
                print('Found template file resolution:')
                lines = source.split('\n')
                for i, line in enumerate(lines):
                    if 'DIRS[\'templates\'] / template_file' in line:
                        print(f'{i:3}: {line}')
                        # Show context
                        for j in range(max(0, i-2), min(len(lines), i+3)):
                            if j != i:
                                print(f'{j:3}: {lines[j]}')

if __name__ == '__main__':
    analyze_notebook()