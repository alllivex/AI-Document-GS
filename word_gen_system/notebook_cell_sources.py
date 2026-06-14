# -*- coding: utf-8 -*-
"""Notebook 中 Cell 8/10/11/12/13 的完整源码字符串（由 _patch_nb.py 写入 ipynb）"""

CELL8 = r'''# Cell 8: 构建上下文（按主表主键：多行批量 / 单行单份）+ TraceMap + 条件表达式追踪
from dataclasses import dataclass
from typing import Optional, Any, Dict, List, Tuple
from datetime import date, datetime
import re
from pathlib import Path
import zipfile
from lxml import etree

@dataclass
class TraceItem:
    """
    数据来源追溯项（用于审阅批注）。

    Attributes:
        var: 模板侧变量路径，如 data.branch_name、products.0.product_name
        table: Excel 实体表名
        field: 字段名
        value: 原始值
        pk: 当前报告实例主键值
        row_index: 数据行索引（可选）
        source_file: 数据文件名（可选）
    """
    var: str
    table: str
    field: str
    value: Any
    pk: Any
    row_index: Optional[int] = None
    source_file: Optional[str] = None


def format_display_value(v: Any) -> str:
    """格式化为 Word 中常见的纯文本，便于与 w:t 精确匹配。"""
    if v is None:
        return ''
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(v, date):
        return v.strftime('%Y-%m-%d')
    if isinstance(v, bool):
        return 'True' if v else 'False'
    if isinstance(v, float):
        if abs(v - round(v, 1)) < 1e-9:
            s = str(round(v, 1))
            return s[:-2] if s.endswith('.0') else s
        if abs(v - int(v)) < 1e-9:
            return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v).strip()


def get_primary_key_field(schema_df: pd.DataFrame, table_name: str) -> str:
    sub = schema_df[(schema_df['table_name'] == table_name) & (schema_df['is_primary_key'] == 1)]
    if sub.empty:
        raise ValueError(f'表 {table_name} 未配置主键字段')
    if len(sub) != 1:
        raise ValueError(f"表 {table_name} 暂仅支持单主键，当前: {sub['field_name'].tolist()}")
    return sub['field_name'].iloc[0]


# ========== 条件表达式追踪功能（原本在 condition_tracker.py）==========
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
        
        # 查找所有段落文本中的条件表达式
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
        expr_info = {
            'expression': expression,
            'variables': [],
            'operators': [],
            'raw_result': None,
            'error': None
        }
        
        # 提取变量名
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
            result = eval(expression, safe_globals, safe_locals)
            expr_info['raw_result'] = result
            return bool(result), expr_info
        except Exception as e:
            expr_info['error'] = str(e)
            
            # 如果直接求值失败，尝试替换表达式中的变量
            expr_for_eval = expression
            for var_name in variables:
                if var_name in safe_locals and safe_locals[var_name] is not None:
                    value = safe_locals[var_name]
                    if isinstance(value, str):
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
                    try:
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
            literal_key = f'__literal__.{hash(display_text) & 0xFFFFFFFF}'
            trace_map[literal_key] = trace_item


def build_report_contexts(
    schema_df: pd.DataFrame,
    tables: Dict[str, pd.DataFrame],
    main_table: str,
    alias_map: Dict[str, str] | None = None,
    template_path: Path | None = None,
    template_text: str | None = None,
) -> List[Tuple[dict, Dict[str, Any]]]:
    """
    按主表主键逐行生成报告；主表一行则仅一份。
    辅表：与主键同名列则过滤；单行 dict，多行 list；Trace 含 products.i.field。
    
    新增参数:
        template_path: Word模板路径（用于提取条件表达式）
        template_text: 模板文本（如果template_path未提供）
    """
    if alias_map is None:
        alias_map = {t: t for t in tables.keys()}

    pk_field = get_primary_key_field(schema_df, main_table)
    if pk_field not in tables[main_table].columns:
        raise ValueError(f'主表 {main_table} 缺少主键列 {pk_field}')

    out: List[Tuple[dict, Dict[str, Any]]] = []
    for idx, row in tables[main_table].iterrows():
        pk_val = row[pk_field]
        context: dict = {}
        trace: Dict[str, Any] = {}

        context['data'] = row.to_dict()
        for k, v in row.to_dict().items():
            var = f'data.{k}'
            trace[var] = TraceItem(
                var=var, table=main_table, field=k, value=v, pk=pk_val,
                row_index=int(idx), source_file=f'{main_table}.xlsx',
            )

        for tname, df in tables.items():
            if tname == main_table:
                continue
            alias = alias_map.get(tname, tname)
            sub = df[df[pk_field] == pk_val] if pk_field in df.columns else df

            if len(sub) == 1:
                obj = sub.iloc[0].to_dict()
                context[alias] = obj
                ri = int(sub.index[0])
                for k, v in obj.items():
                    var = f'{alias}.{k}'
                    trace[var] = TraceItem(
                        var=var, table=tname, field=k, value=v, pk=pk_val,
                        row_index=ri, source_file=f'{tname}.xlsx',
                    )
            else:
                lst = sub.to_dict(orient='records')
                context[alias] = lst
                for row_i, rec in enumerate(lst):
                    ri = int(sub.index[row_i]) if row_i < len(sub.index) else None
                    for k, v in rec.items():
                        var = f'{alias}.{row_i}.{k}'
                        trace[var] = TraceItem(
                            var=var, table=tname, field=k, value=v, pk=pk_val,
                            row_index=ri, source_file=f'{tname}.xlsx',
                        )

        # 添加条件表达式溯源（通用，支持任意条件表达式）
        add_condition_traces(
            context=context,
            trace_map=trace,
            pk_val=pk_val,
            template_path=template_path,
            template_text=template_text
        )
        
        out.append((context, trace))

    return out


# --- 测试 ---
template_file, table_names, main_table = get_template_tables(relation_df2, template_id=1)
tables_loaded = load_data_tables(DIRS['data'], table_names)
contexts = build_report_contexts(schema_df2, tables_loaded, main_table=main_table)
print('报告份数（=主表行数）:', len(contexts))
print('首份 trace 条数:', len(contexts[0][1]))
'''

