# Excel 模板生成支持：Codex 开发任务

## 1. 任务目标

在不破坏现有 Word 批量生成闭环的前提下，为系统新增 `.xlsx` 模板批量生成能力。任务仍按主表每一行生成一份文件，继续复用现有模板关系、Excel 业务数据上传、校验、context、TraceMap、任务状态、文档记录、Web 溯源、单文件下载和 ZIP 下载能力。

首版 Excel 模板只渲染第一个工作表中的变量，不实现循环、条件、AI 段落或公式计算。

## 2. 已确认的现状与设计结论

当前实现并非只在渲染器中依赖 Word，而是在以下环节直接绑定 `.docx`：模板上传/替换、模板安全文件名、变量解析与中文变量规范化、生成调度、AI 收尾、预览解析、下载 MIME、输出后缀及前端文案。因此必须按模板文件类型分派完整生成管线，不能简单复制 `docx_renderer.py`。

保留以下公共链路，不重复实现：

- `TemplateRequirementService`、`load_data_tables()`、`validate_task()` 的公共数据校验
- `build_report_contexts()` 及现有 `TraceMap`
- 任务/文档数据库记录、状态推进、日志、失败隔离
- `.trace.json`、`.preview.json`、单文件下载和 ZIP 下载 API
- 前端任务创建、上传业务数据、任务结果和溯源详情主流程

新增文件类型分派，Word 继续走当前 DOCX 管线，Excel 走新的 XLSX 管线。不得将 Excel 分支塞入 Word 渲染器、Word finalizer 或 DOCX preview parser。

## 3. 首版范围

### 3.1 支持

- 模板格式：仅 `.docx`、`.xlsx`；拒绝 `.doc`、`.xls`、`.xlsm`、`.csv`
- Excel 模板渲染范围：`workbook.worksheets[0]`
- 单元格变量：`{{ customer_info.customer_name }}`
- 单元格混合文本：`客户名称：{{ customer_info.customer_name }}`
- 英文变量及项目现有中文别名兼容；渲染前统一规范化为英文 `table.field`
- 主表和 `one_to_one` 辅表字段
- 每个主表数据行生成一份 `.xlsx`
- 保留工作簿已有样式、合并单元格、行高、列宽、打印设置和未修改单元格
- 生成 `.trace.json` 和 `.preview.json`，Web 可点击预览字段查看来源
- 单文件及混合格式 ZIP 下载

### 3.2 不支持

- `{% for %}`、`{%tr %}`、`{% if %}`、宏、include 等 Jinja 控制结构
- `one_to_many` 数据直接渲染；该关系必须等待后续循环能力
- AI Block、批注提示词、知识库或任何 RAG 能力
- 公式求值、公式内变量、图表数据重算
- 多工作表渲染；非首个工作表保持原样
- 在线编辑 Excel

若非首个工作表存在 Jinja 标记，生成前校验必须报错，防止输出带有未渲染变量。

## 4. 变量和值规则

1. 模板内部规范变量仍为英文 `table_name.field_name`，禁止 `data.field_name`。
2. 为兼容项目当前已实现能力，允许作者使用 Schema 中唯一匹配的中文表名/字段名；必须在临时规范化副本中转换为英文路径，原模板不得被修改。
3. 未知表、未知字段、歧义中文名、`data.*`、一对多字段及控制语句均在生成前校验阶段失败，不允许静默输出空字符串。
4. 使用 Jinja2 `StrictUndefined`。每个字符串单元格独立渲染，不把整个 worksheet XML 当作一个模板。
5. context 中的 `TraceValue` 继续输出现有 `display_value`，确保 Word 与 Excel 展示格式一致。
6. 空值沿用当前 `format_display_value()` 结果；不得在 Excel 分支另造格式规则。
7. 公式单元格保持原公式。公式文本中出现 Jinja 标记时校验失败。
8. openpyxl 不计算公式；输出文件打开后是否重算由 Excel/WPS 决定，本任务不伪造缓存值。

## 5. 后端改造

### 5.1 文件类型公共能力

新增集中定义（建议 `backend/app/engine/template_file_type.py`）：

- `TemplateFileType`：`docx`、`xlsx`
- 后缀白名单、输出后缀、下载 MIME 映射
- `detect_template_file_type(path_or_filename)`；未知后缀抛稳定业务错误

文件类型以模板文件实际后缀为唯一事实来源，首版不新增数据库列，避免既有 SQLite 数据迁移和双来源不一致。API 模型可增加只读计算字段 `template_file_type`，值由 `template_file` 推导。

### 5.2 模板上传、替换与存储

修改：

- `services/template_file_service.py`
- `storage/safe_filename.py`
- `storage/file_manager.py`（如其内部假设 `.docx`）
- 模板下载接口的 MIME

要求：

- 创建支持 `.docx` 和 `.xlsx`；保存名为 `template_{template_id}{原后缀}`
- XLSX 使用 `openpyxl.load_workbook(BytesIO(...), data_only=False)` 验证包完整性且至少有一个工作表
- 替换模板只允许相同文件类型，避免已有模板路径、任务及配置语义突变；类型不同返回 `UPLOAD_FILE_INVALID`
- 写入继续使用原子替换和目录边界检查
- DOCX 现有校验行为不得回退

