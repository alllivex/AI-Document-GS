# AI智能文档生成系统 MVP 产品需求文档

> 版本：MVP V1.0\
> 定位：Excel业务数据 + Word模板批量生成文档，并提供在线可视化溯源与本地下载\
> 状态：建议开发版\
> 核心原则：先跑通"配置---校验---生成---溯源---下载"最小闭环，不做审核流、不做在线编辑、不做RAG知识库、不做复杂权限体系。

## 一、产品概述

### 1.1 产品定义

AI智能文档生成系统是一款面向金融业务场景的"结构化数据 → Word文档"自动生成工具。

系统以Excel业务数据为输入，以Word模板为文档载体，通过模板变量渲染、条件判断、表格循环、AI段落生成和可视化溯源能力，实现批量生成规范Word文档，并支持用户在Web界面中查看每个关键数据值对应的Excel来源，最终下载干净的Word文档到本地进行后续审阅、修改和流转。

MVP阶段的核心目标不是做完整文档协同平台，而是先完成以下闭环：

> 上传Excel数据 → 选择Word模板 → 系统校验 → 批量生成Word → 在线查看溯源 → 下载Word。

### 1.2 MVP核心目标

1.  **提升文档生成效率**\
    用户无需手工复制粘贴Excel字段到Word模板，系统根据模板变量自动批量生成文档。

2.  **降低数据核对成本**\
    用户可在Web页面点击文档中的数据值，查看该值来自哪个Excel文件、哪张表、哪一行、哪个字段。

3.  **保证Word文档干净可用**\
    最终下载的Word文档不包含溯源批注、不包含系统标记、不污染文档结构。

4.  **复用旧代码中已验证的核心能力**\
    MVP优先复用旧代码中已跑通的配置加载、数据加载、context构建、docxtpl渲染、AI prompt提取、DeepSeek调用、批量生成等能力。

### 1.3 MVP不做范围

MVP阶段明确不做以下功能：

1.  不做在线Word编辑。
2.  不做多人协同审阅。
3.  不做审核通过、驳回、备注、复核等审核流程。
4.  不做RAG知识库。
5.  不做复杂权限体系。
6.  不做模板在线可视化编辑器。
7.  不做高保真Word在线编辑预览。
8.  不做复杂流程引擎。
9.  不做企业级归档、长期审计、操作日志追踪。
10. 不做Word内溯源批注。

MVP只负责：生成、溯源查看、下载。

## 二、核心用户与使用场景

### 2.1 用户角色

#### 业务经办人员

负责创建生成任务、上传Excel业务数据、选择模板、查看生成结果、查看数据溯源、下载Word文档。

#### 模板管理员

负责维护Word模板、维护实体表Schema、维护模板与数据表之间的关系。

#### 系统管理员

MVP阶段仅负责系统配置、文件目录、API Key、基础运行环境维护。不设计复杂后台管理权限。

### 2.2 典型场景

#### 场景一：批量生成客户尽调报告

客户经理准备客户信息表、企业财务表、贷款合同表等Excel数据，选择尽调报告模板。系统按客户信息表中的每个客户编号逐条生成Word尽调报告。用户可点击报告中的客户名称、贷款金额、资产负债率等字段，查看来源Excel行列，确认后下载Word。

#### 场景二：批量生成支行经营分析报告

分行经办人员上传支行主表、贷款汇总表、产品明细表等数据。系统以支行主表为主表，每个支行生成一份经营分析报告。报告中的贷款余额、不良率、产品明细等字段可在Web页面中溯源。

#### 场景三：批量生成合同签署材料

用户上传客户贷款数据和担保品明细数据。系统根据合同模板批量生成签署材料。担保品明细支持表格循环生成，用户可查看合同金额、客户名称、担保品信息的Excel来源。

## 三、MVP总体架构

### 3.1 架构原则

1.  **配置驱动**\
    模板、数据表、字段、主键、表关系通过配置文件管理，减少硬编码。

2.  **任务隔离**\
    每次生成任务拥有独立工作目录，上传数据、生成产物、trace文件互相隔离。

3.  **生成与溯源分离**\
    Word文档只保留最终业务内容；溯源信息存储在独立的trace JSON文件中。

