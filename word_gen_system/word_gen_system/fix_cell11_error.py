import json

def fix_cell11_import():
    """修复word_gen_system_demo_with_marking.ipynb中的cell11导入错误"""
    
    with open('word_gen_system_demo_with_marking.ipynb', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed = False
    
    for i, cell in enumerate(data['cells']):
        if cell.get('cell_type') == 'code':
            lines = cell.get('source', [])
            
            # 查找包含错误导入的行
            for j, line in enumerate(lines):
                if 'from cell11 import DeepSeekClient' in line:
                    print(f'在Cell {i+1}的第{j+1}行找到错误导入，正在修复...')
                    
                    # 查找try:行
                    try_line = -1
                    for k in range(max(0, j-10), j):
                        if 'try:' in lines[k]:
                            try_line = k
                            break
                    
                    if try_line != -1:
                        # 查找except:行
                        except_line = -1
                        for k in range(j, min(len(lines), j+5)):
                            if 'except:' in lines[k]:
                                except_line = k
                                break
                        
                        if except_line != -1:
                            # 查找except块结束
                            except_end = -1
                            for k in range(except_line, min(len(lines), except_line+10)):
                                if k > except_line and (lines[k].strip() == '' or 'ai_meta = []' in lines[k]):
                                    except_end = k
                                    break
                            
                            if except_end == -1:
                                except_end = except_line + 3
                            
                            # 构建修复后的代码
                            new_lines = lines[:try_line]
                            new_lines.extend([
                                '    # AI处理（保持不变）\n',
                                '    client = None\n',
                                '    if use_ai and api_key:\n',
                                '        # 首先尝试从当前命名空间导入DeepSeekClient（如果Cell 11已经运行过）\n',
                                '        try:\n',
                                '            client = DeepSeekClient(api_key=api_key)\n',
                                '        except NameError:\n',
                                '            # 如果DeepSeekClient未定义，尝试从smart_marking_system导入\n',
                                '            try:\n',
                                '                from smart_marking_system import DeepSeekClient\n',
                                '                client = DeepSeekClient(api_key=api_key)\n',
                                '            except ImportError:\n',
                                '                # 如果smart_marking_system也不存在，尝试从notebook_cell_sources导入\n',
                                '                try:\n',
                                '                    from notebook_cell_sources import DeepSeekClient\n',
                                '                    client = DeepSeekClient(api_key=api_key)\n',
                                '                except ImportError:\n',
                                '                    # 如果所有导入都失败，则无法使用AI\n',
                                '                    print("警告: 无法导入DeepSeekClient，跳过AI处理")\n',
                                '                    client = None\n'
                            ])
                            new_lines.extend(lines[except_end:])
                            
                            # 更新单元格
                            data['cells'][i]['source'] = new_lines
                            fixed = True
                            print(f'修复完成，替换了 {except_end - try_line} 行代码')
                            
                            # 显示修复后的代码
                            print('\n修复后的代码:')
                            for k in range(try_line, min(try_line + 20, len(new_lines))):
                                print(f'{k+1:3}: {new_lines[k].rstrip()}')
                            break
                    break
    
    if fixed:
        # 保存修复后的文件
        with open('word_gen_system_demo_with_marking.ipynb', 'w', encoding='utf-8') as f:
            json.dump(data, f_out, ensure_ascii=False, indent=2)
        print('\n✅ 修复完成，文件已保存！')
    else:
        print('未找到需要修复的错误导入')

if __name__ == '__main__':
    fix_cell11_import()