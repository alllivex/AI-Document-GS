"""
RAG 知识库模块 - 银行普惠贷后领域
功能：知识库加载、向量化索引、语义检索、Prompt 增强
"""
import pandas as pd
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

# 尝试导入向量检索相关库，若未安装则降级为关键词匹配
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("警告：未安装 sentence-transformers，将使用关键词匹配模式。请运行：pip install sentence-transformers")

@dataclass
class KnowledgeItem:
    """知识库条目"""
    kb_id: str
    category: str  # 分类：政策/产品/风险/流程
    title: str
    content: str
    keywords: List[str]
    source: str  # 来源文档
    effective_date: Optional[str] = None
    embedding: Optional[Any] = None  # 向量嵌入


class RAGKnowledgeBase:
    """RAG 知识库管理器"""
    
    def __init__(self, kb_excel_path: Optional[Path] = None, model_name: str = "paraphrase-MiniLM-L6-v2"):
        """
        初始化知识库
        
        Args:
            kb_excel_path: 知识库 Excel 文件路径
            model_name: 句子嵌入模型名称
        """
        self.kb_items: List[KnowledgeItem] = []
        self.kb_index: Dict[str, KnowledgeItem] = {}
        self.embeddings_matrix = None
        self.model = None
        
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer(model_name)
                print(f"已加载嵌入模型：{model_name}")
            except Exception as e:
                print(f"加载模型失败：{e}，将使用关键词匹配")
                self.model = None
        
        if kb_excel_path and kb_excel_path.exists():
            self.load_from_excel(kb_excel_path)
    
    def load_from_excel(self, excel_path: Path) -> int:
        """
        从 Excel 加载知识库
        
        Args:
            excel_path: 知识库 Excel 文件
            
        Returns:
            加载的条目数量
        """
        df = pd.read_excel(excel_path)
        required_cols = {'kb_id', 'category', 'title', 'content', 'keywords', 'source'}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"知识库 Excel 缺少列：{missing}")
        
        count = 0
        for _, row in df.iterrows():
            kb_id = str(row['kb_id']).strip()
            if not kb_id or kb_id in self.kb_index:
                continue
                
            keywords_str = str(row.get('keywords', ''))
            keywords = [k.strip() for k in re.split(r'[,,]', keywords_str) if k.strip()]
            
            item = KnowledgeItem(
                kb_id=kb_id,
                category=str(row.get('category', 'general')).strip(),
                title=str(row.get('title', '')).strip(),
                content=str(row.get('content', '')).strip(),
                keywords=keywords,
                source=str(row.get('source', '')).strip(),
                effective_date=str(row.get('effective_date', '')) if pd.notna(row.get('effective_date')) else None
            )
            
            self.kb_items.append(item)
            self.kb_index[kb_id] = item
            count += 1
        
        print(f"已加载 {count} 条知识库条目")
        
        # 构建向量索引
        if self.model and self.kb_items:
            self._build_embeddings()
        
        return count
    
    def _build_embeddings(self) -> None:
        """为所有知识库条目构建向量嵌入"""
        if not self.model or not self.kb_items:
            return
        
        texts = [f"{item.title} {item.content}" for item in self.kb_items]
        try:
            self.embeddings_matrix = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            print(f"已构建 {len(self.kb_items)} 条向量索引")
        except Exception as e:
            print(f"构建向量索引失败：{e}")
            self.embeddings_matrix = None
    
    def retrieve(self, query: str, top_k: int = 3, category_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        检索相关知识
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            category_filter: 分类过滤列表
            
        Returns:
            检索结果列表，每项包含 kb_id, title, content, score, source
        """
        if not self.kb_items:
            return []
        
        # 分类过滤
        candidates = self.kb_items
        if category_filter:
            candidates = [item for item in self.kb_items if item.category in category_filter]
        
        if not candidates:
            return []
        
        # 向量检索或关键词检索
        if self.model and self.embeddings_matrix is not None and HAS_SENTENCE_TRANSFORMERS:
            results = self._vector_search(query, candidates, top_k)
        else:
            results = self._keyword_search(query, candidates, top_k)
        
        return results
    
    def _vector_search(self, query: str, candidates: List[KnowledgeItem], top_k: int) -> List[Dict[str, Any]]:
        """向量相似度搜索"""
        try:
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
            
            # 获取候选项在原始矩阵中的索引
            candidate_indices = [self.kb_items.index(item) for item in candidates]
            candidate_embeddings = self.embeddings_matrix[candidate_indices]
            
            # 计算余弦相似度
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity([query_embedding], candidate_embeddings)[0]
            
            # 排序
            sorted_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
            
            results = []
            for idx in sorted_indices:
                if similarities[idx] < 0.1:  # 阈值过滤
                    continue
                item = candidates[idx]
                results.append({
                    'kb_id': item.kb_id,
                    'title': item.title,
                    'content': item.content,
                    'score': float(similarities[idx]),
                    'source': item.source,
                    'category': item.category
                })
            
            return results
        except Exception as e:
            print(f"向量检索失败：{e}，降级为关键词检索")
            return self._keyword_search(query, candidates, top_k)
    
    def _keyword_search(self, query: str, candidates: List[KnowledgeItem], top_k: int) -> List[Dict[str, Any]]:
        """关键词匹配搜索（降级方案）"""
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        scored_items = []
        for item in candidates:
            score = 0
            text_lower = f"{item.title} {item.content} {' '.join(item.keywords)}".lower()
            
            # 精确匹配标题
            if query_lower in item.title.lower():
                score += 5
            
            # 关键词匹配
            for word in query_words:
                if len(word) < 2:
                    continue
                if word in text_lower:
                    score += 1
                for kw in item.keywords:
                    if kw.lower() == word:
                        score += 2
            
            if score > 0:
                scored_items.append((score, item))
        
        # 排序
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, item in scored_items[:top_k]:
            results.append({
                'kb_id': item.kb_id,
                'title': item.title,
                'content': item.content,
                'score': float(score),
                'source': item.source,
                'category': item.category
            })
        
        return results
    
    def format_context_for_prompt(self, results: List[Dict[str, Any]], max_length: int = 1000) -> str:
        """
        格式化检索结果为 Prompt 上下文
        
        Args:
            results: 检索结果列表
            max_length: 最大字符长度
            
        Returns:
            格式化的知识上下文字符串
        """
        if not results:
            return "未检索到相关知识库内容。"
        
        parts = []
        current_length = 0
        
        for i, r in enumerate(results, 1):
            segment = f"[{i}] {r['title']} (来源：{r['source']})\n{r['content'][:300]}\n"
            if current_length + len(segment) > max_length:
                break
            parts.append(segment)
            current_length += len(segment)
        
        return "\n".join(parts)


class RAGPromptEnhancer:
    """RAG Prompt 增强器 - 在调用大模型前注入检索知识"""
    
    def __init__(self, knowledge_base: RAGKnowledgeBase, categories: Optional[List[str]] = None, top_k: int = 3):
        """
        初始化增强器
        
        Args:
            knowledge_base: 知识库实例
            categories: 默认检索的分类过滤
            top_k: 默认检索结果数量
        """
        self.kb = knowledge_base
        self.categories = categories
        self.top_k = top_k
    
    def enhance_prompt(self, original_prompt: str, context_data: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        增强 Prompt：提取关键信息→检索知识→注入上下文
        
        Args:
            original_prompt: 原始 Prompt 模板
            context_data: 渲染上下文（用于提取关键词）
            
        Returns:
            (增强后的 Prompt, 检索结果列表)
        """
        # 从原始 Prompt 和上下文中提取检索关键词
        query_keywords = self._extract_query_keywords(original_prompt, context_data)
        
        if not query_keywords:
            return original_prompt, []
        
        # 执行检索
        query_text = " ".join(query_keywords)
        results = self.kb.retrieve(query_text, top_k=self.top_k, category_filter=self.categories)
        
        if not results:
            return original_prompt, []
        
        # 格式化知识上下文
        knowledge_context = self.kb.format_context_for_prompt(results)
        
        # 构建增强 Prompt
        enhanced_prompt = (
            f"【相关知识库参考】\n{knowledge_context}\n\n"
            f"【原始任务】\n{original_prompt}\n\n"
            f"请结合上述知识库内容，完成【原始任务】中的要求。"
        )
        
        return enhanced_prompt, results
    
    def _extract_query_keywords(self, prompt: str, context: Dict[str, Any]) -> List[str]:
        """从 Prompt 和上下文中提取检索关键词"""
        keywords = set()
        
        # 从 Prompt 中提取名词短语（简化版）
        words = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', prompt)
        for w in words:
            if w in ['基于', '分析', '给出', '建议', '请', '的', '了', '和']:
                continue
            keywords.add(w)
        
        # 从上下文数据中提取关键值
        for key, value in context.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, str) and len(v) > 1:
                        # 删除：keywords.add(v[:10])  # 取前 10 个字符
                        # 改进：提取更有意义的关键词而非简单截取
                        if len(v) <= 20:
                            keywords.add(v)
                        else:
                            # 尝试提取关键实体（如支行名、产品名等）
                            extracted = re.findall(r'[\u4e00-\u9fa5]{2,6}', v)[:3]
                            keywords.update(extracted)
            elif isinstance(value, str) and len(value) > 2:
                if len(value) <= 20:
                    keywords.add(value)
                else:
                    extracted = re.findall(r'[\u4e00-\u9fa5]{2,6}', value)[:3]
                    keywords.update(extracted)
        
        # 添加领域特定关键词
        domain_keywords = ['不良', '逾期', '风险', '贷款', '普惠', '清偿', '抵押', '催收', '续贷', '容忍度']
        for dk in domain_keywords:
            if dk in prompt or dk in str(context):
                keywords.add(dk)
        
        # 从上下文中提取数值相关的关键词（如不良率、抵押率等）
        if 'npl_ratio' in str(context).lower() or '不良' in str(context):
            keywords.add('不良率')
        if 'mortgage_ratio' in str(context).lower() or '抵押' in str(context):
            keywords.add('抵押率')
        if 'overdue' in str(context).lower() or '逾期' in str(context):
            keywords.add('逾期')
        
        return list(keywords)[:30]  # 适当增加关键词数量限制


