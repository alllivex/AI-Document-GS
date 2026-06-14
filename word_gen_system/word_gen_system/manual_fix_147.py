#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手动修复第147行JSON语法错误"""

import json
import sys
from pathlib import Path

def manual_fix():
    """手动修复第147行"""
    notebook_path = Path("word_gen_system_demo_with_marking.ipynb")
    
    if not notebook_path.exists():
        print("错误: 文件不存在:", notebook_path)
        return False
    
    # 读取文件内容
    with open(notebook_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 创建备份
    backup_path = notebook_path.with_suffix('.ipynb.backup147')
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
        
        # 分割为行
        lines = content.split('\n')
        
        # 检查第147行（索引146）
        if 146 < len(lines):
            line_147 = lines[146]
            print("\n=== 第147行分析 ===")
            print("原始行:", repr(line_147))
            print("长度:", len(line_147))
            
            # 检查第25列（索引24）
            if len(line_147) >= 25:
                col_25 = line_147[24]
                print("第25列字符:", repr(col_25))
                print("ASCII码:", ord(col_25))
                
                # 查看上下文
                start = max(0, 24 - 10)
                end = min(len(line_147), 24 + 10)
                context = line_147[start:end]
                print("上下文:", context)
                print("      ", " " * (24 - start) + "^")
                
                # 查看前后字符
                if 24 > 0:
                    print("前一个字符:", repr(line_147[23]))
                if 25 < len(line_147):
                    print("后一个字符:", repr(line_147[25]))
            
            # 分析可能的修复
            print("\n=== 尝试修复 ===")
            
            # 根据错误信息"Expecting ',' delimiter"，可能缺少逗号
            # 检查第147行的上下文
            print("第146行:", repr(lines[145]) if 145 < len(lines) else "N/A")
            print("第147行:", repr(line_147))
            print("第148行:", repr(lines[147]) if 147 < len(lines) else "N/A")
            
            # 查看第147行在文件中的完整上下文
            print("\n=== 完整上下文（第140-155行） ===")
            for i in range(139, 155):
                if i < len(lines):
                    marker = ">>>" if i == 146 else "   "
                    print(f"{marker} {i+1:4}: {lines[i][:100]}")
        
        # 基于notebook内容分析，第147行可能在Cell 8.1的Python代码字符串中
        # 错误可能是Python字符串中的未转义引号
        
        # 尝试修复：在Python代码字符串中修复未转义的引号
        print("\n=== 尝试修复Python代码字符串 ===")
        
        # 查找所有代码单元格
        lines = content.split('\n')
        in_code_cell = False
        in_source_array = False
        source_lines = []
        
        for i, line in enumerate(lines):
            # 检查是否进入代码单元格
            if '"cell_type": "code"' in line:
                in_code_cell = True
                continue
            
            # 检查是否进入源代码数组
            if in_code_cell and '"source": [' in line:
                in_source_array = True
                continue
            
            # 检查是否退出源代码数组
            if in_source_array and line.strip() == ']':
                in_source_array = False
                in_code_cell = False
                
                # 处理收集的源代码行
                for src_idx in source_lines:
                    src_line = lines[src_idx]
                    
                    # 检查是否是源代码字符串行
                    if src_line.strip().startswith('"') and src_line.strip().endswith('",'):
                        # 提取字符串内容
                        str_content = src_line.strip()[1:-2]
                        
                        # 检查是否有未转义的双引号
                        # 简单的检查：统计引号数量
                        quotes = str_content.count('"')
                        escaped_quotes = str_content.count('\\"')
                        unescaped_quotes = quotes - escaped_quotes
                        
                        if unescaped_quotes > 0:
                            print(f"第{src_idx+1}行有{unescaped_quotes}个未转义引号")
                            
                            # 修复未转义的引号
                            fixed_str = ""
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
                            lines[src_idx] = '    "' + fixed_str + '",'
                            print(f"  已修复第{src_idx+1}行")
                
                source_lines = []
                continue
            
            # 收集源代码数组中的行
            if in_source_array:
                if line.strip().startswith('"'):
                    source_lines.append(i)
        
        # 重新组合内容
        fixed_content = '\n'.join(lines)
        
        # 测试修复
        try:
            data = json.loads(fixed_content)
            print("\n✓ 修复成功！")
            
            # 保存修复后的文件
            with open(notebook_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print("已保存修复后的文件")
            
            # 验证修复
            try:
                with open(notebook_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                print("验证通过：文件现在包含有效的JSON。")
            except Exception as e:
                print("验证警告:", e)
            
            return True
            
        except json.JSONDecodeError as e2:
            print("\n✗ 修复失败，新错误:", e2)
            print("位置: 第", e2.lineno, "行, 第", e2.colno, "列")
            
            # 显示新错误位置
            new_lines = fixed_content.split('\n')
            if e2.lineno - 1 < len(new_lines):
                error_line = new_lines[e2.lineno - 1]
                print("新错误行:", repr(error_line[:100]))
            
            return False
    
    return False

def main():
    """主函数"""
    print("开始手动修复JSON文件...")
    
    success = manual_fix()
    
    if success:
        print("\n✓ 修复完成！")
        print("现在可以尝试在VS Code中打开文件了。")
        return 0
    else:
        print("\n✗ 修复失败。")
        print("可能需要手动编辑文件。")
        print("备份文件已保存为：word_gen_system_demo_with_marking.ipynb.backup147")
        return 1

if __name__ == "__main__":
    sys.exit(main())