4.  **主表只负责批量驱动，不参与变量别名转换**\
    取消`data`别名。模板中所有变量都使用真实表名访问。

5.  **Web预览服务于溯源，不追求Word高保真排版**\
    MVP预览页面只需结构化展示段落、标题和表格，并支持点击数据值查看来源。

### 3.2 核心流程

    1. 模板管理员准备配置
       - entity_schema.xlsx
       - template_relation.xlsx
       - Word模板文件

    2. 业务用户创建任务
       - 选择模板
       - 上传Excel数据
       - 填写任务名称

    3. 系统执行生成前校验
       - 检查模板是否存在
       - 检查依赖表是否上传
       - 检查字段是否完整
       - 检查主键是否唯一
       - 检查模板变量是否合法
       - 检查AI Block是否配置正确

    4. 系统批量生成文档
       - 按主表逐行生成context
       - docxtpl渲染变量、条件、循环
       - 处理AI段落
       - 输出最终docx
       - 输出trace.json
       - 输出preview.json

    5. 用户在线查看溯源
       - 左侧查看文档结构化预览
       - 点击数据值
       - 右侧查看Excel来源

    6. 用户下载文档
       - 单个下载docx
       - 批量下载zip

## 四、变量命名与模板规范

### 4.1 核心决策：取消`data`别名

旧方案中主表字段通过`{{ data.xxx }}`访问，辅表通过`{{ table_name.xxx }}`访问。这会造成理解割裂：明明主表是"客户信息表"，但模板里却叫`data`。

MVP新规则：

> 模板中的所有变量统一使用"表名.字段名"访问，不再使用`data`别名。

例如：

    {{ customer_info.customer_name }}
    {{ customer_info.customer_id }}
    {{ loan_summary.loan_balance }}
    {{ company_finance.debt_ratio }}

其中：

-   `customer_info`是真实表名。
-   `customer_name`是真实字段名。
-   `role=main`只表示该表是批量生成的驱动表。
-   主表在模板中仍然使用自己的真实表名，不再被改名为`data`。

### 4.2 主表定义规则

每个模板必须且只能配置一个主表。

主表的作用：

1.  决定系统按哪张表逐行生成文档。
2.  决定每份文档的主键值。
3.  决定辅表数据过滤的基准。
4.  决定输出文件名中的主体标识。

示例：

    template_id = 1
    template_name = 客户尽调报告
    main_table = customer_info
    primary_key = customer_id

如果`customer_info.xlsx`中有3个客户：

    C001 张三公司
    C002 李四公司
    C003 王五公司

系统生成：

    客户尽调报告_C001.docx
    客户尽调报告_C002.docx
    客户尽调报告_C003.docx

模板中访问主表字段：

    客户名称：{{ customer_info.customer_name }}
    客户编号：{{ customer_info.customer_id }}
    所属行业：{{ customer_info.industry }}

### 4.3 辅表定义规则

辅表通过配置表与主表建立关联。

辅表分为两类：

#### 一对一辅表

一份报告中只匹配一行数据。

示例：

    贷款余额：{{ loan_summary.loan_balance }}
    不良余额：{{ loan_summary.bad_balance }}
    不良率：{{ loan_summary.bad_rate }}

#### 一对多辅表

一份报告中匹配多行数据，通常用于Word表格循环。

示例：

    {%tr for item in collateral_info %}
    {{ item.collateral_name }}
    {{ item.eval_amount }}
    {{ item.mortgage_rate }}
    {%tr endfor %}

说明：

-   如果辅表配置为`one_to_one`，模板中直接使用`{{ table_name.field_name }}`。
-   如果辅表配置为`one_to_many`，模板中使用`{% for item in table_name %}`循环。
-   系统根据配置中的关联键自动过滤出当前主键对应的数据。

### 4.4 中文名使用策略

MVP阶段建议：

1.  模板变量只使用英文表名和英文字段名。
2.  中文表名和中文字段名只用于页面展示、溯源说明和错误提示。
3.  暂不支持模板中直接写中文变量，例如`{{ ``客户信息表.客户名称`` }}`。
4.  后续版本可增加中文变量预处理能力，但不纳入MVP。

