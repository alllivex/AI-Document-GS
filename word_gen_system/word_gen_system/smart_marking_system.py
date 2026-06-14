# -*- coding: utf-8 -*-
"""智能标记系统 - 模板预处理与位置标记

本模块实现基于位置标记的精确批注生成系统，解决文本匹配导致的批注缺失问题。
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any, Set
from pathlib import Path
from enum import Enum


class MarkerType(Enum):
    """标记类型枚举"""
    VARIABLE = "variable"      # 基础变量标记
    CONDITION = "condition"    # 条件表达式标记
    BLOCK = "block"           # 逻辑块标记
    AI_BLOCK = "ai_block"     # AI段落标记


@dataclass
class PositionMarker:
    """位置标记 - 记录模板中的标记信息"""
    marker_id: str            # 唯一标识符，如 "VAR_001", "COND_001"
    marker_type: MarkerType   # 标记类型
    var_path: str            # 变量路径，如 "data.branch_name"
    template_pos: Tuple[int, int]  # 在模板中的位置(起始, 结束)
    original_text: str       # 原始模板文本
    marked_text: str         # 标记后的文本


@dataclass
class DocumentPosition:
    """文档位置 - 记录标记在渲染后文档中的位置"""
    marker_id: str
    xml_path: str           # XML中的路径，如 "/word/document/body[1]/p[1]/r[1]/t[1]"
    text_range: Tuple[int, int]  # 文本范围(起始, 结束)
    text_content: str       # 实际渲染文本
    element_ref: Any        # XML元素引用(可选)


@dataclass
class PositionMapping:
    """位置映射 - 关联标记与文档位置"""
    marker: PositionMarker
    doc_position: DocumentPosition
    trace_item: Any         # 关联的TraceItem


class TemplateMarker:
    """模板标记器 - 自动为模板添加位置标记"""
    
    def __init__(self):
        self.marker_counter = {
            MarkerType.VARIABLE: 0,
            MarkerType.CONDITION: 0,
            MarkerType.BLOCK: 0,
            MarkerType.AI_BLOCK: 0
        }
    
    def _get_next_marker_id(self, marker_type: MarkerType) -> str:
        """生成下一个标记ID"""
        counter = self.marker_counter[marker_type]
        self.marker_counter[marker_type] += 1
        
        prefix_map = {
            MarkerType.VARIABLE: "VAR",
            MarkerType.CONDITION: "COND",
            MarkerType.BLOCK: "BLOCK",
            MarkerType.AI_BLOCK: "AI"
        }
        
        return f"{prefix_map[marker_type]}_{counter:03d}"
    
    def _extract_variables(self, template_text: str) -> List[Tuple[str, Tuple[int, int]]]:
        """提取模板中的所有变量及其位置"""
        variables = []
        pattern = r'\{\{\s*([^{}]+?)\s*\}\}'
        
        for match in re.finditer(pattern, template_text):
            var_expr = match.group(1)
            # 跳过已经包含过滤器的变量
            if '|' in var_expr:
                continue
            start, end = match.span()
            variables.append((var_expr, (start, end)))
        
        return variables
    
    def _extract_conditions(self, template_text: str) -> List[Tuple[str, Tuple[int, int]]]:
        """提取模板中的所有条件表达式及其位置"""
        conditions = []
        # 匹配 {% if ... %} 结构
        pattern = r'(\{%\s*if\s+)(.+?)(\s*%\})'
        
        for match in re.finditer(pattern, template_text, re.DOTALL):
            condition = match.group(2)
            start, end = match.start(2), match.end(2)
            conditions.append((condition, (start, end)))
        
        return conditions
    
    def _extract_ai_blocks(self, template_text: str) -> List[Tuple[str, Tuple[int, int]]]:
        """提取模板中的所有AI块标记及其位置"""
        ai_blocks = []
        pattern = r'(§AIBLOCK\d+§)'
        
        for match in re.finditer(pattern, template_text):
            ai_marker = match.group(1)
            start, end = match.span()
            ai_blocks.append((ai_marker, (start, end)))
        
        return ai_blocks
    
    def mark_template(self, template_text: str) -> Tuple[str, List[PositionMarker]]:
        """
        为模板添加位置标记
        
        Args:
            template_text: 原始模板文本
            
        Returns:
            (marked_template, markers): 标记后的模板和标记列表
        """
        markers = []
        marked_template = template_text
        
        # 1. 标记AI块（优先级最高）
        ai_blocks = self._extract_ai_blocks(marked_template)
        for ai_marker, (start, end) in reversed(ai_blocks):  # 反向处理避免位置偏移
            marker_id = self._get_next_marker_id(MarkerType.AI_BLOCK)
            original_text = ai_marker
            marked_text = f"{ai_marker}|trace('{marker_id}')"
            
            marker = PositionMarker(
                marker_id=marker_id,
                marker_type=MarkerType.AI_BLOCK,
                var_path=ai_marker,
                template_pos=(start, end),
                original_text=original_text,
                marked_text=marked_text
            )
            markers.append(marker)
            
            # 替换模板中的文本
            marked_template = (
                marked_template[:start] + 
                marked_text + 
                marked_template[end:]
            )
        
        # 2. 标记条件表达式
        conditions = self._extract_conditions(marked_template)
        for condition, (start, end) in reversed(conditions):
            marker_id = self._get_next_marker_id(MarkerType.CONDITION)
            original_text = condition
            marked_text = f"{condition}|trace('{marker_id}')"
            
            marker = PositionMarker(
                marker_id=marker_id,
                marker_type=MarkerType.CONDITION,
                var_path=condition,
                template_pos=(start, end),
                original_text=original_text,
                marked_text=marked_text
            )
            markers.append(marker)
            
            # 替换模板中的文本
            marked_template = (
                marked_template[:start] + 
                marked_text + 
                marked_template[end:]
            )
        
        # 3. 标记变量
        variables = self._extract_variables(marked_template)
        for var_expr, (start, end) in reversed(variables):
            marker_id = self._get_next_marker_id(MarkerType.VARIABLE)
            original_text = f"{{{{ {var_expr} }}}}"
            marked_text = f"{{{{ {var_expr}|trace('{marker_id}') }}}}"
            
            marker = PositionMarker(
                marker_id=marker_id,
                marker_type=MarkerType.VARIABLE,
                var_path=var_expr,
                template_pos=(start, end),
                original_text=original_text,
                marked_text=marked_text
            )
            markers.append(marker)
            
            # 替换模板中的文本
            marked_template = (
                marked_template[:start] + 
                marked_text + 
                marked_template[end:]
            )
        
        return marked_template, markers


class SmartAnnotationGenerator:
    """智能批注生成器 - 基于位置映射生成精确批注"""
    
    def __init__(self):
        self.w_ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    def _wtag(self, name: str) -> str:
        """生成带命名空间的标签名"""
        return '{%s}%s' % (self.w_ns['w'], name)
    
    def _append_comment_xml(self, comments_root, cid: int, body: str, 
                          author: str = '数据溯源', initials: str = 'SRC') -> None:
        """添加批注XML"""
        from lxml import etree
        from datetime import datetime, timezone
        
        c = etree.SubElement(comments_root, self._wtag('comment'))
        c.set('{%s}id' % self.w_ns['w'], str(cid))
        c.set('{%s}author' % self.w_ns['w'], author)
        c.set('{%s}date' % self.w_ns['w'], datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        c.set('{%s}initials' % self.w_ns['w'], initials)
        p = etree.SubElement(c, self._wtag('p'))
        r = etree.SubElement(p, self._wtag('r'))
        t = etree.SubElement(r, self._wtag('t'))
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = body[:8000] if len(body) > 8000 else body
    
    def _wrap_run_with_comment(self, parent, w_r, cid: int) -> None:
        """为运行添加批注标记"""
        from lxml import etree
        
        idx = parent.index(w_r)
        st = etree.Element(self._wtag('commentRangeStart'))
        st.set('{%s}id' % self.w_ns['w'], str(cid))
        en = etree.Element(self._wtag('commentRangeEnd'))
        en.set('{%s}id' % self.w_ns['w'], str(cid))
        ref_r = etree.Element(self._wtag('r'))
        ref_cr = etree.SubElement(ref_r, self._wtag('commentReference'))
        ref_cr.set('{%s}id' % self.w_ns['w'], str(cid))
        parent.insert(idx, st)
        parent.insert(idx + 2, en)
        parent.insert(idx + 3, ref_r)
    
    def _collect_max_comment_id(self, doc_root, comments_root) -> int:
        """收集文档中最大的批注ID"""
        from lxml import etree
        
        ids = []
        
        def grab(el):
            for k, v in el.attrib.items():
                if k.endswith('}id') or k == 'id':
                    if str(v).isdigit():
                        ids.append(int(v))
        
        for el in doc_root.iter():
            if el.tag in (self._wtag('commentRangeStart'), 
                         self._wtag('commentRangeEnd'), 
                         self._wtag('commentReference')):
                grab(el)
        if comments_root is not None:
            for el in comments_root.iter():
                if el.tag == self._wtag('comment'):
                    grab(el)
        return max(ids) if ids else -1
    
    def _create_annotation_body(self, position_mapping: PositionMapping) -> str:
        """创建批注正文"""
        trace_item = position_mapping.trace_item
        marker = position_mapping.marker
        
        # 处理不同类型的标记
        if marker.marker_type == MarkerType.CONDITION:
            # 条件表达式的批注
            condition = trace_item.get('field', '')
            expr_info = trace_item.get('_expression_info', {})
            variables = expr_info.get('variables', [])
            result = trace_item.get('_condition_result', False)
            display_text = trace_item.get('value', '')
            
            var_desc = f"条件表达式: {condition}"
            if variables:
                var_desc += f" (变量: {', '.join(variables)})"
            
            body = (f"[条件表达式溯源] 表达式={condition} | 结果={'True' if result else 'False'} "
                   f"| 显示文本={display_text} | {var_desc}")
            
            if expr_info.get('parsed'):
                parsed = expr_info['parsed']
                operator_map = {'lt': '<', 'le': '<=', 'gt': '>', 'ge': '>=', 
                               'eq': '==', 'ne': '!=', 'in': 'in', 'not_in': 'not in'}
                op_symbol = operator_map.get(parsed.get('operator', ''), parsed.get('operator', ''))
                body += f" | 计算: {parsed.get('left', '')} {op_symbol} {parsed.get('right', '')}"
            
            return body
        
        elif marker.marker_type == MarkerType.AI_BLOCK:
            # AI段落的批注（保持原有逻辑）
            return f"[AI生成说明] 标记={marker.var_path}"
        
        else:
            # 普通变量的批注
            table = trace_item.table if hasattr(trace_item, 'table') else trace_item.get('table', '')
            field = trace_item.field if hasattr(trace_item, 'field') else trace_item.get('field', '')
            var = trace_item.var if hasattr(trace_item, 'var') else trace_item.get('var', '')
            pk = trace_item.pk if hasattr(trace_item, 'pk') else trace_item.get('pk', '')
            value = trace_item.value if hasattr(trace_item, 'value') else trace_item.get('value', '')
            
            return f"[数据来源] 表={table} 字段={field} 值={value} | 变量={var} | 主键={pk}"
    
    def annotate_by_mapping(self, doc_root, position_mappings: List[PositionMapping], 
                          comments_root) -> None:
        """
        基于位置映射生成批注
        
        Args:
            doc_root: 文档XML根元素
            position_mappings: 位置映射列表
            comments_root: 批注XML根元素
        """
        from lxml import etree
        
        cid = self._collect_max_comment_id(doc_root, comments_root) + 1
        
        for mapping in position_mappings:
            # 根据xml_path定位元素
            try:
                # 简化实现：这里我们使用文本内容匹配
                # 在实际实现中，应该根据xml_path直接定位
                target_text = mapping.doc_position.text_content
                
                # 在文档中查找包含目标文本的元素
                for w_t in doc_root.xpath('.//w:t', namespaces=self.w_ns):
                    if w_t.text and target_text in w_t.text:
                        w_r = w_t.getparent()
                        while w_r is not None and w_r.tag != self._wtag('r'):
                            w_r = w_r.getparent()
                        
                        if w_r is not None:
                            # 创建批注
                            body = self._create_annotation_body(mapping)
                            self._append_comment_xml(comments_root, cid, body)
                            self._wrap_run_with_comment(w_r.getparent(), w_r, cid)
                            cid += 1
                        break
            except Exception as e:
                print(f"警告: 为标记 {mapping.marker.marker_id} 生成批注时出错: {e}")
                continue


# 兼容性辅助函数
def trace_filter(value, marker_id=None):
    """
    Jinja2过滤器：用于标记变量，实际渲染中不做任何修改
    
    使用方式: {{ data.branch_name|trace("VAR_001") }}
    """
    # 这个过滤器在实际渲染中不做任何修改，只是用于标记
    return value


def create_trace_mapping(trace_map: Dict[str, Any], markers: List[PositionMarker]) -> Dict[str, Any]:
    """
    创建标记到TraceItem的映射
    
    Args:
        trace_map: 原始的trace映射
        markers: 位置标记列表
        
    Returns:
        标记ID到TraceItem的映射
    """
    mapping = {}
    
    for marker in markers:
        if marker.marker_type == MarkerType.VARIABLE:
            # 查找对应的TraceItem
            var_key = marker.var_path.replace('.', '_')
            for trace_key, trace_item in trace_map.items():
                if hasattr(trace_item, 'var') and trace_item.var == marker.var_path:
                    mapping[marker.marker_id] = trace_item
                    break
                elif isinstance(trace_item, dict) and trace_item.get('var') == marker.var_path:
                    mapping[marker.marker_id] = trace_item
                    break
    
    return mapping


# 在smart_marking_system.py文件末尾添加以下代码

class DeepSeekClient:
    """DeepSeek AI客户端（从Cell 11复制）"""
    def __init__(
        self,
        api_key: str,
        base_url: str = 'https://api.deepseek.com/v1',
        model: str = 'deepseek-chat',
    ):
        if not api_key:
            raise ValueError('未提供 API Key，请设置环境变量 DEEPSEEK_API_KEY')
        self.model = model
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def rewrite(self, text_final: str, prompt_final: str) -> str:
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def _call_api():
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
        
        return _call_api()
"""
智能标记系统，用于增强文档批注的精确性
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from lxml import etree
import re
from jinja2 import Environment, StrictUndefined