### 5.3 Excel 变量解析与规范化

新增：

- `engine/xlsx_template_parser.py`
- `engine/xlsx_template_canonicalizer.py`

解析器只扫描首个工作表的字符串单元格，返回变量引用及所在坐标。复用 `template_canonicalizer.py` 中的 `TemplateVariableResolver` 和文本级 `canonicalize_jinja_text()`；如需抽取公共代码，应保持 DOCX 现有测试通过。

规范化器读取原模板、只修改内存工作簿首个 sheet 的字符串单元格并写入任务临时目录，例如 `{task_id}_{template_id}.canonical.xlsx`。它必须返回：

- 规范化文件路径
- `original_var_paths_by_canonical`
- 未识别变量列表
- 单元格绑定信息：sheet 名、坐标、单元格原文本、规范变量出现顺序

不要直接手改 `sharedStrings.xml` 或 worksheet XML；项目已有 openpyxl，使用结构化 API 更稳妥。

### 5.4 校验

重构 `engine/validator.py` 的模板专属部分为按文件类型分派，公共 Schema/Excel 数据/主键/关联校验保持不变。

XLSX 新增校验项：

- 文件可由 openpyxl 打开且存在工作表
- 首 sheet 中 Jinja 语法可解析
- 变量符合 `table.field`，并存在于本模板依赖表及 Schema
- 禁止 `data.*`
- 禁止控制结构、AI 标记、公式内 Jinja
- 禁止引用 `one_to_many` 表字段
- 非首 sheet 不得含 Jinja 标记
- 合并区域只允许左上角主单元格含变量

错误继续进入现有 `validation_report.json`。新增稳定 item code：

- `xlsx_template_invalid`
- `xlsx_jinja_syntax_invalid`
- `xlsx_unsupported_jinja_statement`
- `xlsx_formula_variable_unsupported`
- `xlsx_one_to_many_unsupported`
- `xlsx_variable_outside_first_sheet`
- `xlsx_merged_cell_variable_invalid`

### 5.5 Excel 渲染器

新增 `engine/xlsx_renderer.py`，接口风格与 `docx_renderer.py` 一致，定义明确的输入/结果模型。

处理流程：

1. `load_workbook(..., data_only=False)` 打开规范化模板。
2. 遍历第一个 sheet 的字符串单元格。
3. 对含变量的单元格使用同一个 `Environment(undefined=StrictUndefined, autoescape=False)` 渲染。
4. 写入临时 `.xlsx`，保存后再次用 openpyxl 打开验证。
5. 成功后原子移动到最终输出路径；失败时清理临时文件并返回清晰错误。

渲染结果同时携带单元格绑定和渲染文本，供预览精确绑定 trace。不得依赖“按显示值搜索”来猜测单元格来源，因为重复值会导致错误溯源。

### 5.6 生成调度

重构 `engine/generation_runner.py`：

- 公共阶段：加载需求与数据、校验、规范化、构建 context/TraceMap、逐主表行、写记录
- DOCX strategy：保持 canonicalize -> render -> AI -> finalize -> DOCX trace/preview
- XLSX strategy：canonicalize -> render XLSX -> XLSX trace/preview；强制不调用 AI prompt loader 和 DOCX finalizer
- 输出名后缀由模板类型决定：`.docx` 或 `.xlsx`
- 失败记录也使用正确后缀
- 即使任务请求 `ai_enabled=true`，XLSX 文档的 `ai_status` 必须为 `not_used`、`ai_block_count=0`；前端创建任务时应对 XLSX 隐藏或禁用 AI 开关

不要依赖当前未实际使用的 `output_name_pattern` 决定后缀。本任务内统一由模板类型产生安全输出名，保留现有文件名截断和哈希规则。

### 5.7 Trace 与 Preview

保留现有 `.trace.json` 顶层契约和 `TraceItem` 来源数据。新增：

- `engine/xlsx_preview_builder.py`
- XLSX 专用 trace/preview 编排函数，或将 `trace_builder.py` 改为清晰的类型分派

预览必须由后端读取最终 XLSX 生成，前端不得解析 Excel。首版将首 sheet used range 表示为一个 `PreviewTableBlock`：

- `headers=[]`
- `rows` 包含所有非裁剪范围的行列
- 合并单元格映射为 `rowspan/colspan`
- 最低限度映射文本、对齐、粗体、斜体、字号、前景色、背景色、列宽
- 空尾行/空尾列应裁剪；完全空 sheet 返回空 blocks

字段 trace 必须依据“模板单元格坐标 + 规范变量路径 + occurrence”绑定到 `PreviewRun.trace_id`。混合文本拆成静态 run 和字段 run；一个单元格只有一个纯变量时也可同时设置 cell 级 trace。不得用渲染后文本值匹配 trace。