原因：

-   英文变量对docxtpl和Jinja2更稳定。
-   中文变量容易遇到字段重名、符号解析、模板维护困难等问题。
-   中文展示需求可以通过Schema配置解决，不影响业务用户查看。

### 4.5 支持的模板能力

#### 变量填充

    {{ customer_info.customer_name }}
    {{ loan_summary.loan_balance }}

#### 条件判断

    {% if company_finance.debt_ratio > 0.7 %}
    该客户资产负债率较高，需关注偿债压力。
    {% else %}
    该客户资产负债率处于合理区间。
    {% endif %}

#### 表格循环

    {%tr for item in collateral_info %}
    {{ item.collateral_name }}
    {{ item.eval_amount }}
    {{ item.mortgage_rate }}
    {%tr endfor %}

#### AI段落生成

在Word模板中使用`§AIBLOCK0§`作为AI段落占位标记，并在Word批注中维护prompt。

模板正文示例：

    §AIBLOCK0§ 请基于客户经营情况、财务指标和贷款信息生成风险分析段落。

批注prompt示例：

    prompt="请基于客户{{ customer_info.customer_name }}的资产负债率{{ company_finance.debt_ratio }}、贷款余额{{ loan_summary.loan_balance }}，生成一段严谨、客观、适合银行内部报告的风险分析。"

AI处理规则：

1.  系统读取原始模板中的批注prompt。
2.  用当前报告context渲染prompt变量。
3.  调用DeepSeek生成文本。
4.  将生成内容替换`§AIBLOCKn§`所在段落。
5.  最终docx中不保留AI标记。

## 五、配置文件设计

### 5.1 实体表Schema配置：entity_schema.xlsx

该文件是系统的数据字典，定义所有业务表和字段。

建议字段如下：

  字段名           必填   说明                             示例
  ---------------- ------ -------------------------------- ----------------------------------
  table_name       是     英文表名，模板变量使用该名称     customer_info
  table_name_cn    否     中文表名，用于页面展示           客户信息表
  field_name       是     英文字段名，模板变量使用该名称   customer_name
  field_name_cn    否     中文字段名，用于页面展示         客户名称
  data_type        否     字段类型                         string / number / date / percent
  is_primary_key   是     是否主键                         1 / 0
  required         否     是否必填                         1 / 0
  display_format   否     展示格式                         amount_2 / percent_2 / date_ymd
  description      否     字段说明                         客户主体名称

业务规则：

1.  同一张表必须且只能有一个主键字段。
2.  `table_name + field_name`必须唯一。
3.  `table_name`、`field_name`建议只使用英文、数字和下划线。
4.  中文名不参与模板渲染，只参与展示。
5.  如果字段配置为必填，上传数据中该字段不能为空。

### 5.2 模板关系配置：template_relation.xlsx

该文件定义模板使用哪些表，以及表与表之间如何关联。

建议字段如下：

  字段名           必填   说明                              示例
  ---------------- ------ --------------------------------- --------------------
  template_id      是     模板ID                            1
  template_name    是     模板名称                          客户尽调报告
  template_file    是     Word模板文件名                    due_diligence.docx
  table_name       是     模板依赖的数据表                  customer_info
  role             是     main / aux                        main
  relation_type    是     main / one_to_one / one_to_many   main
  main_join_key    否     主表关联字段                      customer_id
  table_join_key   否     当前表关联字段                    customer_id
  required         否     是否必须匹配到数据                1
  description      否     说明                              客户基础信息主表

业务规则：

1.  每个`template_id`必须且只能有一张`role=main`的表。
2.  主表的`relation_type`固定为`main`。
3.  辅表必须配置`main_join_key`和`table_join_key`。
4.  `one_to_one`辅表匹配多行时，系统报错。
5.  `one_to_many`辅表匹配零行时，根据`required`决定报错或返回空列表。
6.  模板中的变量只能引用该模板已配置的数据表。

## 六、任务与数据管理

### 6.1 创建任务

用户在Web界面创建生成任务，需要填写或选择：

