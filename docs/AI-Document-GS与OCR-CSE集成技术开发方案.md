# AI-Document-GS 与 OCR-CSE 集成技术开发方案

> **文档版本**: v1.0  
> **适用范围**: AI 智能文档生成系统 (AI-Document-GS)  
> **技术栈**: FastAPI + Python 3.12 + SQLite + Vue 3 + TypeScript  
> **集成目标**: 支撑贷前集约系统 (AI-OCR-CSE) 以下能力：一键生成、多文档切换、OCR 图片溯源

---

## 一、概述

本文档定义 AI-Document-GS 为支持 AI-OCR-CSE 集成所需新增/修改的后端 API、数据模型、业务逻辑和存储格式。

### 1.1 集成约定

| 事项 | 约定 |
|------|------|
| 跨系统通信 | OCR-CSE 通过 HTTP 调用 AI-Document-GS 的 REST API |
| GS 监听地址 | `http://127.0.0.1:8000`（两个系统部署在同一台机器） |
| 数据流转 | OCR-CSE 导出数据要素表为 Excel → 按映射规则拆分多表 → 上传到 GS → GS 完成校验/生成/输出 |
| 溯源桥接 | GS 的 .trace.json 扩展 OCR 桥接字段，OCR-CSE 根据桥接字段查询本系统 OCR 证据 |
| 响应格式适配 | OCR-CSE 调用时通过适配层将 GS 的 `{success, data, error}` 转为 `{code, message, data}` |

---

## 二、新增 API 契约

### 2.1 基础路径

```text
BASE = /api/tasks
BASE_DOC = /api/documents
```

### 2.2 API-1: 一键创建并生成 (自动流程)

#### `POST /api/tasks/auto-create-and-generate`

**用途**: 一次性完成创建任务 → 批量上传 Excel → 校验 → 触发生成。OCR-CSE 只需调用此接口即可完成全部流程。

**请求体**:

```json
{
  "task_name": "贷前集约-张三-客户尽调报告",
  "template_id": 1,
  "ai_enabled": true,
  "source_task_id": "ocr_task_20260624_120000",
  "files": [
    {
      "table_name": "customer_info",
      "file_data": "<base64编码的xlsx文件内容>"
    },
    {
      "table_name": "loan_summary",
      "file_data": "<base64编码的xlsx文件内容>"
    }
  ],
  "ocr_field_mappings": [
    {
      "trace_id": "",
      "var_path": "customer_info.customer_name",
      "source_task_id": "ocr_task_20260624_120000",
      "source_file_id": "file_uuid_001",
      "source_page_id": "page_uuid_001",
      "source_block_ids": ["block_uuid_001", "block_uuid_002"],
      "source_bbox": {"x1": 420, "y1": 680, "x2": 890, "y2": 750},
      "source_image_url": "storage/uploads/ocr_task_20260624_120000/original/id_card_front.jpg"
    }
  ]
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_name | string | 是 | 任务名称 |
| template_id | integer | 是 | AI-Document-GS 的模板 ID |
| ai_enabled | boolean | 否 | 默认 true |
| source_task_id | string | 否 | OCR-CSE 的任务 ID，用于溯源桥接 |
| files | array | 是 | 要上传的 Excel 文件列表 |
| files[].table_name | string | 是 | 数据表英文名，如 `customer_info` |
| files[].file_data | string | 是 | Base64 编码的 .xlsx 文件内容 |
| ocr_field_mappings | array | 否 | OCR 字段→模板变量的溯源映射表 |
| ocr_field_mappings[].var_path | string | 是 | GS 模板变量路径，如 `customer_info.customer_name` |
| ocr_field_mappings[].source_task_id | string | 是 | OCR-CSE 的任务 ID |
| ocr_field_mappings[].source_file_id | string | 是 | OCR 原始图片文件 ID |
| ocr_field_mappings[].source_page_id | string | 否 | OCR 页面 ID |
| ocr_field_mappings[].source_block_ids | string[] | 否 | OCR 文本块 ID 列表 |
| ocr_field_mappings[].source_bbox | object | 否 | 识别块坐标 `{x1, y1, x2, y2}` |
| ocr_field_mappings[].source_image_url | string | 否 | OCR 原始图片相对路径 |

**成功响应 (202 Accepted)**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_20260624_160000_a1b2c3",
    "task_name": "贷前集约-张三-客户尽调报告",
    "template_id": 1,
    "template_name": "客户尽调报告",
    "status": "running",
    "file_upload_results": [
      {
        "table_name": "customer_info",
        "row_count": 1,
        "column_count": 10,
        "uploaded": true
      }
    ],
    "validation_summary": {
      "status": "passed",
      "error_count": 0,
      "warning_count": 0
    },
    "message": "任务已创建，文件已上传，校验通过，生成已启动。"
  },
  "request_id": "req_xxx",
  "timestamp": "2026-06-24T16:00:00+08:00"
}
```

