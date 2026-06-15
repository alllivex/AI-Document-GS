# AI 智能文档生成系统

## 项目启动

建议分别打开两个终端启动后端和前端。

### 1. 启动后端

首次运行前先安装 Python 依赖：

```powershell
cd F:\资料\AI\AI-Document-GS\backend
pip install -r requirements.txt
```

启动 FastAPI 服务：

```powershell
cd F:\资料\AI\AI-Document-GS\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端默认地址：

```text
http://127.0.0.1:8000
```

### 2. 启动前端

首次运行前先安装 Node 依赖：

```powershell
cd F:\资料\AI\AI-Document-GS\frontend
npm install
```

启动 Vite 开发服务：

```powershell
cd F:\资料\AI\AI-Document-GS\frontend
npm run dev
```

前端默认地址：

```text
http://127.0.0.1:5173
```

前端开发服务已配置 `/api` 代理到后端：

```text
http://127.0.0.1:8000
```