1.  任务名称。
2.  模板。
3.  上传Excel文件。
4.  是否启用AI生成。
5.  是否生成后自动进入溯源预览。

MVP阶段建议一次任务只选择一个模板。多模板批量生成后置。

### 6.2 数据上传规则

1.  仅支持`.xlsx`。
2.  每张业务表对应一个Excel文件。
3.  Excel文件名建议与`table_name`一致，例如`customer_info.xlsx`。
4.  第一行为字段名，字段名必须使用英文字段名。
5.  单个文件建议不超过100MB。
6.  系统上传后复制到任务目录，不直接修改原始文件。

### 6.3 任务目录结构

    tasks/
    └── task_20260613_001/
        ├── meta.json
        ├── data/
        │   ├── customer_info.xlsx
        │   ├── loan_summary.xlsx
        │   └── collateral_info.xlsx
        ├── validation/
        │   └── validation_report.json
        ├── output/
        │   ├── 客户尽调报告_C001.docx
        │   ├── 客户尽调报告_C001.trace.json
        │   ├── 客户尽调报告_C001.preview.json
        │   ├── 客户尽调报告_C002.docx
        │   ├── 客户尽调报告_C002.trace.json
        │   └── 客户尽调报告_C002.preview.json
        └── logs/
            └── generation.log

## 七、生成前校验

### 7.1 校验目标

在真正生成Word之前，系统必须先发现配置、模板和数据中的明显问题，避免用户等待生成后才发现失败。

### 7.2 校验内容

#### 模板配置校验

1.  模板文件是否存在。
2.  模板ID是否存在。
3.  是否配置且仅配置一个主表。
4.  依赖表是否均已在Schema中定义。
5.  辅表关联键是否配置完整。

#### 数据文件校验

1.  依赖Excel是否已上传。
2.  Excel能否正常读取。
3.  Excel字段是否覆盖Schema必需字段。
4.  主键字段是否存在。
5.  主键是否为空。
6.  主键是否重复。
7.  必填字段是否为空。
8.  字段类型是否明显异常。

#### 模板变量校验

1.  模板中的变量表名是否存在于`template_relation.xlsx`。
2.  模板中的字段是否存在于`entity_schema.xlsx`。
3.  条件表达式中的字段是否存在。
4.  表格循环中的表是否为`one_to_many`。
5.  AI Block标记与批注prompt是否匹配。
6.  Jinja语法是否可以正常解析。

### 7.3 校验报告

系统生成`validation_report.json`，并在前端以可读方式展示。

报告分为三类：

1.  **Error**：阻断生成，必须修正。
2.  **Warning**：不阻断生成，但提示风险。
3.  **Info**：普通提示。

示例：

    {
      "status": "failed",
      "errors": [
        {
          "type": "missing_field",
          "message": "模板引用字段 loan_summary.loan_balance，但上传数据中缺少字段 loan_balance",
          "table": "loan_summary",
          "field": "loan_balance"
        }
      ],
      "warnings": [
        {
          "type": "empty_aux_table",
          "message": "collateral_info 未匹配到客户 C001 的担保品数据，将渲染为空表"
        }
      ]
    }

## 八、批量文档生成引擎

### 8.1 生成逻辑

系统以主表为批量生成驱动表。

伪流程：

    读取模板配置
    读取主表
    读取辅表
    for 主表每一行:
        当前主键 = 当前行主键值
        构建context
        构建trace_map
        渲染Word模板
        处理AI段落
        生成trace.json
        生成preview.json
        输出docx

### 8.2 Context构建规则

对于当前主键值，系统构建如下context：

    {
      "customer_info": {
        "customer_id": "C001",
        "customer_name": "张三公司",
        "industry": "制造业"
      },
      "loan_summary": {
        "loan_balance": 1200.00,
        "bad_rate": 0.018
      },
      "collateral_info": [
        {
          "collateral_name": "厂房",
          "eval_amount": 3000.00
        },
        {
          "collateral_name": "设备",
          "eval_amount": 500.00
        }
      ]
    }

说明：

1.  主表以真实表名作为context key。
2.  一对一辅表以真实表名作为dict。
3.  一对多辅表以真实表名作为list。
4.  不再创建`data`别名。
5.  不再创建中文变量别名。
6.  所有展示格式在渲染前统一处理。