class MarkerType(Enum):
    VARIABLE = "variable"
    CONDITION = "condition"
    LITERAL = "literal"


@dataclass
class TemplateMarker:
    """模板标记对象"""
    marker_id: str
    marker_type: MarkerType
    original_text: str
    var_path: Optional[str] = None  # 仅对VARIABLE类型有效
    condition: Optional[str] = None  # 仅对CONDITION类型有效


@dataclass
class DocumentPosition:
    """文档位置信息"""
    marker_id: str
    xml_path: str
    text_range: Tuple[int, int]  # (start, end) in text
    text_content: str
    element_ref: Optional[Any] = None


@dataclass
class PositionMapping:
    """位置映射"""
    marker: TemplateMarker
    doc_position: DocumentPosition
    trace_item: Any  # 可能是TraceItem或字典


class TemplateMarkerProcessor:
    """模板标记处理器"""
    
    def __init__(self):
        self.marker_counter = 0
    
    def mark_template(self, template_text: str) -> Tuple[str, List[TemplateMarker]]:
        """标记模板中的变量和条件表达式"""
        markers = []
        marker_mapping = {}
        
        # 标记变量 {{ }}
        var_pattern = r'\{\{\s*([^\}]+?)\s*\}\}'
        
        def replace_var(match):
            var_content = match.group(1).strip()
            marker_id = f"VAR_{self.marker_counter}"
            self.marker_counter += 1
            
            marker = TemplateMarker(
                marker_id=marker_id,
                marker_type=MarkerType.VARIABLE,
                original_text=match.group(0),
                var_path=var_content
            )
            markers.append(marker)
            marker_mapping[marker_id] = marker
            
            # 返回带标记的版本
            return f"{{MARKER:{marker_id}}}"
        
        marked_text = re.sub(var_pattern, replace_var, template_text)
        
        # 标记条件表达式 {% %}
        cond_pattern = r'\{\%\s*(if|else|endif|for|endfor)\s*([^\%]*)\%\}'
        
        def replace_cond(match):
            cmd = match.group(1).strip()
            expr = match.group(2).strip() if match.group(2) else ""
            marker_id = f"COND_{self.marker_counter}"
            self.marker_counter += 1
            
            marker = TemplateMarker(
                marker_id=marker_id,
                marker_type=MarkerType.CONDITION,
                original_text=match.group(0),
                condition=f"{cmd} {expr}".strip()
            )
            markers.append(marker)
            marker_mapping[marker_id] = marker
            
            return f"{{MARKER:{marker_id}}}"
        
        marked_text = re.sub(cond_pattern, replace_cond, marked_text)
        
        return marked_text, markers