**错误响应**:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "校验未通过，无法启动生成。",
    "detail": {
      "status": "validation_failed",
      "error_count": 2,
      "items": [
        {
          "level": "error",
          "code": "missing_field",
          "message": "缺少必填字段：loan_summary.loan_balance"
        }
      ]
    }
  },
  "request_id": "req_xxx",
  "timestamp": "2026-06-24T16:00:00+08:00"
}
```

**状态限制**: 不支持校验失败后强制生成，OCR-CSE 需要根据校验结果修复 Excel 后重新提交。

**处理逻辑**:

```
接收请求
  │
  ├── 1. 校验 template_id 是否存在
  │
  ├── 2. 创建任务 (tasks 表)
  │     └── status = created
  │
  ├── 3. 遍历 files:
  │     ├── 解码 base64 → 写入 tasks/{task_id}/data/{table_name}.xlsx
  │     └── 写入 uploaded_files 表
  │
  ├── 4. 执行校验 (validate_task)
  │     └── 校验不通过 → 返回 error, 任务保持 uploaded 状态
  │
  ├── 5. 保存 ocr_field_mappings 到 tasks/{task_id}/meta.json
  │
  ├── 6. 启动生成 (同步或异步)
  │     └── 将 ocr_field_mappings 注入 generation_runner
  │
  └── 7. 返回 task_id + status
```

### 2.3 API-2: 批量上传文件

#### `POST /api/tasks/{task_id}/upload-batch`

**用途**: 一次请求上传多张 Excel 表。

**Content-Type**: `multipart/form-data`

**Form Fields**:

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| table_names | string[] | 是 | JSON 数组，如 `["customer_info","loan_summary"]` |
| files | File[] | 是 | 文件列表，顺序与 table_names 对应 |

**Request 示例**:

```
POST /api/tasks/task_20260624_160000_a1b2c3/upload-batch
Content-Type: multipart/form-data

table_names=["customer_info","loan_summary"]
file=customer_info.xlsx
file=loan_summary.xlsx
```

**成功响应**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_20260624_160000_a1b2c3",
    "results": [
      {
        "table_name": "customer_info",
        "original_filename": "customer_info.xlsx",
        "row_count": 1,
        "column_count": 10,
        "uploaded": true
      },
      {
        "table_name": "loan_summary",
        "original_filename": "loan_summary.xlsx",
        "row_count": 1,
        "column_count": 8,
        "uploaded": true
      }
    ],
    "uploaded_count": 2,
    "failed_count": 0
  },
  "request_id": "req_xxx",
  "timestamp": "2026-06-24T16:00:00+08:00"
}
```

### 2.4 API-3: 获取文档 OCR 溯源详情

#### `GET /api/documents/{doc_id}/ocr-provenance/{trace_id}`

**用途**: 返回 OCR 图片溯源证据。OCR-CSE 前端通过此接口获取图片 URL 和高亮块坐标，在图片上绘制识别块高亮。

**成功响应**:

```json
{
  "success": true,
  "data": {
    "trace_id": "trace_550e8400-e29b-41d4-a716-446655440001",
    "doc_id": "doc_xxx",
    "task_id": "task_xxx",
    "var_path": "customer_info.customer_name",
    "field_name": "customer_name",
    "field_name_cn": "客户名称",
    "display_value": "张三公司",
    "source_system": "ocr_cse",
    "source_task_id": "ocr_task_20260624_120000",
    "provenance": {
      "file_id": "file_uuid_001",
      "page_id": "page_uuid_001",
      "page_no": 1,
      "total_pages": 3,
      "image_url": "storage/uploads/ocr_task_20260624_120000/original/id_card_front.jpg",
      "image_width": 2480,
      "image_height": 3508,
      "highlights": [
        {
          "block_id": "block_uuid_001",
          "text": "张三公司",
          "confidence": 0.95,
          "bbox": {
            "x1": 420,
            "y1": 680,
            "x2": 890,
            "y2": 750
          },
          "polygon": [[420,680],[890,680],[890,750],[420,750]],
          "highlight_type": "primary"
        },
        {
          "block_id": "block_uuid_002",
          "text": "张三",
          "confidence": 0.88,
          "bbox": {
            "x1": 420,
            "y1": 680,
            "x2": 620,
            "y2": 720
          },
          "polygon": [[420,680],[620,680],[620,720],[420,720]],
          "highlight_type": "context"
        }
      ]
    }
  },
  "request_id": "req_xxx",
  "timestamp": "2026-06-24T16:00:00+08:00"
}
```

**处理逻辑**: 此 API 从 `.trace.json` 文件的 `ocr_provenance` 字段读取保存的 OCR 桥接信息，直接返回。OCR-CSE 在生成时已经将 OCR 溯源信息写入 trace.json。

---

## 三、数据模型扩展

### 3.1 TraceItem 模型扩展

文件: `backend/app/models/trace_models.py`

在 `TraceItem` 类中新增以下可选字段（**所有新字段均有默认值，完全向后兼容**）：

```python
class TraceItem(ContractModel):
    # ... 现有字段保持不变 ...

    # ===== 🆕 OCR 溯源桥接字段 (v2.0) =====
    source_system: str = ""
    # 来源系统标识, "ocr_cse" | ""（空字符串表示来自Excel文件）
    # 当此字段非空时, 前端溯源面板切换为图片证据模式

    ocr_source_task_id: str = ""
    # OCR-CSE 的任务 ID, 用于前端构造图片URL

    ocr_source_file_id: str = ""
    # OCR 原始图片文件ID

    ocr_source_page_id: str = ""
    # OCR 页面ID

    ocr_source_block_ids: list[str] = []
    # OCR 文本块ID列表, 用于关联 bbox 坐标

    ocr_source_bbox: dict | None = None
    # 主识别块坐标 {x1, y1, x2, y2}, 用于定位

    ocr_source_image_url: str = ""
    # OCR 图片相对路径

    ocr_source_image_width: int = 0
    # 图片宽度(像素)

    ocr_source_image_height: int = 0
    # 图片高度(像素)
```

### 3.2 FieldTraceDetail 模型扩展

```python
class FieldTraceDetail(BaseTraceDetail):
    # ... 现有字段保持不变 ...

    # 🆕 OCR 溯源桥接字段
    source_system: str = ""
    ocr_source_task_id: str = ""
    ocr_source_file_id: str = ""
    ocr_source_page_id: str = ""
    ocr_source_block_ids: list[str] = []
    ocr_source_bbox: dict | None = None
    ocr_source_image_url: str = ""
    ocr_source_image_width: int = 0
    ocr_source_image_height: int = 0
```

### 3.3 TraceFile 模型扩展

```python
class TraceFile(ContractModel):
    # ... 现有字段保持不变 ...

    # 🆕 文档级 OCR 溯源信息
    ocr_source_info: dict | None = None
    # {
    #   "source_system": "ocr_cse",
    #   "source_task_id": "ocr_task_xxx",
    #   "field_mappings_count": 12
    # }
```

---

## 四、存储层修改

### 4.1 `meta.json` 扩展

在任务级 `meta.json` 中增加 `ocr_source_info` 字段：

```json
{
  "schema_version": "1.0",
  "task_id": "task_20260624_160000_a1b2c3",
  "status": "completed",
  "ocr_source_info": {
    "source_system": "ocr_cse",
    "source_task_id": "ocr_task_20260624_120000",
    "field_mappings_count": 12
  },
  // ... 现有字段保持不变 ...
}
```