### 8.3 输出文件命名

默认命名规则：

    {template_name}_{primary_key}.docx

示例：

    客户尽调报告_C001.docx
    客户尽调报告_C002.docx

后续版本可支持通过配置自定义文件名，例如：

    {{ customer_info.customer_name }}_尽调报告.docx

MVP阶段可暂不实现自定义文件名。

### 8.4 AI生成规则

1.  AI功能默认可开关。
2.  如果用户关闭AI，系统保留模板中的原始段落并删除`§AIBLOCKn§`标记。
3.  如果AI调用失败，系统保留原始段落并在生成日志中记录失败原因。
4.  AI失败不阻断整份文档生成。
5.  每个AI段落生成时应记录AI调用元数据。

AI元数据建议写入trace文件：

    {
      "ai_blocks": [
        {
          "block_id": "AIBLOCK0",
          "status": "success",
          "prompt_template": "...",
          "prompt_rendered": "...",
          "model": "deepseek-chat",
          "generated_text": "...",
          "generated_at": "2026-06-13T15:00:00"
        }
      ]
    }

## 九、可视化溯源功能

### 9.1 功能定位

可视化溯源不是审核流程，而是"生成结果解释器"。

用户可以通过Web界面理解：

1.  文档中的某个值来自哪里。
2.  来源Excel文件是什么。
3.  来源表是什么。
4.  来源字段是什么。
5.  来源行是哪一行。
6.  当前文档对应哪个主键。

用户查看确认后，可直接下载Word到本地。

### 9.2 页面布局

    ┌─────────────────────────────────────────────────────────────┐
    │  任务：客户尽调报告生成任务                                  │
    │  当前文档：客户尽调报告_C001.docx                            │
    │  [上一份] [下一份] [下载当前Word] [批量下载ZIP]                │
    ├──────────────────────────────┬──────────────────────────────┤
    │ 左侧：文档结构化预览           │ 右侧：数据来源详情             │
    │                              │                              │
    │ 客户尽调报告                  │ 当前主键：C001                 │
    │ 客户名称：[张三公司]           │ 来源文件：customer_info.xlsx   │
    │ 贷款余额：[1200.00]万元        │ 来源表：客户信息表              │
    │ 不良率：[1.80%]               │ 来源字段：客户名称              │
    │                              │ Excel行号：第2行               │
    │ 担保品明细表：                │ 原始值：张三公司                │
    │ [厂房] [3000.00]              │ 展示值：张三公司                │
    │ [设备] [500.00]               │                              │
    │                              │ 表格预览：                     │
    │                              │ customer_id | customer_name    │
    │                              │ C001        | 张三公司          │
    └──────────────────────────────┴──────────────────────────────┘

### 9.3 交互规则

1.  用户从任务结果列表进入文档预览页。
2.  左侧加载`preview.json`，展示标题、段落、表格。
3.  可溯源字段显示为可点击样式。
4.  用户点击某个值后，右侧加载对应trace详情。
5.  右侧展示来源文件、来源表、来源字段、来源行、原始值、展示值。
6.  页面提供"下载当前Word"和"批量下载ZIP"。
7.  页面不提供通过、驳回、备注、保存审核等按钮。

### 9.4 TraceItem数据结构

    {
      "trace_id": "uuid-trace-001",
      "var_path": "customer_info.customer_name",
      "table_name": "customer_info",
      "table_name_cn": "客户信息表",
      "field_name": "customer_name",
      "field_name_cn": "客户名称",
      "source_file": "customer_info.xlsx",
      "pk": "C001",
      "row_index": 0,
      "excel_row_number": 2,
      "raw_value": "张三公司",
      "display_value": "张三公司",
      "value_type": "string"
    }

