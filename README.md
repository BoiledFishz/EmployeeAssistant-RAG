# 企业雇员助手 RAG API 原型

这是一个面向 HR、行政和公司政策问答的教学型 RAG 原型。当前代码已按后端常见三层结构拆分：

```text
app/
├── main.py                     # FastAPI app、/health、依赖装配
├── routers/                    # Router 层：只处理 HTTP 入参/出参
│   ├── query.py                # POST /query
│   └── ingest.py               # POST /ingest
├── services/                   # Service 层：业务编排
│   ├── rag_service.py          # 查询改写、缓存、检索、证据门控、生成回答
│   └── ingest_service.py       # 文档入库业务
├── repositories/               # Data/Repository 层：数据访问
│   └── vector_store.py         # 内存向量/BM25 检索库，生产可替换为 ES/Milvus/pgvector
├── schemas/                    # API 请求/响应模型
│   ├── request.py
│   └── response.py
└── config/
    └── settings.py

src/employee_assistant/         # 可复用的 RAG 核心：chunking、retrieval、cache、loader
tests/
requirements.txt
```

## API

- `GET /health`：查看服务状态、文档数、chunk 数、知识库版本
- `POST /ingest`：把 HR/行政/政策文本加入知识库
- `POST /query`：基于当前知识库回答问题

## 安装和启动

如果你已经在 `.venv` 里面，不要再执行 `py -m venv .venv`。直接安装依赖：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install --no-build-isolation -e .
```

启动 API：

```powershell
uvicorn app.main:app --reload
```

打开：

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## 示例请求

先入库：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/ingest" `
  -ContentType "application/json" `
  -Body '{
    "title": "HR政策",
    "text": "# 年假\n员工每年享有十五天年假。年假申请至少提前三个工作日提交。",
    "allowed_groups": ["all-employees-cn"]
  }'
```

再查询：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/query" `
  -ContentType "application/json" `
  -Body '{
    "question": "年假有多少天？",
    "user_groups": ["all-employees-cn"]
  }'
```

也可以按文件入库：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/ingest" `
  -ContentType "application/json" `
  -Body '{
    "source_path": "data/hr.txt",
    "title": "hr",
    "allowed_groups": ["all-employees-cn"]
  }'
```

注意：项目里的 `data/hr.txt` 目前如果是空文件，`POST /ingest` 会返回 400；需要先把文档内容保存进去。

## 设计要点

- Chunking：结构感知 parent-child chunk。按 Markdown/编号标题切 section，再切较小窗口。
- Embedding：原型使用本地 hash embedding，方便离线演示；生产建议换 BGE-M3、bge-large-zh 或托管 embedding。
- Hybrid Search：原型已做 dense + BM25 + RRF 融合，并在检索前做 ACL 过滤。
- 降低幻觉：证据不足时拒答；回答必须带 citation；缓存 key 包含 tenant、权限组和知识库版本。
- 知识库更新：通过 `/ingest` 入库后重建内存索引；生产中可替换为增量索引和版本化发布。
- 缓存：Service 层使用 TTLCache；生产可换 Redis，并保留当前 cache key 维度。
- 多轮对话：`POST /query` 支持 `history` 和 `thread_id`，追问会用最近用户问题补全上下文。

