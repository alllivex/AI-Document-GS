#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复第147行特定的JSON语法错误"""

import json
import sys
from pathlib import Path

def fix_specific_line():
    """修复第147行未转义的双引号"""
    notebook_path = Path("word_gen_system_demo_with_marking.ipynb")
    
    if not notebook_path.exists():
        print("错误: 文件不存在:", notebook_path)
        return False
    
    # 读取文件内容
    with open(notebook_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 创建备份
    backup_path = notebook_path.with_suffix('.ipynb.before_fix')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("创建备份:", backup_path)
    
    # 检查第147行（索引146）
    if 146 >= len(lines):
        print("错误: 文件没有147行")
        return False
    
    original_line = lines[146]
    print("原始第147行:", repr(original_line))
    
    # 分析问题：字符串中有未转义的双引号
    # 原始内容: "# 业务数据，放到 data/，模拟"数据准备文件夹"\n"
    # 问题在: 模拟"数据准备文件夹" 中的双引号
    
    # 修复：将未转义的双引号转义
    # 查找模式：在字符串中找到 "数据准备文件夹" 这样的模式
    # 我们需要找到 "模拟"数据准备文件夹"" 并修复为 "模拟\"数据准备文件夹\""
    
    # 更简单的方法：直接修复整个字符串
    if '"# 业务数据，放到 data/，模拟"数据准备文件夹"' in original_line:
        # 修复未转义的双引号
        fixed_line = original_line.replace('模拟"数据准备文件夹"', '模拟\\"数据准备文件夹\\"')
        print("修复后的行:", repr(fixed_line))
        
        # 更新行
        lines[146] = fixed_line
        
        # 重新组合内容
        fixed_content = ''.join(lines)
        
        # 测试修复
        try:
            data = json.loads(fixed_content)
            print("JSON解析成功！")
            
            # 保存修复后的文件
            with open(notebook_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print("已保存修复后的文件")
            return True
            
        except json.JSONDecodeError as e:
            print("修复后仍然失败:", e)
            print("位置: 第", e.lineno, "行, 第", e.colno, "列")
            
            # 尝试另一种修复：在整个文件中修复所有未转义的双引号
            print("尝试更全面的修复...")
            
            # 重新读取原始内容
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复Python代码字符串中的未转义双引号
            # 使用状态机方法
            lines = content.split('\n')
            in_string = False
            escape_next = False
            
            for i in range(len(lines)):
                line = lines[i]
                new_chars = []
                j = 0
                
                while j < len(line):
                    char = line[j]
                    
                    if escape_next:
                        new_chars.append(char)
                        escape_next = False
                        j += 1
                    elif char == '\\':
                        new_chars.append(char)
                        escape_next = True
                        j += 1
                    elif char == '"':
                        new_chars.append(char)
                        in_string = not in_string
                        j += 1
                    elif in_string and char == '"':
                        # 在字符串内部遇到双引号，需要转义
                        new_chars.append('\\"')
                        j += 1
                    else:
                        new_chars.append(char)
                        j += 1
                
                lines[i] = ''.join(new_chars)
            
            fixed_content = '\n'.join(lines)
            
            # 测试
            try:
                data = json.loads(fixed_content)
                print("全面修复成功！")
                
                with open(notebook_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                return True
                
            except json.JSONDecodeError as e2:
                print("全面修复也失败:", e2)
                return False
    
    else:
        print("未找到预期的字符串模式")
        return False

def main():
    """主函数"""
    print("开始修复JSON文件...")
    
    success = fix_specific_line()
    
    if success:
        print("修复完成！")
        print("现在可以尝试在VS Code中打开文件了。")
        
        # 验证修复
        try:
            with open("word_gen_system_demo_with_marking.ipynb", 'r', encoding='utf-8') as f:
                json.load(f)
            print("验证通过：文件现在包含有效的JSON。")
        except Exception as e:
            print("验证警告:", e)
        
        return 0
    else:
        print("修复失败。")
        print("备份文件已保存为：word_gen_system_demo_with_marking.ipynb.before_fix")
        return 1

if __name__ == "__main__":
    sys.exit(main())