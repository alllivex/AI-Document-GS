import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class AnalysisRequest:
    """分析请求对象"""
    dataset_name: str
    prompt: str
    chart_type: Optional[str] = None
    chart_x_col: Optional[str] = None
    chart_y_col: Optional[str] = None
    chart_title: Optional[str] = None

class AnalysisPromptParser:
    """
    分析提示词解析器：解析 Word 批注中的特殊标记
    
    支持的标记格式：
    - {analysis:数据集名：提示词内容}
    - {chart:图表类型：数据集名：X 列：Y 列：标题}
    - {chart:bar:loan_data:branch_name:loan_amount:各支行贷款分布}
    """
    
    # 正则表达式模式
    ANALYSIS_PATTERN = r'\{analysis:([^:]+):([^}]+)\}'
    CHART_PATTERN = r'\{chart:([^:]+):([^:]+):([^:]+):([^:]+)(?::([^}]+))?\}'
    
    def parse_text(self, text: str) -> List[AnalysisRequest]:
        """
        从文本中解析分析请求
        
        Args:
            text: 包含标记的文本（如批注内容）
            
        Returns:
            分析请求列表
        """
        requests = []
        
        # 解析 analysis 标记
        for match in re.finditer(self.ANALYSIS_PATTERN, text):
            dataset_name = match.group(1).strip()
            prompt = match.group(2).strip()
            
            requests.append(AnalysisRequest(
                dataset_name=dataset_name,
                prompt=prompt
            ))
        
        # 解析 chart 标记
        for match in re.finditer(self.CHART_PATTERN, text):
            chart_type = match.group(1).strip()
            dataset_name = match.group(2).strip()
            x_col = match.group(3).strip()
            y_col = match.group(4).strip()
            title = match.group(5).strip() if match.group(5) else f"{chart_type}图表"
            
            requests.append(AnalysisRequest(
                dataset_name=dataset_name,
                prompt=f"生成{chart_type}图表",
                chart_type=chart_type,
                chart_x_col=x_col,
                chart_y_col=y_col,
                chart_title=title
            ))
        
        return requests
    
    def parse_comment(self, comment_text: str) -> List[AnalysisRequest]:
        """
        专门解析批注文本
        
        Args:
            comment_text: 批注内容
            
        Returns:
            分析请求列表
        """
        return self.parse_text(comment_text)
    
    @staticmethod
    def extract_datasets_from_requests(requests: List[AnalysisRequest]) -> List[str]:
        """从请求列表中提取所有涉及的数据集名称"""
        datasets = set()
        for req in requests:
            datasets.add(req.dataset_name)
        return list(datasets)

# 全局单例
_parser_instance: Optional[AnalysisPromptParser] = None

def get_analysis_parser() -> AnalysisPromptParser:
    """获取或创建解析器单例"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = AnalysisPromptParser()
    return _parser_instance

def parse_analysis_requests(text: str) -> List[AnalysisRequest]:
    """便捷函数：解析文本中的分析请求"""
    parser = get_analysis_parser()
    return parser.parse_text(text)