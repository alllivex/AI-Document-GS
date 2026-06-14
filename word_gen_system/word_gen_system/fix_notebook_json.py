#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复Jupyter Notebook JSON语法错误"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

def validate_json_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """验证JSON文件，返回解析后的数据或None"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        data = json.loads(content)
        print(f"✓ JSON验证成功: {filepath}")
        return data
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析错误: {e}")
        print(f"  位置: 第{e.lineno}行, 第{e.colno}列")
        print(f"  上下文: {e.doc[e.pos-50:e.pos+50] if e.doc else 'N/A'}")
        return None
    except Exception as e:
        print(f"✗ 其他错误: {e}")
        return None

def fix_common_json_issues(content: str) -> str:
    """
    修复常见的JSON语法问题
    1. 未转义的控制字符
    2. 字符串中的未转义引号
    3. 多余的逗号
    4. 缺失的逗号
    """
    print("开始修复JSON常见问题...")
    
    # 备份原始内容
    original = content
    
    # 修复1: 处理字符串中的未转义双引号
    # 在Python代码字符串中，双引号需要转义为 \"
    # 模式：匹配Python代码字符串中的双引号（不在转义序列中）
    def fix_quotes_in_string(match):
        # 获取字符串内容
        string_content = match.group(1)
        # 替换未转义的双引号为转义的双引号
        # 但要注意不要破坏已经转义的引号
        # 使用负向后顾：前面不是反斜杠的双引号
        fixed = re.sub(r'(?<!\\)"', r'\"', string_content)
        # 转义反斜杠本身
        fixed = fixed.replace('\\', '\\\\')
        return f'"{fixed}"'
    
    # 只对Python代码单元格的内容进行修复
    lines = content.split('\n')
    in_code_cell = False
    in_string = False
    escape_next = False
    string_delimiter = None
    
    for i, line in enumerate(lines):
        # 检查是否在代码单元格中
        if '"cell_type": "code"' in line:
            in_code_cell = True
        elif in_code_cell and '"source": [' in line:
            # 进入源代码数组
            pass
        elif in_code_cell and line.strip() == ']' and '"source"' in lines[i-1]:
            # 退出源代码数组
            in_code_cell = False
        
        # 如果不在代码单元格中，跳过
        if not in_code_cell:
            continue
        
        # 检查行是否包含源代码行
        if line.strip().startswith('"') and line.strip().endswith('",'):
            # 这是一个源代码行
            line_content = line.strip()[1:-2]  # 移除引号和逗号
            
            # 修复常见问题
            # 1. 替换未转义的换行符为 \n
            line_content = line_content.replace('\n', '\\n')
            line_content = line_content.replace('\r', '\\r')
            line_content = line_content.replace('\t', '\\t')
            
            # 2. 确保双引号被正确转义（但不要双重转义）
            # 计算当前字符串中的引号数量
            quotes = line_content.count('"')
            backslash_quotes = line_content.count('\\"')
            unescaped_quotes = quotes - backslash_quotes
            
            if unescaped_quotes > 0:
                # 需要修复未转义的引号
                # 使用更聪明的方法：逐个字符处理
                fixed_chars = []
                j = 0
                while j < len(line_content):
                    char = line_content[j]
                    if char == '\\' and j + 1 < len(line_content):
                        # 转义序列
                        next_char = line_content[j + 1]
                        if next_char == '"':
                            # 已经是转义的引号
                            fixed_chars.append('\\"')
                            j += 2
                        else:
                            # 其他转义序列
                            fixed_chars.append(char + next_char)
                            j += 2
                    elif char == '"':
                        # 未转义的引号，需要转义
                        fixed_chars.append('\\"')
                        j += 1
                    else:
                        fixed_chars.append(char)
                        j += 1
                
                line_content = ''.join(fixed_chars)
            
            lines[i] = '    "' + line_content + '",'
    
    content = '\n'.join(lines)
    
    # 修复2: 移除对象末尾的多余逗号
    # 模式：在 } 或 ] 前的逗号
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    # 修复3: 确保逗号分隔数组元素
    # 模式：值后面直接跟着新值（缺少逗号）
    # 这比较复杂，我们让JSON解析器来检测
    
    print("常见问题修复完成")
    return content

def fix_specific_position(content: str, line_num: int, col_num: int) -> str:
    """修复特定位置的错误"""
    print(f"尝试修复第{line_num}行第{col_num}列的错误...")
    
    lines = content.split('\n')
    if line_num - 1 < len(lines):
        error_line = lines[line_num - 1]
        print(f"错误行内容: {error_line}")
        
        # 检查常见的错误模式
        # 1. 字符串中的未转义引号
        if col_num - 1 < len(error_line):
            # 查看错误位置附近的字符
            start = max(0, col_num - 20)
            end = min(len(error_line), col_num + 20)
            context = error_line[start:end]
            print(f"错误位置上下文: ...{context}...")
            
            # 尝试修复：在引号前添加反斜杠
            if col_num - 1 < len(error_line) and error_line[col_num - 1] == '"':
                # 检查前面是否已经有反斜杠
                if col_num - 2 >= 0 and error_line[col_num - 2] != '\\':
                    # 需要添加转义
                    fixed_line = error_line[:col_num - 1] + '\\' + error_line[col_num - 1:]
                    lines[line_num - 1] = fixed_line
                    print(f"已修复: 在位置{col_num}添加了转义字符")
    
    return '\n'.join(lines)

def manual_fix_based_on_content(content: str) -> str:
    """基于内容分析的手动修复"""
    print("执行基于内容分析的手动修复...")
    
    # 查找可能的问题区域
    # 1. 查找Python代码中的字符串字面量
    
    # 使用更简单的方法：先尝试解析，如果失败则逐步修复
    # 这里我们实现一个逐步修复的方法
    
    # 首先尝试标准JSON解析
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        
        # 获取错误位置
        error_pos = e.pos
        error_line = e.lineno
        error_col = e.colno
        
        # 在错误位置附近查找问题
        start = max(0, error_pos - 100)
        end = min(len(content), error_pos + 100)
        context = content[start:end]
        print(f"错误位置上下文: ...{context}...")
        
        # 尝试不同的修复策略
        fixes_applied = 0
        
        # 策略1: 修复未转义的控制字符
        # 在错误位置附近查找未转义的控制字符
        control_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07',
                        '\x08', '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12',
                        '\x13', '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a',
                        '\x1b', '\x1c', '\x1d', '\x1e', '\x1f']
        
        for char in control_chars:
            if char in content:
                # 替换控制字符为Unicode转义序列
                hex_code = hex(ord(char))[2:].zfill(4)
                content = content.replace(char, f'\\u{hex_code}')
                fixes_applied += 1
                print(f"修复了控制字符 U+{hex_code.upper()}")
        
        # 策略2: 修复字符串中的未转义引号
        # 查找模式：不在转义序列中的双引号
        # 使用状态机方法
        lines = content.split('\n')
        in_string = False
        escape_next = False
        
        for i, line in enumerate(lines):
            new_line_chars = []
            j = 0
            while j < len(line):
                char = line[j]
                
                if escape_next:
                    # 当前字符是转义序列的一部分
                    new_line_chars.append(char)
                    escape_next = False
                    j += 1
                elif char == '\\':
                    # 转义字符
                    new_line_chars.append(char)
                    escape_next = True
                    j += 1
                elif char == '"':
                    # 引号
                    if in_string:
                        # 字符串结束
                        new_line_chars.append(char)
                        in_string = False
                    else:
                        # 字符串开始
                        new_line_chars.append(char)
                        in_string = True
                    j += 1
                else:
                    new_line_chars.append(char)
                    j += 1
            
            lines[i] = ''.join(new_line_chars)
        
        content = '\n'.join(lines)
        
        print(f"应用了{fixes_applied}个修复")
        return content

def save_backup(original_path: Path) -> Path:
    """创建备份文件"""
    backup_path = original_path.with_suffix('.ipynb.backup')
    import shutil
    shutil.copy2(original_path, backup_path)
    print(f"创建备份文件: {backup_path}")
    return backup_path

def main():
    """主函数"""
    notebook_path = Path("word_gen_system_demo_with_marking.ipynb")
    
    if not notebook_path.exists():
        print(f"错误: 文件不存在: {notebook_path}")
        sys.exit(1)
    
    print(f"正在修复: {notebook_path}")
    
    # 创建备份
    backup_path = save_backup(notebook_path)
    
    # 读取文件内容
    with open(notebook_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # 验证原始JSON
    print("\n=== 验证原始JSON ===")
    original_data = validate_json_file(notebook_path)
    
    if original_data:
        print("原始JSON已经有效，无需修复")
        return
    
    # 尝试修复
    print("\n=== 尝试修复JSON ===")
    
    # 第一轮修复：常见问题
    fixed_content = fix_common_json_issues(original_content)
    
    # 验证修复后的内容
    try:
        data = json.loads(fixed_content)
        print("✓ 第一轮修复成功")
    except json.JSONDecodeError as e:
        print(f"✗ 第一轮修复失败: {e}")
        
        # 第二轮修复：针对特定位置
        fixed_content = fix_specific_position(fixed_content, e.lineno, e.colno)
        
        try:
            data = json.loads(fixed_content)
            print("✓ 第二轮修复成功")
        except json.JSONDecodeError as e2:
            print(f"✗ 第二轮修复失败: {e2}")
            
            # 第三轮修复：手动修复
            fixed_content = manual_fix_based_on_content(fixed_content)
            
            try:
                data = json.loads(fixed_content)
                print("✓ 第三轮修复成功")
            except json.JSONDecodeError as e3:
                print(f"✗ 所有修复尝试都失败: {e3}")
                print("尝试使用jq工具修复...")
                
                # 尝试使用jq（如果可用）
                import subprocess
                try:
                    result = subprocess.run(
                        ['jq', '.', str(notebook_path)],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    fixed_content = result.stdout
                    print("✓ 使用jq修复成功")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("✗ jq不可用或修复失败")
                    print("请手动检查文件内容")
                    return
    
    # 保存修复后的文件
    with open(notebook_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"\n✓ 已保存修复后的文件: {notebook_path}")
    
    # 最终验证
    print("\n=== 最终验证 ===")
    final_data = validate_json_file(notebook_path)
    
    if final_data:
        print("✓ 文件修复成功，可以在VS Code中打开了")
    else:
        print("✗ 文件修复失败，可能需要手动修复")

if __name__ == "__main__":
    main()