CELL10 = r'''# Cell 10: 模板 zip 读取 AI prompt + 文档 XML 工具（docxtpl 渲染后无 comments.xml）
import zipfile
import re
from lxml import etree
from typing import Dict, List, NamedTuple

W_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


class CommentBlock(NamedTuple):
    comment_id: str
    prompt_tpl: str
    text_final: str


def read_docx_xml(docx_path: Path, internal_path: str) -> bytes:
    """从 docx zip 读取内部 XML。"""
    with zipfile.ZipFile(docx_path, 'r') as z:
        return z.read(internal_path)


def extract_prompt_from_comment_text(comment_text: str) -> str:
    """从批注正文中解析 prompt=\"...\" """
    m = re.search(r'prompt\s*=\s*"([\s\S]*?)"', comment_text)
    if not m:
        raise ValueError('批注中未找到 prompt="..."')
    return m.group(1)


def extract_comments_map_from_bytes(xml_bytes: bytes) -> Dict[str, str]:
    root = etree.fromstring(xml_bytes)
    out: Dict[str, str] = {}
    for c in root.xpath('.//w:comment', namespaces=W_NS):
        cid = c.get('{%s}id' % W_NS['w'])
        texts = c.xpath('.//w:t/text()', namespaces=W_NS)
        out[str(cid)] = ''.join(texts)
    return out


def load_ai_prompts_from_template(template_docx: Path) -> List[str]:
    """
    从【模板】docx 的 comments.xml 按 id 排序提取 prompt（与 §AIBLOCK0§ 顺序对应）。
    docxtpl 渲染结果通常不含 comments.xml，必须从模板读取。
    """
    try:
        xml_bytes = read_docx_xml(template_docx, 'word/comments.xml')
    except KeyError:
        return []
    cmap = extract_comments_map_from_bytes(xml_bytes)
    prompts: List[str] = []
    for cid in sorted(cmap.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        text = cmap[cid]
        if 'prompt' not in text:
            continue
        try:
            prompts.append(extract_prompt_from_comment_text(text))
        except ValueError:
            continue
    return prompts


def iter_document_order(root: etree._Element):
    yield root
    for child in root:
        yield from iter_document_order(child)


def extract_range_text(document_root: etree._Element, comment_id: str) -> str:
    start = document_root.xpath(f".//w:commentRangeStart[@w:id='{comment_id}']", namespaces=W_NS)
    end = document_root.xpath(f".//w:commentRangeEnd[@w:id='{comment_id}']", namespaces=W_NS)
    if not start or not end:
        raise ValueError(f'找不到 commentRange, id={comment_id}')
    start_el, end_el = start[0], end[0]
    all_nodes = list(iter_document_order(document_root))
    try:
        i0, i1 = all_nodes.index(start_el), all_nodes.index(end_el)
    except ValueError:
        return ''
    if i1 <= i0:
        return ''
    parts = []
    for node in all_nodes[i0 + 1:i1]:
        if node.tag == '{%s}t' % W_NS['w']:
            parts.append(node.text or '')
        else:
            for t in node.xpath('.//w:t', namespaces=W_NS):
                parts.append(t.text or '')
    return ''.join(parts).strip()


def extract_ai_comment_blocks(docx_path: Path) -> List[CommentBlock]:
    try:
        cmap = extract_comments_map_from_bytes(read_docx_xml(docx_path, 'word/comments.xml'))
    except KeyError:
        return []
    if not cmap:
        return []
    doc_root = etree.fromstring(read_docx_xml(docx_path, 'word/document.xml'))
    blocks: List[CommentBlock] = []
    for cid, ctext in cmap.items():
        if 'prompt' not in ctext:
            continue
        try:
            pt = extract_prompt_from_comment_text(ctext)
        except ValueError:
            continue
        try:
            tf = extract_range_text(doc_root, cid)
        except ValueError:
            tf = ''
        blocks.append(CommentBlock(comment_id=cid, prompt_tpl=pt, text_final=tf))
    return blocks


_tpl = DIRS['templates'] / 'template_1.docx'
if _tpl.exists():
    _ps = load_ai_prompts_from_template(_tpl)
    print('模板中 AI prompt 条数:', len(_ps))
    if _ps:
        print('首条 prompt 预览:', _ps[0][:80], '...')
'''