# 便捷函数
def init_rag_system(kb_excel_path: Path, categories: Optional[List[str]] = None) -> Tuple[RAGKnowledgeBase, RAGPromptEnhancer]:
    """
    初始化 RAG 系统
    
    Args:
        kb_excel_path: 知识库 Excel 路径
        categories: 默认检索分类
        
    Returns:
        (知识库实例，增强器实例)
    """
    kb = RAGKnowledgeBase(kb_excel_path)
    enhancer = RAGPromptEnhancer(kb, categories=categories)
    return kb, enhancer


# 新增：便捷测试函数
def test_rag_end_to_end(kb_excel_path: Path, test_queries: List[str] = None) -> None:
    """
    端到端测试 RAG 系统
    
    Args:
        kb_excel_path: 知识库 Excel 路径
        test_queries: 测试查询列表
    """
    if test_queries is None:
        test_queries = [
            "不良率上升如何处理",
            "法人 e 抵产品额度是多少",
            "逾期 90 天以上催收流程",
            "小微企业续贷政策"
        ]
    
    print("=== RAG 系统端到端测试 ===\n")
    kb, enhancer = init_rag_system(kb_excel_path, categories=['政策', '风险', '产品'])
    
    for query in test_queries:
        print(f"查询：{query}")
        results = kb.retrieve(query, top_k=2)
        if results:
            for i, r in enumerate(results, 1):
                print(f"  [{i}] {r['title']} (得分：{r['score']:.2f}, 分类：{r['category']})")
                print(f"      来源：{r['source']}")
        else:
            print("  未找到相关知识")
        print()