### 9.5 trace.json结构

    {
      "schema_version": "1.0",
      "doc_id": "uuid-doc-001",
      "task_id": "task_20260613_001",
      "template_id": 1,
      "template_name": "客户尽调报告",
      "output_file": "客户尽调报告_C001.docx",
      "main_table": "customer_info",
      "primary_key": "customer_id",
      "primary_key_value": "C001",
      "generated_at": "2026-06-13T15:00:00",
      "source_files": [
        "customer_info.xlsx",
        "loan_summary.xlsx",
        "collateral_info.xlsx"
      ],
      "trace_items": [
        {
          "trace_id": "uuid-trace-001",
          "var_path": "customer_info.customer_name",
          "table_name": "customer_info",
          "table_name_cn": "客户信息表",
          "field_name": "customer_name",
          "field_name_cn": "客户名称",
          "source_file": "customer_info.xlsx",
          "pk": "C001",
          "row_index": 0,
          "excel_row_number": 2,
          "raw_value": "张三公司",
          "display_value": "张三公司"
        }
      ],
      "ai_blocks": []
    }

### 9.6 preview.json结构

    {
      "doc_id": "uuid-doc-001",
      "title": "客户尽调报告_C001.docx",
      "blocks": [
        {
          "type": "heading",
          "level": 1,
          "text": "客户尽调报告"
        },
        {
          "type": "paragraph",
          "runs": [
            {"text": "客户名称："},
            {
              "text": "张三公司",
              "trace_id": "uuid-trace-001"
            }
          ]
        },
        {
          "type": "table",
          "headers": ["担保品名称", "评估价值"],
          "rows": [
            [
              {"text": "厂房", "trace_id": "uuid-trace-101"},
              {"text": "3000.00", "trace_id": "uuid-trace-102"}
            ]
          ]
        }
      ]
    }

说明：

1.  Web预览优先使用`preview.json`，不强依赖从最终docx反解析定位。
2.  `preview.json`由生成阶段同步产生。
3.  最终docx保持干净，不写入trace_id。

## 十、前端功能需求

### 10.1 页面一：任务列表

功能：

1.  查看历史任务。
2.  查看任务状态。
3.  新建任务。
4.  进入任务结果。
5.  删除本地任务记录，MVP可选。

字段：

  字段            说明
  --------------- -----------------------------------------------------
  task_id         任务ID
  task_name       任务名称
  template_name   模板名称
  status          pending / validating / running / completed / failed
  doc_count       生成文档数量
  created_at      创建时间

### 10.2 页面二：新建任务

功能：

1.  输入任务名称。
2.  选择模板。
3.  根据模板自动展示所需数据表。
4.  上传Excel文件。
5.  点击"校验数据"。
6.  校验通过后点击"开始生成"。

交互要求：

1.  如果缺少必需文件，不允许生成。
2.  如果校验失败，展示错误清单。
3.  如果校验通过，展示预计生成文档数量。
4.  生成过程中展示进度。

### 10.3 页面三：任务结果

功能：

1.  展示本次任务生成的所有文档。
2.  支持按主键、文件名搜索。
3.  点击文档进入溯源预览页。
4.  支持单个下载。
5.  支持批量下载ZIP。

### 10.4 页面四：文档溯源预览

功能：

1.  左侧展示文档结构化预览。
2.  可溯源字段高亮显示。
3.  点击字段后右侧展示来源详情。
4.  支持上一份/下一份切换。
5.  支持下载当前Word。
6.  支持返回任务结果页。

## 十一、后端API需求

### 11.1 任务API

  API                               方法   说明
  --------------------------------- ------ ------------------
  `/api/tasks`                      GET    获取任务列表
  `/api/tasks`                      POST   创建任务
  `/api/tasks/{task_id}`            GET    获取任务详情
  `/api/tasks/{task_id}/validate`   POST   执行生成前校验
  `/api/tasks/{task_id}/generate`   POST   开始生成
  `/api/tasks/{task_id}/outputs`    GET    获取生成结果列表

### 11.2 模板API

  API                                           方法   说明
  --------------------------------------------- ------ ----------------------
  `/api/templates`                              GET    获取模板列表
  `/api/templates/{template_id}`                GET    获取模板详情
  `/api/templates/{template_id}/requirements`   GET    获取模板依赖表和字段

MVP阶段模板上传可先通过文件目录和配置Excel维护，前端上传模板可以后置。