CELL11 = r'''# Cell 11: 渲染 prompt（Jinja2）+ DeepSeek 调用
import os
from jinja2 import Environment, StrictUndefined
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
DEEPSEEK_MODEL = 'deepseek-chat'


def build_jinja_env() -> Environment:
    return Environment(undefined=StrictUndefined)


def render_prompt(prompt_tpl: str, context: dict) -> str:
    env = build_jinja_env()
    return env.from_string(prompt_tpl).render(context)


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEEPSEEK_BASE_URL,
        model: str = DEEPSEEK_MODEL,
    ):
        if not api_key:
            raise ValueError('未提供 API Key，请设置环境变量 DEEPSEEK_API_KEY')
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def rewrite(self, text_final: str, prompt_final: str) -> str:
        messages = [
            {'role': 'system', 'content': '你是严谨的金融风险分析助手，输出简洁专业。'},
            {'role': 'user', 'content': (
                '请根据【当前段落原文】与【任务说明】生成最终可放入 Word 的正文（不要重复标题）。\n\n'
                f'【当前段落原文】\n{text_final}\n\n【任务说明】\n{prompt_final}'
            )},
        ]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return (resp.choices[0].message.content or '').strip()


api_key = os.getenv('DEEPSEEK_API_KEY')
print('DEEPSEEK_API_KEY 已设置:', bool(api_key))
_demo_ctx = contexts[0][0] if contexts else {}
_demo_prompts = load_ai_prompts_from_template(DIRS['templates'] / 'template_1.docx') if (DIRS['templates'] / 'template_1.docx').exists() else []
if _demo_prompts:
    print('渲染后 prompt 示例:', render_prompt(_demo_prompts[0], _demo_ctx)[:120], '...')
'''