class SmartAnnotationGenerator:
    """智能批注生成器"""
    
    def __init__(self):
        self.W_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    def _wtag(self, name: str) -> str:
        return '{%s}%s' % (self.W_NS['w'], name)
    
    def _find_text_element(self, doc_root, target_text: str):
        """查找包含目标文本的元素"""
        for w_t in doc_root.xpath('.//w:t', namespaces=self.W_NS):
            if w_t.text and target_text in w_t.text:
                return w_t
        return None
    
    def annotate_by_mapping(self, doc_root, position_mappings: List[PositionMapping], comments_root):
        """根据位置映射进行批注"""
        cid = self._collect_max_comment_id(doc_root, comments_root) + 1
        
        for mapping in position_mappings:
            marker = mapping.marker
            trace_item = mapping.trace_item
            
            # 根据trace_item类型构建批注正文
            if isinstance(trace_item, dict):
                table = trace_item.get('table', '')
                field = trace_item.get('field', '')
                value = trace_item.get('value', '')
                var = trace_item.get('var', '')
                pk = trace_item.get('pk', '')
                
                if trace_item.get('_is_condition'):
                    # 条件表达式批注
                    condition = trace_item.get('field', '')
                    body = f"[数据来源] 表={table} 类型=条件表达式 值={value} | 表达式={condition} | 主键={pk}"
                else:
                    # 普通字段批注
                    body = f"[数据来源] 表={table} 字段={field} 值={value} | 变量={var} | 主键={pk}"
            else:
                # TraceItem对象
                table = getattr(trace_item, 'table', '')
                field = getattr(trace_item, 'field', '')
                value = getattr(trace_item, 'value', '')
                var = getattr(trace_item, 'var', '')
                pk = getattr(trace_item, 'pk', '')
                
                body = f"[数据来源] 表={table} 字段={field} 值={value} | 变量={var} | 主键={pk}"
            
            # 查找要批注的文本
            target_text = str(value if hasattr(trace_item, 'value') else trace_item.get('value', ''))
            if not target_text:
                continue
                
            w_t = self._find_text_element(doc_root, target_text)
            if w_t is None:
                continue
            
            # 找到文本所在的run
            w_r = w_t.getparent()
            while w_r is not None and w_r.tag != self._wtag('r'):
                w_r = w_r.getparent()
            
            if w_r is None:
                continue
            
            # 添加批注
            self._append_comment_to_run(doc_root, comments_root, w_r, cid, body)
            cid += 1
    
    def _collect_max_comment_id(self, doc_root, comments_root) -> int:
        """获取最大的评论ID"""
        ids = []
        
        def grab(el):
            for k, v in el.attrib.items():
                if k.endswith('}id') or k == 'id':
                    if str(v).isdigit():
                        ids.append(int(v))
        
        for el in doc_root.iter():
            if el.tag in (self._wtag('commentRangeStart'), self._wtag('commentRangeEnd'), self._wtag('commentReference')):
                grab(el)
        if comments_root is not None:
            for el in comments_root.iter():
                if el.tag == self._wtag('comment'):
                    grab(el)
        return max(ids) if ids else 0
    
    def _append_comment_to_run(self, doc_root, comments_root, w_r, cid: int, body: str):
        """向run添加批注"""
        # 添加评论到comments.xml
        c = etree.SubElement(comments_root, self._wtag('comment'))
        c.set('{%s}id' % self.W_NS['w'], str(cid))
        c.set('{%s}author' % self.W_NS['w'], '智能标注')
        c.set('{%s}initials' % self.W_NS['w'], 'AI')
        p = etree.SubElement(c, self._wtag('p'))
        r = etree.SubElement(p, self._wtag('r'))
        t = etree.SubElement(r, self._wtag('t'))
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = body[:8000] if len(body) > 8000 else body
        
        # 在run周围包装评论范围
        parent = w_r.getparent()
        if parent is not None:
            idx = parent.index(w_r)
            st = etree.Element(self._wtag('commentRangeStart'))
            st.set('{%s}id' % self.W_NS['w'], str(cid))
            en = etree.Element(self._wtag('commentRangeEnd'))
            en.set('{%s}id' % self.W_NS['w'], str(cid))
            ref_r = etree.Element(self._wtag('r'))
            ref_cr = etree.SubElement(ref_r, self._wtag('commentReference'))
            ref_cr.set('{%s}id' % self.W_NS['w'], str(cid))
            
            parent.insert(idx, st)
            parent.insert(idx + 2, en)
            parent.insert(idx + 3, ref_r)


