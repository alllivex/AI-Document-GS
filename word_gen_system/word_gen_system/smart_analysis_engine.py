import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from ydata_profiling import ProfileReport
import warnings

# 忽略部分警告
warnings.filterwarnings('ignore')

from dataset_manager import get_dataset_manager, DatasetManager
from chart_generator import get_chart_generator, ChartGenerator
from analysis_prompt_parser import get_analysis_parser, AnalysisRequest, parse_analysis_requests

class SmartAnalysisEngine:
    """
    智能分析引擎：集成 ydata-profiling，支持多数据集分析和图表生成
    """
    
    def __init__(self, data_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.cwd() / 'data'
        self.output_dir = (output_dir or Path.cwd() / 'output') / 'analysis_reports'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.dataset_manager = get_dataset_manager(self.data_dir)
        self.chart_generator = get_chart_generator(self.output_dir)
        self.parser = get_analysis_parser()
        
        print("✓ 智能分析引擎已初始化")
        print(f"  - 数据目录：{self.data_dir}")
        print(f"  - 输出目录：{self.output_dir}")
    
    def register_dataset(self, name: str, file_path: str) -> pd.DataFrame:
        """注册数据集"""
        return self.dataset_manager.load_dataset(name, file_path)
    
    def analyze_dataset(self, dataset_name: str, 
                        output_filename: Optional[str] = None) -> str:
        """
        使用 ydata-profiling 生成详细分析报告
        
        Args:
            dataset_name: 数据集名称
            output_filename: 输出 HTML 文件名
            
        Returns:
            生成的报告文件路径
        """
        df = self.dataset_manager.get_dataset(dataset_name)
        
        print(f"正在分析数据集 '{dataset_name}' ({len(df)} 行)...")
        
        # 生成 ProfileReport
        profile = ProfileReport(
            df,
            title=f"{dataset_name} 数据分析报告",
            minimal=False,
            progress_bar=True
        )
        
        if not output_filename:
            output_filename = f"report_{dataset_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        output_path = self.output_dir / output_filename
        profile.to_file(output_path)
        
        print(f"✓ 分析报告已生成：{output_path}")
        return str(output_path)
    
    def execute_request(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        执行单个分析请求
        
        Args:
            request: 分析请求对象
            
        Returns:
            执行结果字典
        """
        result = {
            'dataset': request.dataset_name,
            'prompt': request.prompt,
            'success': False,
            'report_path': None,
            'chart_path': None,
            'error': None
        }
        
        try:
            # 获取数据
            df = self.dataset_manager.get_dataset(request.dataset_name)
            
            # 如果有图表需求
            if request.chart_type:
                chart_path = self.chart_generator.generate_chart(
                    df=df,
                    chart_type=request.chart_type,
                    x_col=request.chart_x_col,
                    y_col=request.chart_y_col,
                    title=request.chart_title or "分析图表"
                )
                result['chart_path'] = chart_path
            
            # 如果没有指定图表类型但有分析提示，生成完整报告
            elif request.prompt and not request.chart_type:
                report_path = self.analyze_dataset(
                    request.dataset_name,
                    output_filename=f"report_{request.dataset_name}_{hash(request.prompt) & 0xFFFFFFFF}.html"
                )
                result['report_path'] = report_path
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            print(f"✗ 执行请求失败：{e}")
        
        return result
    
    def process_comments(self, comments: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理批注列表
        
        Args:
            comments: 批注文本列表
            
        Returns:
            所有请求的执行结果列表
        """
        all_requests = []
        
        # 解析所有批注
        for comment in comments:
            requests = self.parser.parse_text(comment)
            all_requests.extend(requests)
        
        if not all_requests:
            print("未检测到分析请求标记")
            return []
        
        print(f"检测到 {len(all_requests)} 个分析请求")
        
        # 执行所有请求
        results = []
        for req in all_requests:
            print(f"\n处理请求：数据集={req.dataset_name}, 类型={'图表' if req.chart_type else '分析报告'}")
            result = self.execute_request(req)
            results.append(result)
        
        return results
    
    def run_interactive(self):
        """交互式运行模式"""
        print("\n=== 智能分析引擎 - 交互模式 ===")
        print("可用命令:")
        print("  register <name> <file>  - 注册数据集")
        print("  analyze <name>          - 生成分析报告")
        print("  list                    - 列出已注册数据集")
        print("  quit                    - 退出")
        
        while True:
            cmd = input("\n请输入命令：").strip()
            if not cmd:
                continue
                
            parts = cmd.split()
            command = parts[0].lower()
            
            if command == 'quit':
                break
            elif command == 'list':
                datasets = self.dataset_manager.list_datasets()
                if datasets:
                    print("已注册数据集:")
                    for ds in datasets:
                        info = self.dataset_manager.get_dataset_info(ds)
                        print(f"  - {ds}: {info['rows']} 行，{info['columns']}")
                else:
                    print("暂无已注册数据集")
            elif command == 'register' and len(parts) >= 3:
                name = parts[1]
                file_path = ' '.join(parts[2:])
                try:
                    self.register_dataset(name, file_path)
                except Exception as e:
                    print(f"注册失败：{e}")
            elif command == 'analyze' and len(parts) >= 2:
                name = parts[1]
                try:
                    self.analyze_dataset(name)
                except Exception as e:
                    print(f"分析失败：{e}")
            else:
                print("未知命令或参数不足")

# 全局单例
_engine_instance: Optional[SmartAnalysisEngine] = None

def get_analysis_engine(data_dir: Optional[Path] = None, 
                        output_dir: Optional[Path] = None) -> SmartAnalysisEngine:
    """获取或创建分析引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SmartAnalysisEngine(data_dir, output_dir)
    return _engine_instance

def init_smart_analysis():
    """便捷初始化函数"""
    engine = get_analysis_engine()
    print("\n智能分析引擎就绪！")
    print("使用示例:")
    print("  1. 注册数据：engine.register_dataset('loan_data', 'loan_summary.xlsx')")
    print("  2. 生成报告：engine.analyze_dataset('loan_data')")
    print("  3. 处理批注：engine.process_comments(['{analysis:loan_data:分析贷款趋势}'])")
    return engine