### 4.2 数据库不新增表

所有 OCR 桥接信息存储在以下位置，数据库无需新增表：

| 数据 | 存储位置 |
|------|----------|
| 字段级 OCR 映射 | `.trace.json` 的每个 `trace_items[].ocr_*` 字段 |
| 任务级 OCR 来源 | `meta.json` 的 `ocr_source_info` |
| 请求时传入的映射 | `tasks/{task_id}/meta.json` 暂存 |

---

## 五、生成引擎修改

### 5.1 generation_runner.py 修改

**位置**: `backend/app/engine/generation_runner.py`

**修改点 1**: 构造 Context 时接收 OCR 映射参数

```python
class GenerationRunner:
    async def run(
        self,
        task_id: str,
        template_id: int,
        primary_key_values: list[str],
        ocr_field_mappings: list[dict] | None = None,  # 🆕
        force: bool = False,
        ai_enabled: bool = True,
    ) -> None:
        # ... 现有逻辑 ...
        self.ocr_field_mappings = ocr_field_mappings or []
```

**修改点 2**: 构建 TraceItem 时注入 OCR 桥接字段

```python
def _build_trace_item(self, source: dict, ocr_mapping: dict | None = None) -> TraceItem:
    item = TraceItem(
        # ... 现有字段 ...
    )
    
    # 🆕 注入 OCR 桥接信息
    if ocr_mapping:
        item.source_system = "ocr_cse"
        item.ocr_source_task_id = ocr_mapping.get("source_task_id", "")
        item.ocr_source_file_id = ocr_mapping.get("source_file_id", "")
        item.ocr_source_page_id = ocr_mapping.get("source_page_id", "")
        item.ocr_source_block_ids = ocr_mapping.get("source_block_ids", [])
        item.ocr_source_bbox = ocr_mapping.get("source_bbox")
        item.ocr_source_image_url = ocr_mapping.get("source_image_url", "")
        item.ocr_source_image_width = ocr_mapping.get("source_image_width", 0)
        item.ocr_source_image_height = ocr_mapping.get("source_image_height", 0)
    
    return item
```

### 5.2 trace_builder.py 修改

**位置**: `backend/app/engine/trace_builder.py`

**修改点**: 写入 `.trace.json` 时包含 OCR 桥接字段

```python
def build_trace_file(
    trace_items: list[TraceItem],
    ocr_source_info: dict | None = None,  # 🆕
) -> TraceFile:
    trace_file = TraceFile(
        # ... 现有字段 ...
        ocr_source_info=ocr_source_info if ocr_source_info else None,
    )
    return trace_file
```

### 5.3 trace_map.py 修改

**位置**: `backend/app/engine/trace_map.py`

**修改点**: 构建溯源映射时保留 OCR 桥接信息

```python
def build_field_trace_detail(
    trace_item: TraceItem,
    source_record: SourceRecordView,
) -> FieldTraceDetail:
    detail = FieldTraceDetail(
        # ... 现有字段 ...
        
        # 🆕 保留 OCR 溯源字段
        source_system=trace_item.source_system,
        ocr_source_task_id=trace_item.ocr_source_task_id,
        ocr_source_file_id=trace_item.ocr_source_file_id,
        ocr_source_page_id=trace_item.ocr_source_page_id,
        ocr_source_block_ids=trace_item.ocr_source_block_ids,
        ocr_source_bbox=trace_item.ocr_source_bbox,
        ocr_source_image_url=trace_item.ocr_source_image_url,
        ocr_source_image_width=trace_item.ocr_source_image_width,
        ocr_source_image_height=trace_item.ocr_source_image_height,
    )
    return detail
```

---

## 六、Service 层修改

### 6.1 task_service.py 新增方法

