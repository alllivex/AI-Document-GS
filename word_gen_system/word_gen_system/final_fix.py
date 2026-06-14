#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终修复JSON语法错误"""

import json
import sys
import re
from pathlib import Path

def fix_json_final():
    """修复JSON文件中的语法错误"""
    notebook_path = Path("word_gen_system_demo_with_marking.ipynb")
    
    if not notebook_path.exists():
        print("错误: 文件不存在:", notebook_path)
        return False
    
    # 读取文件内容
    with open(notebook_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 创建备份
    backup_path = notebook_path.with_suffix('.ipynb.original')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("创建备份:", backup_path)
    
    # 先尝试解析
    try:
        data = json.loads(content)
        print("JSON已有效，无需修复")
        return True
    except json.JSONDecodeError as e:
        print("JSON解析错误:", e)
        print("位置: 第", e.lineno, "行, 第", e.colno, "列")
        
        # 显示错误位置
        lines = content.split('\n')
        line_idx = e.lineno - 1
        
        if line_idx < len(lines):
            error_line = lines[line_idx]
            print("错误行内容:", repr(error_line))
            
            # 检查第147行第25列的具体字符
            if e.colno <= len(error_line):
                char_idx = e.colno - 1
                print("第", e.colno, "列字符:", repr(error_line[char_idx]))
                
                # 查看上下文
                start = max(0, char_idx - 15)
                end = min(len(error_line), char_idx + 15)
                print("上下文:", error_line[start:end])
        
        # 修复策略：处理Python代码字符串中的常见问题
        print("\n开始修复...")
        
        # 方法1：修复字符串中的未转义控制字符
        fixed_content = content
        
        # 替换控制字符
        control_char_map = {
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '\b': '\\b',
            '\f': '\\f',
            '\\': '\\\\',
            '"': '\\"'
        }
        
        # 但我们需要小心，只替换字符串内部的字符，而不是JSON语法字符
        # 使用状态机方法
        lines = fixed_content.split('\n')
        in_string = False
        escape_next = False
        in_code_cell_string = False
        
        for i in range(len(lines)):
            line = lines[i]
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
                    new_line_chars.append(char)
                    in_string = not in_string
                    j += 1
                elif in_string:
                    # 在字符串内部
                    if char == '\n':
                        # 字符串中的换行符，需要转义
                        new_line_chars.append('\\n')
                    elif char == '\r':
                        # 字符串中的回车符，需要转义
                        new_line_chars.append('\\r')
                    elif char == '\t':
                        # 字符串中的制表符，需要转义
                        new_line_chars.append('\\t')
                    elif char == '"':
                        # 字符串中的双引号，需要转义
                        new_line_chars.append('\\"')
                    elif char == '\\':
                        # 字符串中的反斜杠，需要转义
                        new_line_chars.append('\\\\')
                    else:
                        new_line_chars.append(char)
                    j += 1
                else:
                    # 不在字符串内部
                    new_line_chars.append(char)
                    j += 1
            
            lines[i] = ''.join(new_line_chars)
        
        fixed_content = '\n'.join(lines)
        
        # 方法2：修复常见的JSON语法错误
        # 修复模式1：缺少逗号，当 } 后面跟着 {
        fixed_content = re.sub(r'\}\s*\{', '}, {', fixed_content)
        
        # 修复模式2：缺少逗号，当 ] 后面跟着 {
        fixed_content = re.sub(r'\]\s*\{', '], {', fixed_content)
        
        # 修复模式3：缺少逗号，当 } 后面跟着 [
        fixed_content = re.sub(r'\}\s*\[', '}, [', fixed_content)
        
        # 修复模式4：缺少逗号，当 ] 后面跟着 [
        fixed_content = re.sub(r'\]\s*\[', '], [', fixed_content)
        
        # 修复模式5：在 ] 或 } 前的多余逗号
        fixed_content = re.sub(r',(\s*[\]}])', r'\1', fixed_content)
        
        # 修复模式6：在数组元素之间缺少逗号
        # 查找模式：值后面直接跟着值
        lines = fixed_content.split('\n')
        for i in range(len(lines)):
            # 简化处理：只在看起来像数组的行中修复
            if '[' in lines[i] and ']' in lines[i]:
                # 修复简单的数组缺少逗号
                line = lines[i]
                # 模式：数字或字符串后直接跟着数字或字符串
                line = re.sub(r'(\d+|"[^"]*")\s+(\d+|"[^"]*")', r'\1, \2', line)
                lines[i] = line
        
        fixed_content = '\n'.join(lines)
        
        # 尝试解析修复后的内容
        try:
            data = json.loads(fixed_content)
            print("\n修复成功！")
            
            # 保存修复后的文件
            with open(notebook_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print("已保存修复后的文件")
            return True
            
        except json.JSONDecodeError as e2:
            print("\n自动修复失败，尝试使用json.tool修复...")
            print("新错误:", e2)
            
            # 使用Python的json.tool格式化
            try:
                import subprocess
                import tempfile
                
                # 写入临时文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                    tmp_path = tmp.name
                    tmp.write(content)
                
                # 使用json.tool格式化
                result = subprocess.run(
                    ['python', '-m', 'json.tool', tmp_path],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    # 格式化成功
                    fixed_content = result.stdout
                    
                    # 保存修复后的文件
                    with open(notebook_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    
                    print("使用json.tool修复成功")
                    return True
                else:
                    print("json.tool失败:", result.stderr)
                    
            except Exception as e3:
                print("json.tool异常:", e3)
            
            # 最后尝试：手动修复第147行
            print("\n尝试手动修复第147行...")
            
            # 重新读取原始内容
            lines = content.split('\n')
            
            if 146 < len(lines):  # 第147行索引是146
                line_147 = lines[146]
                print("原始第147行:", repr(line_147))
                
                # 根据常见错误猜测修复
                # 错误在第25列，可能缺少逗号
                if len(line_147) >= 25:
                    # 在第25列插入逗号
                    fixed_line = line_147[:24] + ',' + line_147[24:]
                    lines[146] = fixed_line
                    print("在第147行第25列插入逗号")
                    
                    fixed_content = '\n'.join(lines)
                    
                    try:
                        data = json.loads(fixed_content)
                        print("手动修复成功！")
                        
                        with open(notebook_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        
                        return True
                    except json.JSONDecodeError as e4:
                        print("手动修复失败:", e4)
            
            return False
    
    return True

def main():
    """主函数"""
    print("开始修复JSON文件...")
    
    success = fix_json_final()
    
    if success:
        print("\n修复完成！")
        print("现在可以尝试在VS Code中打开文件了。")
        
        # 验证修复
        try:
            with open("word_gen_system_demo_with_marking.ipynb", 'r', encoding='utf-8') as f:
                json.load(f)
            print("验证通过：文件现在包含有效的JSON。")
        except Exception as e:
            print("警告：文件可能仍有问题:", e)
        
        return 0
    else:
        print("\n修复失败。")
        print("可能需要手动编辑文件。")
        print("备份文件已保存为：word_gen_system_demo_with_marking.ipynb.original")
        return 1

if __name__ == "__main__":
    sys.exit(main())