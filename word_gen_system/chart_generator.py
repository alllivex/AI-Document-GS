import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
import io

# 设置中文字体（防止乱码）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class ChartGenerator:
    """
    图表生成器：根据数据特征自动选择图表类型并生成
    """
    
    # 图表类型映射
    CHART_TYPES = {
        'bar': '条形图',
        'line': '折线图',
        'pie': '饼图',
        'scatter': '散点图',
        'hist': '直方图',
        'box': '箱线图',
        'heatmap': '热力图'
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path.cwd() / 'output' / 'charts'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def auto_select_chart_type(self, df: pd.DataFrame, x_col: Optional[str] = None, 
                               y_col: Optional[str] = None) -> str:
        """
        根据数据特征自动推荐图表类型
        
        Returns:
            推荐的图表类型 ('bar', 'line', 'pie', 'scatter', 'hist')
        """
        if df.empty:
            return 'bar'
            
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        
        # 如果指定了列
        if x_col and y_col:
            x_dtype = df[x_col].dtype
            y_dtype = df[y_col].dtype
            
            if x_dtype in ['object', 'category'] and y_dtype in ['int64', 'float64']:
                return 'bar'  # 分类 vs 数值 -> 条形图
            elif x_dtype in ['int64', 'float64'] and y_dtype in ['int64', 'float64']:
                return 'scatter'  # 数值 vs 数值 -> 散点图
            elif pd.api.types.is_datetime64_any_dtype(df[x_col]):
                return 'line'  # 时间序列 -> 折线图
                
        # 自动推断
        if len(num_cols) >= 2:
            return 'scatter'  # 多个数值列 -> 散点图
        elif len(cat_cols) >= 1 and len(num_cols) >= 1:
            return 'bar'  # 有分类和数值 -> 条形图
        elif len(num_cols) == 1:
            return 'hist'  # 单个数值列 -> 直方图
        elif len(cat_cols) == 1 and len(df[cat_cols[0]].unique()) <= 10:
            return 'pie'  # 单个分类列且类别少 -> 饼图
            
        return 'bar'  # 默认
    
    def generate_chart(self, df: pd.DataFrame, chart_type: str, 
                       x_col: Optional[str] = None, y_col: Optional[str] = None,
                       title: str = "数据分析图表", 
                       output_filename: Optional[str] = None) -> str:
        """
        生成图表并保存
        
        Args:
            df: 数据框
            chart_type: 图表类型 ('bar', 'line', 'pie', 'scatter', 'hist', 'box')
            x_col: X 轴列名
            y_col: Y 轴列名
            title: 图表标题
            output_filename: 输出文件名（不含路径）
            
        Returns:
            生成的图表文件路径
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 自动选择列（如果未指定）
        if not x_col or not y_col:
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
            
            if chart_type in ['bar', 'pie'] and cat_cols:
                x_col = cat_cols[0]
                y_col = num_cols[0] if num_cols else None
            elif chart_type in ['scatter', 'line'] and len(num_cols) >= 2:
                x_col = num_cols[0]
                y_col = num_cols[1]
            elif chart_type == 'hist' and num_cols:
                y_col = num_cols[0]
        
        # 绘制图表
        try:
            if chart_type == 'bar':
                if x_col and y_col:
                    # 分组聚合
                    plot_data = df.groupby(x_col)[y_col].sum().reset_index()
                    ax.bar(plot_data[x_col].astype(str), plot_data[y_col])
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                else:
                    df.select_dtypes(include=['number']).iloc[:10].plot(kind='bar', ax=ax)
                    
            elif chart_type == 'line':
                if x_col and y_col:
                    plot_data = df.sort_values(x_col).groupby(x_col)[y_col].mean().reset_index()
                    ax.plot(plot_data[x_col], plot_data[y_col], marker='o')
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                else:
                    df.select_dtypes(include=['number']).iloc[:20].plot(kind='line', ax=ax)
                    
            elif chart_type == 'pie':
                if x_col and y_col:
                    plot_data = df.groupby(x_col)[y_col].sum()
                    if len(plot_data) > 10:
                        plot_data = plot_data.nlargest(10)
                    ax.pie(plot_data.values, labels=plot_data.index.astype(str), autopct='%1.1f%%')
                else:
                    # 默认使用第一个分类列
                    cat_cols = df.select_dtypes(include=['object', 'category']).columns
                    if len(cat_cols) > 0:
                        counts = df[cat_cols[0]].value_counts().head(10)
                        ax.pie(counts.values, labels=counts.index.astype(str), autopct='%1.1f%%')
                        
            elif chart_type == 'scatter':
                if x_col and y_col:
                    ax.scatter(df[x_col], df[y_col], alpha=0.6)
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                else:
                    num_cols = df.select_dtypes(include=['number']).columns
                    if len(num_cols) >= 2:
                        ax.scatter(df[num_cols[0]], df[num_cols[1]], alpha=0.6)
                        ax.set_xlabel(num_cols[0])
                        ax.set_ylabel(num_cols[1])
                        
            elif chart_type == 'hist':
                col = y_col or df.select_dtypes(include=['number']).columns[0]
                ax.hist(df[col].dropna(), bins=20, edgecolor='black', alpha=0.7)
                ax.set_xlabel(col)
                ax.set_ylabel('频数')
                
            elif chart_type == 'box':
                col = y_col or df.select_dtypes(include=['number']).columns[0]
                ax.boxplot(df[col].dropna())
                ax.set_ylabel(col)
            
            ax.set_title(title)
            plt.tight_layout()
            
            # 保存文件
            if not output_filename:
                output_filename = f"chart_{chart_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            output_path = self.output_dir / output_filename
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            print(f"✓ 图表已生成：{output_path}")
            return str(output_path)
            
        except Exception as e:
            plt.close(fig)
            raise RuntimeError(f"图表生成失败：{str(e)}")
    
    def generate_chart_to_buffer(self, df: pd.DataFrame, chart_type: str,
                                 x_col: Optional[str] = None, y_col: Optional[str] = None,
                                 title: str = "数据分析图表") -> bytes:
        """
        生成图表到内存缓冲区（用于直接插入文档或返回二进制数据）
        
        Returns:
            图片的二进制数据
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 复用 generate_chart 的逻辑进行绘制（简化版）
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        
        if chart_type == 'bar' and cat_cols and num_cols:
            x_col = x_col or cat_cols[0]
            y_col = y_col or num_cols[0]
            plot_data = df.groupby(x_col)[y_col].sum().reset_index()
            ax.bar(plot_data[x_col].astype(str), plot_data[y_col])
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
        elif chart_type == 'hist' and num_cols:
            col = y_col or num_cols[0]
            ax.hist(df[col].dropna(), bins=20, edgecolor='black', alpha=0.7)
            ax.set_xlabel(col)
        elif chart_type == 'scatter' and len(num_cols) >= 2:
            x_col = x_col or num_cols[0]
            y_col = y_col or num_cols[1]
            ax.scatter(df[x_col], df[y_col], alpha=0.6)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
        else:
            # 默认条形图
            if num_cols:
                df[num_cols[0]].iloc[:10].plot(kind='bar', ax=ax)
        
        ax.set_title(title)
        plt.tight_layout()
        
        # 保存到缓冲区
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

# 全局单例
_generator_instance: Optional[ChartGenerator] = None

def get_chart_generator(output_dir: Optional[Path] = None) -> ChartGenerator:
    """获取或创建图表生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ChartGenerator(output_dir)
    return _generator_instance