### 11.3 文档API

  API                                   方法   说明
  ------------------------------------- ------ ------------------
  `/api/documents/{doc_id}/preview`     GET    获取preview.json
  `/api/documents/{doc_id}/trace`       GET    获取trace.json
  `/api/documents/{doc_id}/download`    GET    下载当前Word
  `/api/tasks/{task_id}/download-zip`   GET    批量下载ZIP

### 11.4 溯源API

  API                                  方法   说明
  ------------------------------------ ------ ---------------------
  `/api/trace/{trace_id}`              GET    获取单个trace详情
  `/api/trace/{trace_id}/source-row`   GET    获取来源Excel行数据

## 十二、技术选型

### 12.1 后端

  技术           用途
  -------------- ------------------------
  FastAPI        后端API
  pandas         Excel数据处理
  openpyxl       xlsx读取
  docxtpl        Word模板渲染
  python-docx    Word结构解析与辅助处理
  lxml           docx底层XML处理
  Jinja2         模板变量与prompt渲染
  SQLite         任务、模板、文档元数据
  本地文件系统   存储上传数据和生成产物
  DeepSeek API   AI段落生成
  tenacity       AI调用重试

### 12.2 前端

  技术                     用途
  ------------------------ -----------------
  Vue 3                    前端框架
  Element Plus             UI组件
  Axios                    API请求
  原生表格/Element Table   Excel来源行展示
  Vite                     前端构建

MVP不建议引入Handsontable，避免授权和集成复杂度。只读表格展示用Element Plus Table即可。

## 十三、数据存储设计

### 13.1 SQLite表

#### templates

    CREATE TABLE templates (
        id INTEGER PRIMARY KEY,
        template_name TEXT NOT NULL,
        template_file TEXT NOT NULL,
        main_table TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT
    );

#### tasks

    CREATE TABLE tasks (
        task_id TEXT PRIMARY KEY,
        task_name TEXT NOT NULL,
        template_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        doc_count INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    );

#### documents

    CREATE TABLE documents (
        doc_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        template_id INTEGER NOT NULL,
        primary_key_value TEXT NOT NULL,
        output_file TEXT NOT NULL,
        trace_file TEXT NOT NULL,
        preview_file TEXT NOT NULL,
        created_at TEXT
    );

#### generation_logs

    CREATE TABLE generation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        detail TEXT,
        created_at TEXT
    );

MVP不需要`reviews`表。

## 十四、异常处理规则

### 14.1 阻断生成的异常

1.  模板文件不存在。
2.  配置中没有主表。
3.  一个模板配置了多个主表。
4.  主表Excel未上传。
5.  主表主键字段缺失。
6.  主表主键为空。
7.  主表主键重复。
8.  模板引用了未配置的表。
9.  模板引用了不存在的字段。
10. Jinja语法错误。
11. Word模板无法读取。

### 14.2 不阻断但需提示的异常

1.  非必需辅表没有匹配数据。
2.  非必填字段为空。
3.  AI调用失败。
4.  AI输出为空。
5.  某些字段格式与Schema声明不一致但可转换。
6.  输出文件名存在特殊字符并被系统自动替换。

### 14.3 AI失败降级

AI失败时：

1.  不终止整份文档生成。
2.  删除`§AIBLOCKn§`标记。
3.  保留原段落文本。
4.  在日志和trace中记录失败原因。
5.  前端任务结果页提示"部分AI段落生成失败"。

## 十五、非功能需求

### 15.1 性能

1.  单份普通文档生成时间不超过30秒。
2.  10份普通文档批量生成不超过5分钟，AI网络延迟除外。
3.  单个Excel文件MVP建议不超过100MB。
4.  溯源预览页面打开时间建议不超过3秒。

### 15.2 可靠性

1.  生成任务失败时，应保留错误日志。
2.  已成功生成的文档不应因后续文档失败而删除。
3.  AI失败不影响基础文档生成。
4.  文件写入应避免覆盖已有任务。
5.  trace.json和preview.json应与docx一一对应。

### 15.3 可维护性

1.  生成引擎、API层、前端页面应分层开发。
2.  旧Notebook代码应重构为独立Python模块，不直接复制成大脚本。
3.  核心函数应有单元测试。
4.  trace JSON schema应固定版本。
5.  错误信息应面向业务用户可读。

