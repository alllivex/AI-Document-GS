import pandas as pd
import os
from typing import Dict, Optional, List

class ChineseNameMapper:
    """
    中文名称映射器：处理模板文件名、表名、字段名的中英文映射。
    """
    
    def __init__(self, entity_schema_path: str, template_relation_path: str):
        """
        初始化映射器
        :param entity_schema_path: entity_schema.xlsx 路径
        :param template_relation_path: template_relation.xlsx 路径
        """
        self.entity_schema_df = pd.read_excel(entity_schema_path)
        self.template_relation_df = pd.read_excel(template_relation_path)
        
        # 构建映射字典
        self._build_mappings()

    def _build_mappings(self):
        """构建内部映射字典"""
        # 1. 表名映射: English -> Chinese
        if 'table_name_chinese' in self.entity_schema_df.columns:
            # 去除空值，建立映射
            valid_rows = self.entity_schema_df.dropna(subset=['table_name', 'table_name_chinese'])
            self.en_to_cn_table_map = dict(zip(valid_rows['table_name'], valid_rows['table_name_chinese']))
            self.cn_to_en_table_map = dict(zip(valid_rows['table_name_chinese'], valid_rows['table_name']))
        else:
            self.en_to_cn_table_map = {}
            self.cn_to_en_table_map = {}

        # 2. 字段名映射: (Table_EN, Field_EN) -> Field_CN
        # 注意：字段名通常依赖于所属表，所以用元组做Key
        self.field_en_to_cn_map = {}
        self.field_cn_to_en_map = {}
        
        if 'field_name_chinese' in self.entity_schema_df.columns:
            valid_fields = self.entity_schema_df.dropna(subset=['table_name', 'field_name', 'field_name_chinese'])
            for _, row in valid_fields.iterrows():
                table_en = row['table_name']
                field_en = row['field_name']
                field_cn = row['field_name_chinese']
                
                key_en = (table_en, field_en)
                key_cn = (table_en, field_cn) # 假设同一表内中文字段名唯一
                
                self.field_en_to_cn_map[key_en] = field_cn
                self.field_cn_to_en_map[key_cn] = field_en

        # 3. 模板关系映射: Template_File -> List[Table_EN] & List[Table_CN]
        # 用于根据模板找到关联的数据表
        self.template_tables_map = {} # Key: template_file_name (without ext), Value: List[table_name_en]
        
        # 确保 template_relation 中有必要的列
        req_cols = ['template_file_name', 'table_name']
        if all(col in self.template_relation_df.columns for col in req_cols):
             for _, row in self.template_relation_df.iterrows():
                 tpl_name = row['template_file_name']
                 tbl_en = row['table_name']
                 
                 if tpl_name not in self.template_tables_map:
                     self.template_tables_map[tpl_name] = []
                 self.template_tables_map[tpl_name].append(tbl_en)

    def get_english_table_name(self, chinese_table_name: str) -> Optional[str]:
        """根据中文表名获取英文表名"""
        return self.cn_to_en_table_map.get(chinese_table_name)

    def get_chinese_table_name(self, english_table_name: str) -> Optional[str]:
        """根据英文表名获取中文表名"""
        return self.en_to_cn_table_map.get(english_table_name)

    def get_english_field_name(self, table_en: str, chinese_field_name: str) -> Optional[str]:
        """根据表英文名和字段中文名获取字段英文名"""
        key = (table_en, chinese_field_name)
        return self.field_cn_to_en_map.get(key)

    def get_chinese_field_name(self, table_en: str, english_field_name: str) -> Optional[str]:
        """根据表英文名和字段英文名获取字段中文名"""
        key = (table_en, english_field_name)
        return self.field_en_to_cn_map.get(key)

    def resolve_template_file(self, templates_dir: str, template_identifier: str) -> Optional[str]:
        """
        根据标识符（可能是中文表名、英文模板名或中文模板名）解析实际的模板文件路径
        策略：
        1. 如果 identifier 直接对应 templates 目录下的某个 .docx 文件，直接返回。
        2. 如果 identifier 是中文表名，尝试在 template_relation 中查找关联的模板。
           (注：通常 template_relation 是通过 template_file_name 关联的。这里假设用户可能输入中文表名想生成对应模板，
           或者 template_file_name 本身就是中文。为了简化，我们主要支持 template_file_name 为中文的情况)
        
        更通用的策略：遍历 templates 目录，匹配文件名（不含扩展名）与 identifier。
        """
        if not os.path.exists(templates_dir):
            return None
            
        # 清理标识符，去除可能的扩展名
        clean_id = template_identifier.replace('.docx', '').replace('.DOCX', '')
        
        # 遍历目录查找匹配的文件
        for filename in os.listdir(templates_dir):
            if filename.lower().endswith('.docx'):
                name_without_ext = os.path.splitext(filename)[0]
                # 完全匹配
                if name_without_ext == clean_id:
                    return os.path.join(templates_dir, filename)
                
                # 模糊匹配：如果 identifier 是中文表名，检查该模板是否关联了这个表
                # 这需要反向查找 template_relation，比较耗时，暂不启用，优先依靠文件名匹配
        
        return None

    def get_tables_for_template(self, template_file_name: str) -> List[str]:
        """
        根据模板文件名（不含扩展名）获取关联的英文表名列表
        """
        clean_name = template_file_name.replace('.docx', '').replace('.DOCX', '')
        return self.template_tables_map.get(clean_name, [])