CELL12 = r'''# Cell 12: 数据溯源批注 + AI 段落（§AIBLOCKn§）后处理并保存
import io
import zipfile
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone

CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'


def _wtag(name: str) -> str:
    return '{%s}%s' % (W_NS['w'], name)


def _collect_max_comment_id(doc_root: etree._Element, comments_root: etree._Element | None) -> int:
    ids: list[int] = []

    def grab(el):
        for k, v in el.attrib.items():
            if k.endswith('}id') or k == 'id':
                if str(v).isdigit():
                    ids.append(int(v))

    for el in doc_root.iter():
        if el.tag in (_wtag('commentRangeStart'), _wtag('commentRangeEnd'), _wtag('commentReference')):
            grab(el)
    if comments_root is not None:
        for el in comments_root.iter():
            if el.tag == _wtag('comment'):
                grab(el)
    return max(ids) if ids else -1


def _load_zip_dict(docx_path: Path) -> dict:
    with zipfile.ZipFile(docx_path, 'r') as z:
        return {n: z.read(n) for n in z.namelist()}


def _write_zip_dict(docx_path: Path, files: dict) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            z.writestr(name, data)
    docx_path.write_bytes(buf.getvalue())


def _ensure_comments_infra(files: dict) -> etree._Element:
    """
    保证 [Content_Types]、document.xml.rels、comments.xml 存在。
    返回 comments 根元素（可修改）。
    """
    ct = etree.fromstring(files['[Content_Types].xml'])
    part = '/word/comments.xml'
    ov_tag = '{%s}Override' % CT_NS
    if not any(el.get('PartName') == part for el in ct.findall('.//' + ov_tag)):
        ov = etree.Element(ov_tag)
        ov.set('PartName', part)
        ov.set('ContentType', 'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml')
        ct.append(ov)
    files['[Content_Types].xml'] = etree.tostring(ct, xml_declaration=True, encoding='UTF-8', standalone='yes')

    rel_path = 'word/_rels/document.xml.rels'
    rel_root = etree.fromstring(files[rel_path])
    rtag = '{%s}Relationship' % REL_NS
    has = any((el.get('Target') or '').endswith('comments.xml') for el in rel_root.findall(rtag))
    if not has:
        max_n = 0
        for el in rel_root.findall(rtag):
            rid = el.get('Id') or ''
            if rid.startswith('rId') and rid[3:].isdigit():
                max_n = max(max_n, int(rid[3:]))
        r = etree.Element(rtag)
        r.set('Id', f'rId{max_n + 1}')
        r.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments')
        r.set('Target', 'comments.xml')
        rel_root.append(r)
    files[rel_path] = etree.tostring(rel_root, xml_declaration=True, encoding='UTF-8', standalone='yes')

    if 'word/comments.xml' in files:
        com_root = etree.fromstring(files['word/comments.xml'])
    else:
        com_root = etree.Element(_wtag('comments'), nsmap={'w': W_NS['w']})
        files['word/comments.xml'] = etree.tostring(com_root, xml_declaration=True, encoding='UTF-8', standalone='yes')
        com_root = etree.fromstring(files['word/comments.xml'])
    return com_root


def _paragraph_full_text(w_p) -> str:
    return ''.join(w_p.xpath('.//w:t/text()', namespaces=W_NS))


def _find_paragraph_contains(doc_root, substr: str):
    for w_p in doc_root.xpath('.//w:p', namespaces=W_NS):
        if substr in _paragraph_full_text(w_p):
            return w_p
    return None


def _replace_paragraph_text(w_p, new_text: str) -> None:
    ts = w_p.xpath('.//w:t', namespaces=W_NS)
    if not ts:
        return
    ts[0].text = new_text
    for t in ts[1:]:
        t.text = ''


def _wrap_run_with_comment(parent, w_r, cid: int) -> None:
    """在 w:p 子树中，给指定 w:r 包上 commentRangeStart/End 与 commentReference。"""
    idx = parent.index(w_r)
    st = etree.Element(_wtag('commentRangeStart'))
    st.set('{%s}id' % W_NS['w'], str(cid))
    en = etree.Element(_wtag('commentRangeEnd'))
    en.set('{%s}id' % W_NS['w'], str(cid))
    ref_r = etree.Element(_wtag('r'))
    ref_cr = etree.SubElement(ref_r, _wtag('commentReference'))
    ref_cr.set('{%s}id' % W_NS['w'], str(cid))
    parent.insert(idx, st)
    parent.insert(idx + 2, en)
    parent.insert(idx + 3, ref_r)


def _append_comment_xml(comments_root: etree._Element, cid: int, body: str, author: str = '数据溯源', initials: str = 'SRC') -> None:
    c = etree.SubElement(comments_root, _wtag('comment'))
    c.set('{%s}id' % W_NS['w'], str(cid))
    c.set('{%s}author' % W_NS['w'], author)
    c.set('{%s}date' % W_NS['w'], datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    c.set('{%s}initials' % W_NS['w'], initials)
    p = etree.SubElement(c, _wtag('p'))
    r = etree.SubElement(p, _wtag('r'))
    t = etree.SubElement(r, _wtag('t'))
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = body[:8000] if len(body) > 8000 else body


def build_trace_annotation_pairs(trace_map: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    生成 (展示字符串, 批注正文) 列表，按展示字符串长度降序，减少短串误匹配。
    支持TraceItem和条件表达式字典。
    """
    pairs: List[Tuple[str, str]] = []
    for _k, ti in trace_map.items():
        # 处理TraceItem对象
        if hasattr(ti, 'value'):
            disp = format_display_value(ti.value)
        # 处理字典格式（条件表达式）
        elif isinstance(ti, dict) and 'value' in ti:
            disp = format_display_value(ti['value'])
        else:
            continue
            
        if disp == '':
            continue
            
        # 构建批注正文
        if isinstance(ti, dict) and ti.get('_is_condition'):
            # 条件表达式的批注
            condition = ti.get('field', '')
            expr_info = ti.get('_expression_info', {})
            variables = expr_info.get('variables', [])
            table = ti.get('table', '__condition__')
            
            # 构建详细的批注内容
            var_desc = f"条件表达式: {condition}"
            if variables:
                var_desc += f" (变量: {', '.join(variables)})"
            
            body = f"[数据来源] 表={table} 字段={condition} 值={disp} | 变量={var_desc} | 主键={ti.get('pk', '')}"
            
            # 添加表达式解析信息
            if expr_info.get('parsed'):
                parsed = expr_info['parsed']
                operator_map = {'lt': '<', 'le': '<=', 'gt': '>', 'ge': '>=', 'eq': '==', 'ne': '!=', 'in': 'in', 'not_in': 'not in'}
                op_symbol = operator_map.get(parsed.get('operator', ''), parsed.get('operator', ''))
                body += f" | 表达式: {parsed.get('left', '')} {op_symbol} {parsed.get('right', '')}"
        else:
            # 普通数据字段的批注
            table = ti.table if hasattr(ti, 'table') else ti.get('table', '')
            field = ti.field if hasattr(ti, 'field') else ti.get('field', '')
            var = ti.var if hasattr(ti, 'var') else ti.get('var', '')
            pk = ti.pk if hasattr(ti, 'pk') else ti.get('pk', '')
            body = f"[数据来源] 表={table} 字段={field} 值={disp} | 变量={var} | 主键={pk}"
        
        pairs.append((disp, body))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def annotate_values_in_document(doc_root: etree._Element, comments_root: etree._Element, trace_map: Dict[str, TraceItem]) -> None:
    """
    遍历 document 中每个 w:t：若整段文本（strip 后）等于某 trace 展示值，则为所在 w:r 加批注。
    说明：docxtpl 常将每个字段放在独立 run，故整 run 匹配在多数场景可行；若被拆 run，可后续增强合并匹配。
    """
    cid = _collect_max_comment_id(doc_root, comments_root) + 1
    pairs = build_trace_annotation_pairs(trace_map)
    annotated_r = set()

    for w_t in doc_root.xpath('.//w:t', namespaces=W_NS):
        raw = w_t.text or ''
        s = raw.strip()
        if not s:
            continue
        w_r = w_t.getparent()
        while w_r is not None and w_r.tag != _wtag('r'):
            w_r = w_r.getparent()
        if w_r is None or id(w_r) in annotated_r:
            continue

        matched = None
        for disp, body in pairs:
            if s == disp:
                matched = body
                break
        if not matched:
            continue

        _append_comment_xml(comments_root, cid, matched)
        # 必须在 w:r 的直接父节点下插入 commentRange（可能是 w:p 或 w:hyperlink 等）
        _wrap_run_with_comment(w_r.getparent(), w_r, cid)
        annotated_r.add(id(w_r))
        cid += 1


def apply_ai_by_markers(
    doc_root: etree._Element,
    template_path: Path,
    context: dict,
    markers: List[str],
    client: Any | None,
) -> List[Tuple[str, str, str]]:
    """
    按 §AIBLOCKn§ 定位段落，从模板 comments 顺序取 prompt，调用 AI 后写回段落纯文本。

    Returns:
        [(marker, prompt_final, ai_text), ...]
    """
    prompts = load_ai_prompts_from_template(template_path)
    results = []
    for i, marker in enumerate(markers):
        w_p = _find_paragraph_contains(doc_root, marker)
        if w_p is None:
            print(f'警告: 未找到含标记 {marker!r} 的段落，跳过该 AI 块')
            continue
        full = _paragraph_full_text(w_p)
        text_final = full.replace(marker, '').strip()
        prompt_tpl = prompts[i] if i < len(prompts) else ''
        prompt_final = render_prompt(prompt_tpl, context) if prompt_tpl else ''
        if client is not None and prompt_final:
            try:
                ai_text = client.rewrite(text_final, prompt_final)
            except Exception as e:
                print('DeepSeek 调用失败，保留原文:', e)
                ai_text = text_final
        else:
            ai_text = text_final
        _replace_paragraph_text(w_p, ai_text)
        results.append((marker, prompt_final, ai_text))
    return results


def finalize_rendered_document(
    rendered_docx: Path,
    template_docx: Path,
    context: dict,
    trace_map: Dict[str, TraceItem],
    output_docx: Path,
    use_ai: bool,
    api_key: str | None,
    ai_markers: List[str] | None = None,
) -> Path:
    """
    对 docxtpl 已渲染的 docx：可选 AI 改写 → 为数据值加溯源批注 → 为 AI 段追加说明批注。

    Args:
        rendered_docx: docxtpl 输出路径
        template_docx: 原始模板（读取 comments 中 prompt）
        context: 渲染上下文
        trace_map: 溯源字典
        output_docx: 最终输出路径
        use_ai: 是否调用 DeepSeek（需 api_key）
        api_key: DEEPSEEK_API_KEY
        ai_markers: 如 ['§AIBLOCK0§']；None 则使用全局 AI_BLOCK_MARKERS

    Returns:
        output_docx
    """
    if ai_markers is None:
        ai_markers = globals().get('AI_BLOCK_MARKERS', ['§AIBLOCK0§'])

    files = _load_zip_dict(rendered_docx)
    doc_root = etree.fromstring(files['word/document.xml'])
    comments_root = _ensure_comments_infra(files)

    client = None
    if use_ai and api_key:
        try:
            client = DeepSeekClient(api_key=api_key)
        except Exception as e:
            print('无法初始化 DeepSeek 客户端:', e)

    # 先 AI 替换段落，再为「仍保留在文档中的数据字面量」加溯源批注，避免批注锚在随后被清空的 run 上
    ai_meta = apply_ai_by_markers(doc_root, template_docx, context, ai_markers, client)

    annotate_values_in_document(doc_root, comments_root, trace_map)

    # AI 段：在首 run 上挂一条总览批注
    cid = _collect_max_comment_id(doc_root, comments_root) + 1
    for marker, prompt_final, ai_text in ai_meta:
        snippet = ai_text[:200] + ('…' if len(ai_text) > 200 else '')
        body = f"[AI生成说明] 标记={marker}\n[PROMPT]\n{prompt_final}\n[OUTPUT]\n{snippet}"
        w_p = None
        at = (ai_text or '').strip()
        for cand in doc_root.xpath('.//w:p', namespaces=W_NS):
            if _paragraph_full_text(cand).strip() == at:
                w_p = cand
                break
        if w_p is None and at:
            w_p = _find_paragraph_contains(doc_root, at[: min(40, len(at))])
        if w_p is None:
            continue
        runs = w_p.xpath('.//w:r', namespaces=W_NS)
        if not runs:
            continue
        w_run = runs[0]
        _append_comment_xml(comments_root, cid, body, author='AI', initials='AI')
        _wrap_run_with_comment(w_run.getparent(), w_run, cid)
        cid += 1

    files['word/document.xml'] = etree.tostring(doc_root, xml_declaration=True, encoding='UTF-8', standalone='yes')
    files['word/comments.xml'] = etree.tostring(comments_root, xml_declaration=True, encoding='UTF-8', standalone='yes')
    _write_zip_dict(output_docx, files)
    return output_docx


# --- 可选测试：在跑完 Cell 9 后取消注释 ---
# finalize_rendered_document(
#     DIRS['output'] / 'mid_A.docx',
#     DIRS['templates'] / 'template_1.docx',
#     contexts[0][0],
#     contexts[0][1],
#     DIRS['output'] / 'final_A_demo.docx',
#     use_ai=False,
#     api_key=None,
# )
'''