# Jinja2过滤器：trace过滤器
def trace_filter(value, *args, **kwargs):
    """Trace过滤器，用于模板中保留原始值"""
    return value


# 从notebook_cell_sources导入DeepSeekClient（如果存在）
try:
    from notebook_cell_sources import DeepSeekClient
except ImportError:
    try:
        # 如果在主notebook中定义了DeepSeekClient，尝试获取
        import builtins
        if hasattr(builtins, 'DeepSeekClient'):
            DeepSeekClient = builtins.DeepSeekClient
        else:
            # 重新定义DeepSeekClient类（如果之前有定义的话）
            import os
            from jinja2 import Environment, StrictUndefined
            from openai import OpenAI
            from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

            DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
            DEEPSEEK_MODEL = 'deepseek-chat'

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            )
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

                def rewrite(self, text_final: str, prompt_final: str) -> str:
                    messages = [
                        {'role': 'system', 'content': '你是严谨的普惠金融文档助手，能够根据任务说明，生成最终可放入 Word 的正文。'},
                        {'role': 'user', 'content': (
                            '请根据【撰写模板】与【任务说明】生成最终可放入 Word 的正文（不要重复标题）。\n\n'
                            f'【撰写模板】\n{text_final}\n\n【任务说明】\n{prompt_final}'
                        )},
                    ]
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.2,
                    )
                    return (resp.choices[0].message.content or '').strip()
    except ImportError:
        # 定义一个空的客户端类，以防所有导入都失败
        class DeepSeekClient:
            def __init__(self, api_key: str):
                self.api_key = api_key

            def rewrite(self, text_final: str, prompt_final: str) -> str:
                # 如果无法导入真正的客户端，返回原始文本
                return text_final