```python
class TaskService:
    async def auto_create_and_generate(
        self,
        task_name: str,
        template_id: int,
        files: list[UploadFileSpec],
        ai_enabled: bool = True,
        source_task_id: str | None = None,
        ocr_field_mappings: list[dict] | None = None,
    ) -> dict:
        """一键创建任务、上传文件、校验、生成"""
        
        # 1. 创建任务
        task = self.create_task(
            CreateTaskRequest(
                task_name=task_name, 
                template_id=template_id, 
                ai_enabled=ai_enabled
            )
        )
        task_id = task["task_id"]
        
        # 2. 批量上传文件
        for file_spec in files:
            self.upload_file(task_id, file_spec.table_name, file_spec.file_data)
        
        # 3. 执行校验
        validation = self.validate_task(task_id)
        if validation["status"] == "failed":
            return self._build_error_response(
                "VALIDATION_FAILED", "校验未通过", validation
            )
        
        # 4. 如果提供了 OCR 映射，保存到 meta.json
        if source_task_id or ocr_field_mappings:
            self._save_ocr_mappings_to_meta(
                task_id, source_task_id, ocr_field_mappings
            )
        
        # 5. 异步启动生成（传入 ocr_field_mappings）
        asyncio.create_task(self._start_generation(
            task_id, ocr_field_mappings=ocr_field_mappings
        ))
        
        return {
            "task_id": task_id,
            "task_name": task_name,
            "template_id": template_id,
            "status": "running",
            "file_upload_results": [...],
            "validation_summary": validation.get("summary", {}),
            "message": "任务已创建并开始生成"
        }
```

---

## 七、API 路由层修改

### 7.1 `backend/app/api/tasks.py` 新增路由

```python
from app.schemas.task_models import AutoCreateAndGenerateRequest

@router.post("/auto-create-and-generate")
async def auto_create_and_generate(request: AutoCreateAndGenerateRequest):
    """一键创建任务、上传文件、校验、生成"""
    return success_response(
        await task_service.auto_create_and_generate(
            task_name=request.task_name,
            template_id=request.template_id,
            files=request.files,
            ai_enabled=request.ai_enabled,
            source_task_id=request.source_task_id,
            ocr_field_mappings=request.ocr_field_mappings,
        )
    )

@router.post("/{task_id}/upload-batch")
async def upload_batch(
    task_id: str,
    table_names: str = Form(...),  # JSON array string
    files: list[UploadFile] = File(...),
):
    """批量上传文件"""
    table_name_list = json.loads(table_names)
    results = []
    for table_name, file in zip(table_name_list, files):
        result = await task_service.upload_file(task_id, table_name, file)
        results.append(result)
    return success_response({
        "task_id": task_id,
        "results": results,
        "uploaded_count": sum(1 for r in results if r.get("uploaded")),
        "failed_count": sum(1 for r in results if not r.get("uploaded")),
    })
```

### 7.2 Request Schema

**位置**: `backend/app/schemas/task_models.py`

```python
class UploadFileSpec(BaseModel):
    table_name: str
    file_data: str  # base64 encoded

class OcrFieldMapping(BaseModel):
    var_path: str
    source_task_id: str
    source_file_id: str
    source_page_id: str = ""
    source_block_ids: list[str] = []
    source_bbox: dict | None = None
    source_image_url: str = ""
    source_image_width: int = 0
    source_image_height: int = 0

class AutoCreateAndGenerateRequest(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=200)
    template_id: int = Field(..., ge=1)
    ai_enabled: bool = True
    source_task_id: str | None = None
    files: list[UploadFileSpec] = Field(..., min_length=1)
    ocr_field_mappings: list[OcrFieldMapping] = []
```

---

## 八、前端修改（仅 trace_detail 面板适配）

### 8.1 TraceDetailPanel.vue 适配

当 `traceItem.source_system === "ocr_cse"` 时，将现有 `FieldTracePanel` 替换为新的图片溯源面板逻辑：

```vue
<!-- 在 TraceDetailPanel.vue 中 -->
<FieldTracePanel v-if="traceItem.trace_kind === 'field' && traceItem.source_system !== 'ocr_cse'" :trace="traceItem" />

<!-- 🆕 新增：OCR 溯源面板 -->
<FieldOcrTracePanel v-else-if="traceItem.trace_kind === 'field' && traceItem.source_system === 'ocr_cse'" :trace="traceItem" />
```

