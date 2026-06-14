"""
条件表达式追踪模块

此模块提供通用功能来：
1. 从Word模板中提取Jinja2条件表达式
2. 计算表达式结果并添加到trace映射
3. 支持任意条件表达式（比较、逻辑运算、成员测试等）
"""
import re
from typing import List, Tuple, Dict, Any
from pathlib import Path
import zipfile
from lxml import etree

# Jinja2条件表达式模式
CONDITION_PATTERN = r'\{%\s*if\s+(.+?)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}'
# 简化模式，匹配{% if ... %}...{% endif %} 可能包含{% else %}
CONDITION_SIMPLE_PATTERN = r'\{%\s*if\s+(.+?)\s*%\}(.*?)(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}'

def extract_condition_expressions_from_docx(template_path: Path) -> List[Tuple[str, str, str]]:
    """
    从Word模板中提取所有条件表达式。
    
    返回: [(condition_expr, true_text, false_text), ...]
    """
    expressions = []
    
    try:
        # 读取Word文档的document.xml
        with zipfile.ZipFile(template_path, 'r') as z:
            xml_content = z.read('word/document.xml').decode('utf-8')
        
        # 简化：查找所有段落文本中的条件表达式
        # 使用更灵活的正则匹配
        pattern = r'\{%\s*if\s+(.+?)\s*%\}(.*?)(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}'
        
        for match in re.finditer(pattern, xml_content, re.DOTALL):
            condition = match.group(1).strip()
            true_text = match.group(2).strip() if match.group(2) else ""
            false_text = match.group(3).strip() if match.group(3) else ""
            
            # 清理文本中的XML标签和多余空白
            true_text = re.sub(r'<[^>]+>', '', true_text)
            false_text = re.sub(r'<[^>]+>', '', false_text)
            true_text = ' '.join(true_text.split())
            false_text = ' '.join(false_text.split())
            
            expressions.append((condition, true_text, false_text))
            
    except Exception as e:
        print(f"警告: 提取条件表达式时出错: {e}")
    
    return expressions


def extract_condition_expressions_from_text(template_text: str) -> List[Tuple[str, str, str]]:
    """
    从文本中提取所有条件表达式。
    
    返回: [(condition_expr, true_text, false_text), ...]
    """
    expressions = []
    
    try:
        # 匹配 {% if ... %}...{% else %}...{% endif %} 结构
        pattern = r'\{%\s*if\s+(.+?)\s*%\}(.*?)(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}'
        
        for match in re.finditer(pattern, template_text, re.DOTALL):
            condition = match.group(1).strip()
            true_text = match.group(2).strip() if match.group(2) else ""
            false_text = match.group(3).strip() if match.group(3) else ""
            
            # 清理文本
            true_text = ' '.join(true_text.split())
            false_text = ' '.join(false_text.split())
            
            expressions.append((condition, true_text, false_text))
            
    except Exception as e:
        print(f"警告: 提取条件表达式时出错: {e}")
    
    return expressions


