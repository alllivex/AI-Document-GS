# RAG知识库功能集成指南

## 概述

本系统为原有的 `word_gen_system_demo_with_marking.ipynb` 智能文档生成系统增加了知识库RAG检索功能。用户可以在Word模板批注中添加 `{kb:知识库名称}` 标记，系统会自动检索相关知识库内容并注入到prompt中，然后交给大模型处理。

## 功能特性

1. **知识库支持**：创建了普惠贷后不良知识库（puhui_daikou_buliang），包含4个Word文档：
   - 不良贷款认定标准与分类
   - 不良贷款处置方式与流程
   - 风险缓释措施与贷后管理
   - 普惠金融特殊政策与案例

2. **灵活的引用语法**：
   - `{kb:知识库名称}`：使用整个prompt作为查询词
   - `{kb:知识库名称:具体查询词}`：使用指定的查询词

3. **智能降级机制**：
   - 主模式：基于sentence-transformers的向量检索
   - 降级模式：基于关键词匹配的检索（网络不可用时自动启用）

4. **无侵入式集成**：通过猴子补丁方式集成到现有系统，无需修改原有代码

## 文件结构

```
knowledge_bases/
├── puhui_daikou_buliang/          # 普惠贷后不良知识库
│   ├── metadata.json             # 知识库元数据
│   ├── 不良贷款认定标准.docx
│   ├── 不良贷款处置方式.docx
│   ├── 风险缓释措施.docx
│   ├── 普惠金融政策案例.docx
│   └── test_kb_retrieval.py      # 知识库测试脚本
│
├── rag_module.py                 # RAG核心模块
├── rag_integration.py            # RAG集成管理器
├── rag_monkey_patch.py           # 猴子补丁模块
├── create_puhui_knowledge_base.py # 知识库创建脚本
├── test_rag_final.py             # 综合测试脚本
├── test_offline_rag.py           # 离线功能测试
├── rag_usage_example.ipynb       # 使用示例Notebook
└── README_RAG_INTEGRATION.md     # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install sentence-transformers numpy scikit-learn python-docx PyPDF2 pyyaml
```

### 2. 创建测试知识库

```bash
python create_puhui_knowledge_base.py
```

### 3. 在Notebook中启用RAG功能

在 `word_gen_system_demo_with_marking.ipynb` 中添加以下代码：

```python
# 在合适的位置添加以下代码
from rag_monkey_patch import setup_rag_for_notebook
setup_rag_for_notebook()
```

### 4. 在Word模板中使用RAG

在Word模板的批注中添加RAG引用：

```
prompt="基于不良率{{data.bad_mom}}，结合{kb:puhui_daikou_buliang}知识库，分析风险状况并给出建议"
```

或者指定具体的查询词：

```
prompt="结合{kb:puhui_daikou_buliang:不良贷款处置方式}，制定具体处置方案"
```

### 5. 运行文档生成

原有的智能文档生成功能会自动识别并处理RAG引用，检索相关知识库内容注入到prompt中。

## 使用示例

详细的使用示例请参考 `rag_usage_example.ipynb`，包含：

1. 环境检查与依赖安装
2. RAG功能设置
3. 基础RAG功能测试
4. Prompt增强测试
5. Word模板示例
6. 完整流程测试
7. 使用指南

## 高级用法

### 扩展知识库

要添加新的知识库，只需在 `knowledge_bases/` 目录下创建新文件夹：

1. 创建知识库目录：`knowledge_bases/新知识库名称/`
2. 创建 `metadata.json` 文件
3. 添加文档文件（支持.docx, .pdf, .txt等格式）

### 手动使用RAG管理器

```python
from rag_integration import create_rag_manager

# 创建RAG管理器
rag_manager = create_rag_manager()

# 搜索知识库
results = rag_manager.search_knowledge_base('puhui_daikou_buliang', '不良贷款', top_k=3)

# 手动增强prompt
enhanced_prompt, used_rag = rag_manager.enhance_prompt_with_rag(original_prompt, context)
```

### 性能优化

- **向量模型选择**：默认使用 `all-MiniLM-L6-v2`，中文环境会尝试加载 `paraphrase-multilingual-MiniLM-L12-v2`
- **分块大小**：默认512字符，可在 `rag_module.py` 中调整
- **检索数量**：默认top_k=3，可根据需要调整

## 故障排除

### 1. 网络问题

sentence-transformers需要下载模型，如果网络不通：
- 使用离线模式（关键词匹配）
- 配置网络代理
- 使用预先下载的模型文件

### 2. 知识库加载失败

- 检查 `knowledge_bases/` 目录结构
- 确保 `metadata.json` 文件存在且格式正确
- 确保文档文件可正常读取

### 3. RAG增强无效

- 检查 `{kb:}` 标记格式是否正确
- 检查知识库名称是否匹配
- 查看控制台输出了解处理过程

### 4. 依赖安装问题

```bash
# 如果pip安装失败，尝试指定镜像源
pip install sentence-transformers -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者使用conda
conda install -c conda-forge sentence-transformers
```

## 设计原理

### 猴子补丁机制

`rag_monkey_patch.py` 通过替换以下函数实现无侵入式集成：

1. `render_prompt()`：增强prompt渲染，支持 `{kb:}` 标记
2. `apply_ai_by_markers()`：在AI调用前进行RAG增强
3. `finalize_rendered_document()`：支持RAG管理器参数
4. `run_smart_document_generation()`：添加RAG启用参数

### 双模检索系统

1. **向量检索模式**：基于sentence-transformers的语义相似度检索
2. **关键词匹配模式**：基于简单关键词匹配的降级方案

### 智能降级

系统会检测向量模型的可用性，如果模型加载失败或网络不可用，会自动降级到关键词匹配模式，确保基本功能可用。

## 测试验证

系统包含完整的测试套件：

1. `test_rag_final.py`：综合功能测试
2. `test_offline_rag.py`：离线功能测试
3. `knowledge_bases/puhui_daikou_buliang/test_kb_retrieval.py`：知识库检索测试

运行测试：

```bash
python test_rag_final.py
python test_offline_rag.py
```

## 兼容性说明

- **向后兼容**：不修改原有系统代码，通过猴子补丁实现功能增强
- **最小侵入**：新增文件与原有系统独立，便于维护和升级
- **渐进增强**：如果RAG功能不可用，原有系统功能不受影响

## 后续扩展

1. **支持更多文件格式**：扩展文档解析器支持更多格式
2. **增加缓存机制**：缓存向量嵌入和检索结果提升性能
3. **优化检索算法**：支持BM25等传统检索算法
4. **增强UI界面**：提供知识库管理和配置界面
5. **支持在线知识库**：连接外部API或数据库作为知识源

---

**注意**：这是一个演示系统，实际生产使用时可能需要根据具体需求进行调整和优化。知识库内容和检索算法可根据业务场景进行定制。