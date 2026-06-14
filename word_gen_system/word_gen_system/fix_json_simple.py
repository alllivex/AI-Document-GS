#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单修复JSON语法错误"""

import json
import sys
from pathlib import Path
import re

def fix_json_file(input_path: Path, output_path: Path = None):
    """修复JSON文件中的语法错误"""
    if output_path is None:
        output_path = input_path
    
    print(f"修复文件: {input_path}")
    
    # 读取文件内容
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 备份原文件
    backup_path = input_path.with_suffix('.ipynb.bak')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"创建备份: {backup_path}")
    
    # 尝试解析JSON，如果失败则尝试修复
    try:
        data = json.loads(content)
        print("✓ JSON已有效，无需修复")
        return True
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析错误: {e}")
        print(f"  错误位置: 第{e.lineno}行, 第{e.colno}列")
        
        # 显示错误位置附近的上下文
        lines = content.split('\n')
        start_line = max(0, e.lineno - 3)
        end_line = min(len(lines), e.lineno + 2)
        
        print(f"\n=== 错误位置附近的上下文 ===")
        for i in range(start_line, end_line):
            line_num = i + 1
            marker = ">>>" if line_num == e.lineno else "   "
            print(f"{marker} {line_num:4}: {lines[i]}")
        
        # 尝试修复常见问题
        fixed_content = content
        
        # 问题1: 检查是否缺少逗号
        # 在第147行附近查找问题
        error_line_index = e.lineno - 1
        if error_line_index < len(lines):
            error_line = lines[error_line_index]
            print(f"\n=== 分析第{e.lineno}行 ===")
            print(f"行内容: {repr(error_line)}")
            
            # 检查第25列附近的字符
            if e.colno <= len(error_line):
                char_at_error = error_line[e.colno - 1]
                context_start = max(0, e.colno - 10)
                context_end = min(len(error_line), e.colno + 10)
                context = error_line[context_start:context_end]
                print(f"错误位置字符: '{char_at_error}' (ASCII: {ord(char_at_error) if char_at_error else 'N/A'})")
                print(f"上下文: ...{context}...")
        
        # 修复策略1: 处理常见问题
        # 1. 修复Python代码字符串中的未转义引号
        print("\n=== 尝试修复: Python代码字符串中的未转义引号 ===")
        
        # 查找所有代码单元格
        lines = fixed_content.split('\n')
        in_code_cell = False
        in_string_array = False
        string_lines = []
        
        for i, line in enumerate(lines):
            # 检查是否进入代码单元格
            if '"cell_type": "code"' in line:
                in_code_cell = True
                continue
            
            # 检查是否进入源代码数组
            if in_code_cell and '"source": [' in line:
                in_string_array = True
                continue
            
            # 检查是否退出源代码数组
            if in_string_array and line.strip() == ']':
                in_string_array = False
                # 处理收集的字符串行
                for str_line_idx in string_lines:
                    orig_line = lines[str_line_idx]
                    # 检查行是否包含源代码字符串
                    if orig_line.strip().startswith('"') and orig_line.strip().endswith('",'):
                        # 提取字符串内容
                        str_content = orig_line.strip()[1:-2]  # 移除引号和逗号
                        
                        # 修复未转义的控制字符
                        # 替换换行符、回车符、制表符
                        str_content = str_content.replace('\n', '\\n')
                        str_content = str_content.replace('\r', '\\r')
                        str_content = str_content.replace('\t', '\\t')
                        
                        # 修复未转义的双引号（不在转义序列中的）
                        fixed_str = ''
                        j = 0
                        while j < len(str_content):
                            if str_content[j] == '\\' and j + 1 < len(str_content):
                                # 转义序列
                                fixed_str += str_content[j:j+2]
                                j += 2
                            elif str_content[j] == '"':
                                # 未转义的双引号，需要转义
                                fixed_str += '\\"'
                                j += 1
                            else:
                                fixed_str += str_content[j]
                                j += 1
                        
                        # 更新行
                        lines[str_line_idx] = '    "' + fixed_str + '",'
                        print(f"  修复第{str_line_idx+1}行中的字符串")
                
                string_lines = []
                in_code_cell = False
                continue
            
            # 收集源代码数组中的字符串行
            if in_string_array:
                if line.strip().startswith('"'):
                    string_lines.append(i)
        
        fixed_content = '\n'.join(lines)
        
        # 修复策略2: 移除对象末尾的多余逗号
        print("\n=== 尝试修复: 移除对象末尾的多余逗号 ===")
        # 匹配模式: }, 或 ], 后跟 } 或 ]
        fixed_content = re.sub(r',(\s*[}\]])', r'\1', fixed_content)
        
        # 修复策略3: 修复数组中的缺失逗号
        print("\n=== 尝试修复: 数组中的缺失逗号 ===")
        lines = fixed_content.split('\n')
        for i in range(len(lines) - 1):
            # 检查行是否以值结束但没有逗号，下一行以值开始
            line1 = lines[i].rstrip()
            line2 = lines[i + 1].rstrip()
            
            # 简单模式: 行以引号结束，下一行以引号开始
            if line1 and line2:
                if (line1.endswith('"') and not line1.endswith('",') and 
                    line2.startswith('"') and not line2.startswith('","')):
                    # 在第1行添加逗号
                    lines[i] = line1 + ','
                    print(f"  在第{i+1}行添加逗号")
        
        fixed_content = '\n'.join(lines)
        
        # 尝试解析修复后的内容
        try:
            data = json.loads(fixed_content)
            print("\n✓ 修复成功，JSON现在有效")
            
            # 保存修复后的文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✓ 已保存修复后的文件: {output_path}")
            
            # 验证修复后的文件
            with open(output_path, 'r', encoding='utf-8') as f:
                json.load(f)
            print("✓ 修复后的文件验证通过")
            
            return True
            
        except json.JSONDecodeError as e2:
            print(f"\n✗ 修复失败，新的错误: {e2}")
            print(f"  新错误位置: 第{e2.lineno}行, 第{e2.colno}列")
            
            # 显示新错误位置
            lines = fixed_content.split('\n')
            start_line = max(0, e2.lineno - 3)
            end_line = min(len(lines), e2.lineno + 2)
            
            print(f"\n=== 新错误位置附近的上下文 ===")
            for i in range(start_line, end_line):
                line_num = i + 1
                marker = ">>>" if line_num == e2.lineno else "   "
                print(f"{marker} {line_num:4}: {lines[i]}")
            
            return False

def main():
    """主函数"""
    notebook_path = Path("word_gen_system_demo_with_marking.ipynb")
    
    if not notebook_path.exists():
        print(f"错误: 文件不存在: {notebook_path}")
        return 1
    
    success = fix_json_file(notebook_path)
    
    if success:
        print("\n✓ 文件修复完成！")
        print("现在可以尝试在VS Code中打开文件了。")
        return 0
    else:
        print("\n✗ 修复失败，可能需要手动修复。")
        print("建议:")
        print("1. 检查备份文件: word_gen_system_demo_with_marking.ipynb.bak")
        print("2. 手动查看第147行附近的语法错误")
        print("3. 常见问题: 缺少逗号、未转义的引号、多余逗号等")
        return 1

if __name__ == "__main__":
    sys.exit(main())