XLSX 不生成 condition、loop、AI trace。trace 文件中的 `trace_items` 建议只保留模板实际引用到的字段 occurrence，避免把未出现在输出中的整行字段误称为文档溯源；若为兼容现有契约必须保留全量，则至少 preview 只能绑定实际引用项，并补充回归测试固定行为。

### 5.8 下载与 ZIP

修改 `api/documents.py`：根据实际输出后缀返回 MIME：

- `.docx`: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `.xlsx`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

ZIP 当前按文档记录收集文件，保留该逻辑并增加 `.xlsx` 及 Word/Excel 混合任务回归测试。所有路径仍必须位于 `tasks/{task_id}/output/` 和 `temp/{task_id}/`。

## 6. 前端改造

修改模板上传/替换组件：

- `accept=".docx,.xlsx"`
- 文件后缀校验及提示同步支持两种格式
- 模板列表/详情显示“Word”或“Excel”类型
- 替换弹窗只接受当前模板类型

修改任务创建和输出列表：

- XLSX 模板禁用 AI 开关并显示“Excel 模板首版不支持 AI 生成”
- 下载按钮文案按类型显示“下载 Word”或“下载 Excel”，通用情况下可显示“下载文件”
- 继续使用现有 preview/trace 页面和 `PreviewRenderer`；针对 `headers=[]` 的 Excel table 确保不渲染空表头
- 类型定义增加 `template_file_type: 'docx' | 'xlsx'`，不要在多个组件重复手写后缀判断

## 7. 测试要求

### 7.1 后端单元测试

新增至少以下测试文件：

- `test_xlsx_template_parser.py`
- `test_xlsx_template_canonicalizer.py`
- `test_xlsx_renderer.py`
- `test_xlsx_preview_builder.py`

覆盖：

- 英文变量、中文别名、混合文本、多变量单元格
- 样式、合并单元格、行高列宽保留
- 未定义变量、`data.*`、控制语句、公式变量、一对多变量失败
- 非首 sheet 出现变量失败
- 重复展示值仍绑定到各自正确 trace_id
- 输出可由 openpyxl 重新打开且原模板未被修改
- 临时文件在成功和失败后均被清理

### 7.2 集成与回归测试

扩展 `test_generation_runner.py` 和 `test_api_e2e.py`：

- 一个 XLSX 模板按三条主表记录生成三份 `.xlsx`、三份 trace、三份 preview
- 生成内容与主键一一对应
- XLSX 不调用 AI 和 DOCX finalizer
- 文档记录后缀、状态、`ai_status`、计数正确
- 下载 MIME/文件名正确，ZIP 可解压且包含 XLSX
- 上传和同类型替换成功，跨类型替换失败
- 现有 DOCX 全部测试继续通过

### 7.3 前端验证

- `npm` 构建和现有脚本通过
- 上传控件接受两种模板
- XLSX 任务禁用 AI
- Excel 输出预览、点击溯源、单文件下载、ZIP 下载可用
- Word 页面行为无回归

## 8. 验收场景

准备一个单 sheet XLSX 模板，其中包含：普通文本、英文变量、中文别名、混合文本、两个相同展示值的不同字段、样式单元格和合并单元格。配置一个主表和一个 `one_to_one` 辅表，主表至少三行。

完成后必须满足：

1. 模板中心可上传、下载、同类型替换 XLSX 模板。
2. 创建任务、上传业务 Excel、校验、生成流程与 Word 一致。
3. 每个主表行生成一份命名安全的 XLSX，Excel/WPS 可正常打开。
4. 首 sheet 变量全部替换，样式和布局保持；其他 sheet 不参与渲染。
5. 每份输出都有 trace 和 preview，Web 点击每个字段能定位正确来源文件、表、字段、Excel 行列、原始值和展示值。
6. 下载响应 MIME 正确，ZIP 内文件完整。
7. 不产生 Word 批注、AI 内容、循环结果、审核文件或项目目录外文件。
8. 所有新增测试及现有后端/前端回归测试通过。

## 9. 实施顺序

1. 提取文件类型、后缀和 MIME 公共能力，改模板存储与 API 模型。
2. 实现 XLSX 解析、规范化、校验及其单元测试。
3. 实现 XLSX 渲染及文件完整性测试。
4. 实现坐标驱动的 XLSX trace/preview。
5. 将 generation runner 改为 DOCX/XLSX strategy 分派。
6. 修正下载、ZIP 和前端类型展示/AI 开关。
7. 补齐 E2E 与全量回归，修复任何 Word 行为变化。

## 10. 开发约束

- 不新增依赖；只使用现有 openpyxl、Jinja2、Pydantic 等固定技术栈。
- 不直接复制旧 notebook 大段代码，不参考禁止的旧文件。
- 不允许前端直接解析 XLSX。
- 不实现 Excel 在线编辑、RAG、审核流或 Word 批注。
- 所有文件路径使用现有 storage/path 安全能力。
- 新增函数必须有 Type Hints，业务错误使用现有统一响应和稳定错误码。
- 每完成一个阶段先运行相关测试，最终运行后端全量 pytest 和前端构建。