新增 `FieldOcrTracePanel.vue` 组件（由 OCR-CSE 前端实现，GS 只做适配预留）：

```vue
<template>
  <div class="field-ocr-trace">
    <!-- OCR-CSE 会通过 doc_id + trace_id 调用 /api/documents/{doc_id}/ocr-provenance/{trace_id} -->
    <!-- 实际渲染由 OCR-CSE 的 EvidencePreviewPanel 完成 -->
    <el-empty description="OCR 溯源请跳转到贷前集约系统查看" />
  </div>
</template>
```

> **说明**: 由于 OCR-CSE 自行承载最终溯源展示页面，GS 的前端 TraceDetailPanel 仅做简单的降级提示。OCR-CSE 的 `DocGenerationPage` 会完全接管预览+溯源布局。

---

## 九、文件修改清单

| 文件路径 | 修改类型 | 修改内容 |
|----------|----------|----------|
| `backend/app/models/trace_models.py` | 修改 | TraceItem 增加 OCR 桥接字段 |
| `backend/app/models/trace_models.py` | 修改 | FieldTraceDetail 增加 OCR 桥接字段 |
| `backend/app/models/trace_models.py` | 修改 | TraceFile 增加 ocr_source_info |
| `backend/app/schemas/task_models.py` | 修改 | 新增 UploadFileSpec, OcrFieldMapping, AutoCreateAndGenerateRequest |
| `backend/app/schemas/task_models.py` | 修改 | 新增 UploadBatchResponse |
| `backend/app/api/tasks.py` | 修改 | 新增 auto_create_and_generate 路由 |
| `backend/app/api/tasks.py` | 修改 | 新增 upload_batch 路由 |
| `backend/app/api/documents.py` | 修改 | 新增 get_ocr_provenance 路由 |
| `backend/app/services/task_service.py` | 修改 | 新增 auto_create_and_generate() 方法 |
| `backend/app/services/task_service.py` | 修改 | 新增 _save_ocr_mappings_to_meta() 方法 |
| `backend/app/engine/generation_runner.py` | 修改 | run() 接收 ocr_field_mappings 参数 |
| `backend/app/engine/generation_runner.py` | 修改 | _build_trace_item() 注入 OCR 桥接字段 |
| `backend/app/engine/trace_builder.py` | 修改 | build_trace_file() 接收 ocr_source_info |
| `backend/app/engine/trace_map.py` | 修改 | build_field_trace_detail() 保留 OCR 桥接字段 |
| `frontend/src/components/TraceDetailPanel.vue` | 修改 | 新增 FieldOcrTracePanel 条件判断 |

### 无需修改的文件

- **数据库 schema.sql**: 无需新增表（桥接信息存储在 trace.json）
- **config/entity_schema.xlsx**: 不涉及
- **config/template_relation.xlsx**: 不涉及
- **现有 tests**: 新增字段有默认值，现有测试完全兼容

---

## 十、测试策略

### 10.1 单元测试

| 测试项 | 说明 |
|--------|------|
| `test_trace_model_ocr_fields` | 验证 TraceItem OCR 桥接字段默认值 |
| `test_auto_create_and_generate` | 验证一键创建任务+上传+校验+生成 |
| `test_upload_batch` | 验证批量上传正确性 |
| `test_ocr_trace_persistence` | 验证 trace.json 写入和读取 OCR 桥接信息 |

### 10.2 集成测试

| 测试项 | 说明 |
|--------|------|
| `test_api_e2e_with_ocr` | 模拟 OCR-CSE 调用 auto-create-and-generate |
| `test_ocr_provenance_api` | 验证 GET /api/documents/{doc_id}/ocr-provenance/{trace_id} |

---

## 十一、部署注意事项

1. **端口冲突**: 确保 AI-Document-GS 与 AI-OCR-CSE 运行在不同端口（GS:8000, CSE:8001）
2. **CORS 配置**: AI-Document-GS 需要配置 CORS 允许 AI-OCR-CSE 的来源
3. **文件锁**: 两个系统不要同时操作同一文件
4. **日志**: 生成日志中标注 `source_system=ocr_cse` 方便问题排查