### 15.4 安全性

1.  API Key只通过环境变量配置。
2.  不在日志中打印API Key。
3.  上传文件限制后缀为`.xlsx`和`.docx`。
4.  任务文件路径必须防止路径穿越。
5.  下载接口只能下载任务输出目录内的文件。

## 十六、MVP开发阶段划分

### Phase 1：后端生成引擎工程化

交付内容：

1.  重构旧代码核心函数。
2.  完成配置加载。
3.  完成Excel加载。
4.  完成context构建。
5.  完成docxtpl渲染。
6.  完成单模板批量生成。
7.  输出docx。

目标：命令行或API能稳定生成Word文档。

### Phase 2：模板校验与任务管理

交付内容：

1.  FastAPI项目结构。
2.  任务创建。
3.  文件上传。
4.  生成前校验。
5.  校验报告。
6.  任务状态管理。
7.  生成日志。

目标：用户能通过API或简单前端创建任务并发现配置/数据问题。

### Phase 3：AI段落集成

交付内容：

1.  读取Word批注prompt。
2.  渲染prompt变量。
3.  调用DeepSeek。
4.  AI失败降级。
5.  记录AI元数据。

目标：支持AI段落生成，但不影响基础文档生成稳定性。

### Phase 4：trace与preview生成

交付内容：

1.  TraceItem数据结构。
2.  trace.json生成。
3.  preview.json生成。
4.  字段展示格式统一。
5.  文档、trace、preview一一对应。

目标：每个生成值都尽量能追溯到来源Excel。

### Phase 5：Web前端MVP

交付内容：

1.  任务列表页。
2.  新建任务页。
3.  任务结果页。
4.  文档溯源预览页。
5.  单文档下载。
6.  批量ZIP下载。

目标：用户能通过Web完成完整闭环。

## 十七、MVP验收标准

### 17.1 基础生成验收

1.  支持上传至少3张Excel表。
2.  支持一个模板关联一个主表和多个辅表。
3.  支持按主表多行批量生成多份docx。
4.  支持变量填充。
5.  支持条件判断。
6.  支持表格循环。
7.  最终docx可用Word/WPS正常打开。

### 17.2 AI生成验收

1.  支持至少一个`§AIBLOCK0§`段落。
2.  支持从Word批注读取prompt。
3.  支持prompt变量渲染。
4.  支持调用DeepSeek生成文本。
5.  AI失败时文档仍可生成。

### 17.3 溯源验收

1.  每份docx对应一个trace.json。
2.  每份docx对应一个preview.json。
3.  预览页中可点击字段值。
4.  点击后可展示来源表、字段、文件、行号、原始值、展示值。
5.  支持一对一辅表字段溯源。
6.  支持一对多表格循环字段溯源。

### 17.4 下载验收

1.  支持下载单个docx。
2.  支持批量下载zip。
3.  下载的Word中不包含trace标记。
4.  下载的Word中不包含系统批注。
5.  下载的Word排版与模板基本一致。

## 十八、后续版本规划

### V1.1

1.  中文变量兼容。
2.  模板上传管理页面。
3.  模板版本管理。
4.  自定义输出文件名。
5.  更完整的格式化规则。

### V1.2

1.  多模板任务。
2.  更强的trace定位能力。
3.  任务归档。
4.  操作日志。
5.  简单用户权限。

### V2.0

1.  在线Word预览增强。
2.  ONLYOFFICE或类似文档编辑服务集成。
3.  审核流。
4.  RAG知识库。
5.  企业级数据库迁移。
6.  多人协同与权限体系。

## 十九、给开发实现的关键提醒

1.  不要再使用`data`作为主表别名。
2.  所有模板变量统一使用`table_name.field_name`。
3.  `role=main`只表示批量生成驱动表。
4.  MVP不做审核状态，不建reviews表。
5.  MVP不做RAG。
6.  MVP不做Word批注溯源。
7.  trace和preview应在生成阶段同步产生，不要完全依赖生成后反查docx文本。
8.  旧Notebook只复用已验证的核心流水线，不复用未完成的智能标记、RAG和Word溯源批注代码。
