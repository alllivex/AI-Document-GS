#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接修复JSON语法错误 - 不输出Unicode字符"""

import json
import sys
from pathlib import Path

def fix_json_direct():
    """直接修复JSON文件"""
    notebook_path = Path("word_gen_system_demo_with_marking.ipynb")
    
    if not notebook_path.exists():
        print("错误: 文件不存在:", notebook_path)
        return False
    
    # 读取文件内容
    with open(notebook_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 创建备份
    backup_path = notebook_path.with_suffix('.ipynb.backup2')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("创建备份:", backup_path)
    
    # 尝试解析JSON
    try:
        data = json.loads(content)
        print("JSON已有效，无需修复")
        return True
    except json.JSONDecodeError as e:
        print("JSON解析错误:", e)
        print("位置: 第", e.lineno, "行, 第", e.colno, "列")
        
        # 直接修复第147行第25列的问题
        lines = content.split('\n')
        if e.lineno <= len(lines):
            line_index = e.lineno - 1
            line = lines[line_index]
            
            print("修复第", e.lineno, "行")
            print("原始行:", line[:100])
            
            # 检查第25列附近的字符
            if e.colno <= len(line):
                char_pos = e.colno - 1
                print("第", e.colno, "列字符:", repr(line[char_pos]))
                
                # 查看附近上下文
                start = max(0, char_pos - 10)
                end = min(len(line), char_pos + 10)
                context = line[start:end]
                print("上下文:", context)
                
                # 常见的JSON错误模式：
                # 1. 缺少逗号: "value1" "value2" 应该为 "value1", "value2"
                # 2. 多余逗号: "value",} 应该为 "value"}
                # 3. 未转义引号: "text with "quotes"" 应该为 "text with \"quotes\""
                
                # 检查是否缺少逗号
                # 查找模式: 引号后直接跟引号
                if char_pos > 0 and char_pos < len(line):
                    # 检查错误位置周围的字符模式
                    if line[char_pos] == '"':
                        # 可能是缺少逗号或未转义引号
                        # 向前查找前一个非空白字符
                        i = char_pos - 1
                        while i >= 0 and line[i] in ' \t':
                            i -= 1
                        
                        if i >= 0 and line[i] == '"':
                            # 两个引号之间没有逗号，需要添加逗号
                            # 在第一个引号后插入逗号
                            # 但需要确定在哪里插入
                            
                            # 更好的方法：检查错误位置前后的完整上下文
                            # 让我们检查第147行的完整内容
                            print("\n完整第147行分析:")
                            print("行内容:", repr(line))
                            
                            # 根据读取的文件，第147行看起来可能是：
                            # 从之前看到的notebook内容，第147行可能在Cell 8.1的Python代码字符串中
                            # 错误可能是Python字符串中的未转义引号
                            
                            # 使用更简单的修复：在整个文件中查找常见问题
                            # 修复未转义的引号在Python代码字符串中
                            
                            pass
            
            # 直接修复：在整个内容中修复常见问题
            # 1. 修复Python代码字符串中的未转义双引号
            # 在源代码字符串中查找模式： text"text
            # 但需要在转义序列中避免
            
            print("\n尝试自动修复...")
            
            # 方法：重建JSON，使用json.tool格式化
            try:
                # 使用json.loads的object_hook来修复
                # 但更简单：使用json.dumps和json.loads重新格式化
                temp_data = json.loads(content, strict=False)
                fixed_content = json.dumps(temp_data, indent=2, ensure_ascii=False)
                
                # 保存修复后的文件
                with open(notebook_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print("修复成功（使用宽松模式解析）")
                return True
                
            except:
                # 如果宽松模式也失败，尝试手动修复
                print("宽松模式失败，尝试手动修复...")
                
                # 手动修复：在第147行第25列插入逗号
                # 这只是一个猜测，需要更多上下文
                
                # 更安全的方法：提取错误部分并尝试修复
                char_index = 0
                for i in range(e.lineno - 1):
                    char_index += len(lines[i]) + 1  # +1 for newline
                
                char_index += e.colno - 1
                
                # 在错误位置插入逗号
                if char_index < len(content):
                    fixed_content = content[:char_index] + ',' + content[char_index:]
                    
                    # 测试修复
                    try:
                        json.loads(fixed_content)
                        print("在位置插入逗号成功")
                        with open(notebook_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        return True
                    except json.JSONDecodeError as e2:
                        print("插入逗号后仍然失败:", e2)
                        
                        # 尝试不同的修复：在错误位置插入转义字符
                        if content[char_index] == '"':
                            fixed_content = content[:char_index] + '\\' + content[char_index:]
                            try:
                                json.loads(fixed_content)
                                print("插入转义字符成功")
                                with open(notebook_path, 'w', encoding='utf-8') as f:
                                    f.write(fixed_content)
                                return True
                            except:
                                print("所有自动修复尝试都失败")
                                return False
    
    return False

def main():
    """主函数"""
    print("开始修复JSON文件...")
    
    success = fix_json_direct()
    
    if success:
        print("\n修复完成！")
        print("现在可以尝试在VS Code中打开文件了。")
        return 0
    else:
        print("\n修复失败。")
        print("建议手动查看第147行附近的JSON语法。")
        print("常见问题：")
        print("1. 缺少逗号分隔数组元素或对象属性")
        print("2. 字符串中的未转义双引号")
        print("3. 多余逗号")
        return 1

if __name__ == "__main__":
    sys.exit(main())