def evaluate_condition_expression(expression: str, context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    安全地计算条件表达式的结果。
    
    返回: (结果, 表达式解析信息字典)
    """
    try:
        # 简单解析表达式，提取变量和操作符
        # 这里我们实现一个简单的求值器，支持常见的比较和逻辑运算
        
        # 保存原始表达式
        expr_info = {
            'expression': expression,
            'variables': [],
            'operators': [],
            'raw_result': None,
            'error': None
        }
        
        # 提取变量名（简单的正则匹配）
        variable_pattern = r'[a-zA-Z_][a-zA-Z0-9_.]*'
        variables = re.findall(variable_pattern, expression)
        expr_info['variables'] = list(set(variables))
        
        # 创建安全的求值环境
        safe_globals = {
            '__builtins__': {},
            'True': True,
            'False': False,
            'None': None,
            'abs': abs,
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'len': len,
            'sum': sum,
            'min': min,
            'max': max,
            'round': round,
        }
        
        # 创建一个访问器函数来安全地获取嵌套值
        def get_nested_value(obj, path):
            """安全地获取嵌套字典/列表中的值"""
            parts = path.split('.')
            value = obj
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
                    value = value[int(part)]
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value
        
        # 准备求值环境
        safe_locals = {'context': context, 'get_nested_value': get_nested_value}
        
        # 为表达式中的每个变量创建访问器
        for var_name in variables:
            if '.' in var_name:
                # 为嵌套变量创建访问器
                parts = var_name.split('.')
                value = get_nested_value(context, var_name)
                safe_locals[var_name] = value
            elif var_name in context:
                safe_locals[var_name] = context[var_name]
            else:
                safe_locals[var_name] = None
        
        # 尝试直接求值
        try:
            # 先尝试直接求值
            result = eval(expression, safe_globals, safe_locals)
            expr_info['raw_result'] = result
            return bool(result), expr_info
        except Exception as e:
            expr_info['error'] = str(e)
            
            # 如果直接求值失败，尝试替换表达式中的变量
            # 将表达式中的变量替换为它们的值
            expr_for_eval = expression
            for var_name in variables:
                if var_name in safe_locals and safe_locals[var_name] is not None:
                    # 将变量替换为其值
                    value = safe_locals[var_name]
                    if isinstance(value, str):
                        # 字符串需要加引号
                        replacement = repr(value)
                    else:
                        replacement = str(value)
                    expr_for_eval = expr_for_eval.replace(var_name, replacement)
            
            # 尝试求值替换后的表达式
            try:
                result = eval(expr_for_eval, safe_globals, {})
                expr_info['raw_result'] = result
                expr_info['evaluated_expression'] = expr_for_eval
                return bool(result), expr_info
            except Exception as e2:
                expr_info['error'] = f"原始错误: {e}, 替换后错误: {e2}"
            
            # 如果eval失败，尝试简单的比较解析
            # 解析常见的比较操作
            comparison_patterns = [
                (r'(.+?)\s*<\s*(.+)', 'lt'),
                (r'(.+?)\s*<=\s*(.+)', 'le'),
                (r'(.+?)\s*>\s*(.+)', 'gt'),
                (r'(.+?)\s*>=\s*(.+)', 'ge'),
                (r'(.+?)\s*==\s*(.+)', 'eq'),
                (r'(.+?)\s*!=\s*(.+)', 'ne'),
                (r'(.+?)\s+in\s+(.+)', 'in'),
                (r'(.+?)\s+not\s+in\s+(.+)', 'not_in'),
            ]
            
            for pattern, op_type in comparison_patterns:
                match = re.match(pattern, expression.strip())
                if match:
                    left, right = match.group(1), match.group(2)
                    # 简单的数值比较处理
                    try:
                        # 尝试将左右两边解析为数值或变量
                        left_val = eval(left.strip(), safe_globals, safe_locals) if '.' in left.strip() or left.strip() in safe_locals else float(left.strip())
                        right_val = eval(right.strip(), safe_globals, safe_locals) if '.' in right.strip() or right.strip() in safe_locals else float(right.strip())
                        
                        if op_type == 'lt':
                            result = left_val < right_val
                        elif op_type == 'le':
                            result = left_val <= right_val
                        elif op_type == 'gt':
                            result = left_val > right_val
                        elif op_type == 'ge':
                            result = left_val >= right_val
                        elif op_type == 'eq':
                            result = left_val == right_val
                        elif op_type == 'ne':
                            result = left_val != right_val
                        elif op_type == 'in':
                            result = left_val in right_val
                        elif op_type == 'not_in':
                            result = left_val not in right_val
                        else:
                            result = False
                        
                        expr_info['raw_result'] = result
                        expr_info['parsed'] = {
                            'left': left,
                            'right': right,
                            'operator': op_type,
                            'left_value': left_val,
                            'right_value': right_val
                        }
                        return bool(result), expr_info
                    except:
                        continue
            
            # 如果所有方法都失败，返回False
            return False, expr_info
            
    except Exception as e:
        print(f"警告: 计算条件表达式 '{expression}' 时出错: {e}")
        return False, {'expression': expression, 'error': str(e)}


from typing import Any, Dict, List, Tuple, Optional

def create_trace_item_from_condition(
    condition: str,
    result: bool,
    display_text: str,
    expr_info: Dict[str, Any],
    pk_val: Any,
    true_text: str,
    false_text: str
) -> Dict[str, Any]:
    """
    从条件表达式创建TraceItem兼容的溯源项字典。
    返回的字典具有与TraceItem相同的字段，外加额外的条件信息。
    """
    return {
        'var': f'条件表达式: {condition}',
        'table': '__condition__',
        'field': condition,
        'value': display_text,
        'pk': pk_val,
        'row_index': None,
        'source_file': 'template_condition',
        # 额外字段用于条件表达式
        '_condition_result': result,
        '_expression_info': expr_info,
        '_true_text': true_text,
        '_false_text': false_text,
        '_is_condition': True  # 标记这是一个条件表达式项
    }


def add_condition_traces(
    context: Dict[str, Any],
    trace_map: Dict[str, Any],
    pk_val: Any,
    template_path: Path = None,
    template_text: str = None
) -> None:
    """
    为模板中的条件表达式添加溯源项。
    
    参数:
        context: 渲染上下文
        trace_map: 当前的trace映射（将接受TraceItem或ConditionTraceItem）
        pk_val: 主键值
        template_path: Word模板路径
        template_text: 模板文本（如果template_path未提供）
    """
    # 提取条件表达式
    expressions = []
    if template_path and template_path.exists():
        expressions = extract_condition_expressions_from_docx(template_path)
    elif template_text:
        expressions = extract_condition_expressions_from_text(template_text)
    else:
        # 如果没有模板信息，尝试从上下文推断常见表达式
        expressions = [
            ('loan_summary.house_eval_amount < loan_summary.loan_balance', '无法清偿', '可清偿')
        ]
    
    # 计算每个表达式并添加到trace
    for condition, true_text, false_text in expressions:
        result, expr_info = evaluate_condition_expression(condition, context)
        
        # 确定显示的文本
        display_text = true_text if result else false_text
        
        if display_text:
            # 创建ConditionTraceItem
            trace_item = create_trace_item_from_condition(
                condition=condition,
                result=result,
                display_text=display_text,
                expr_info=expr_info,
                pk_val=pk_val,
                true_text=true_text,
                false_text=false_text
            )
            
            # 添加到trace映射
            trace_key = f'__condition__.{hash(condition) & 0xFFFFFFFF}'
            trace_map[trace_key] = trace_item
            
            # 同时为显示文本创建标准TraceItem兼容项（用于批注匹配）
            # 使用与现有系统兼容的键名
            literal_key = f'__literal__.{hash(display_text) & 0xFFFFFFFF}'
            # 创建简化版本，只包含value用于文本匹配
            trace_map[literal_key] = trace_item