CELL13 = r'''# Cell 13: 智能生成入口 — 多模板 ID、确认数据表、批量/单份、可选无 AI
import os
from typing import Iterable, List

# 若 Cell 5 未运行，提供默认标记列表
if 'AI_BLOCK_MARKERS' not in globals():
    AI_BLOCK_MARKERS = ['§AIBLOCK0§']


def parse_template_id_input(s: str) -> List[int]:
    """解析用户输入的模板 ID 列表（逗号分隔）。"""
    out: List[int] = []
    for part in s.replace('，', ',').split(','):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    if not out:
        raise ValueError('未解析到任何模板 ID')
    return out


def summarize_required_tables(relation_df: pd.DataFrame, template_ids: Iterable[int]) -> dict[int, List[str]]:
    """每个模板 ID -> 所需实体表名列表。"""
    m: dict[int, List[str]] = {}
    for tid in template_ids:
        _f, tables, _m = get_template_tables(relation_df, int(tid))
        m[int(tid)] = list(dict.fromkeys(tables))
    return m


def run_smart_document_generation(
    template_ids: List[int],
    data_dir: Path | None = None,
    use_ai: bool = False,
    skip_confirm: bool = False,
) -> List[Path]:
    """
    按模板 ID 列表批量生成报告（每个模板：主表多行则多份）。

    Args:
        template_ids: 模板 ID
        data_dir: 数据目录，默认 DIRS['data']
        use_ai: 是否调用 DeepSeek（需环境变量 DEEPSEEK_API_KEY）
        skip_confirm: True 时非交互（测试用）

    Returns:
        生成的最终 docx 路径列表
    """
    data_dir = data_dir or DIRS['data']
    schema_path = DIRS['config'] / 'entity_schema.xlsx'
    relation_path = DIRS['config'] / 'template_relation.xlsx'
    schema_df = load_entity_schema(schema_path)
    relation_df = load_template_relation(relation_path)
    api_key = os.getenv('DEEPSEEK_API_KEY')

    req = summarize_required_tables(relation_df, template_ids)
    print('=== 各模板所需数据表（请在数据目录准备 表名.xlsx）===')
    for tid, tabs in req.items():
        print(f'  模板 {tid}: {tabs}')
    print(f'数据目录: {data_dir.resolve()}')

    if not skip_confirm:
        ans = input('确认已准备好上述 Excel？(y/n): ').strip().lower()
        if ans not in ('y', 'yes', '是'):
            print('已取消生成。')
            return []

    outputs: List[Path] = []
    for tid in template_ids:
        template_file, table_names, main_table = get_template_tables(relation_df, tid)
        tables = load_data_tables(data_dir, table_names)
        tpl_path = DIRS['templates'] / template_file
        if not tpl_path.exists():
            raise FileNotFoundError(f'模板文件不存在: {tpl_path}')
        ctx_list = build_report_contexts(schema_df, tables, main_table=main_table, template_path=tpl_path)

        for i, (ctx, trace) in enumerate(ctx_list):
            pk = ctx.get('data', {})
            pk_val = pk.get('branch_name', pk.get(list(pk.keys())[0] if pk else 'key', f'idx{i}'))
            safe_name = str(pk_val).replace('/', '_').replace('\\', '_')
            mid_name = f'mid_tpl{tid}_{safe_name}.docx'
            final_name = f'report_tpl{tid}_{safe_name}.docx'
            mid_path = DIRS['output'] / mid_name
            final_path = DIRS['output'] / final_name

            render_docx_template(tpl_path, ctx, mid_path)
            finalize_rendered_document(
                mid_path,
                tpl_path,
                ctx,
                trace,
                final_path,
                use_ai=use_ai,
                api_key=api_key,
                ai_markers=list(AI_BLOCK_MARKERS),
            )
            outputs.append(final_path)
            print('已生成:', final_path)

    return outputs


def interactive_smart_generation() -> None:
    """交互：输入模板 ID → 展示依赖表 → 确认 → 生成（可选 AI）。"""
    raw = input('请输入要生成的 Word 模板 ID，多个用英文逗号分隔: ')
    tids = parse_template_id_input(raw)
    want_ai = input('是否调用 DeepSeek 进行 AI 改写？(y/n): ').strip().lower() in ('y', 'yes', '是')
    run_smart_document_generation(tids, use_ai=want_ai, skip_confirm=False)


# 非交互自测示例（需要前面 Cell 已加载 relation_df2 等）:
# run_smart_document_generation([1], use_ai=False, skip_confirm=True)
'''