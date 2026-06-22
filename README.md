# 企业雇员助手：LangGraph RAG 原型

这是一个面向 HR、行政和公司政策问答的教学型原型。它刻意把“编排”和“基础设施”分开：

- LangGraph：查询改写 → 缓存 → Hybrid Retrieval → 证据门控 → 回答。
- 本地检索器：无需 API Key 的 BM25 + 哈希向量，便于理解和测试。
- 生产环境：替换为 OpenSearch/Elasticsearch + BGE-M3/托管 embedding + reranker。
- 安全：检索前 ACL 过滤；缓存键包含租户、权限和知识库版本；答案必须附来源。
- 多轮：用 LangGraph checkpointer 保存对话状态，使用最近历史补全指代。

完整设计见 [docs/engineering-design.md](docs/engineering-design.md)。

## 运行

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
employee-assistant
```

程序默认读取项目内的 `data/hr.txt`。也可以通过环境变量指定其他文件：

```powershell
$env:EMPLOYEE_ASSISTANT_DATA="D:\Code\EmployeeAssistant-RAG\data\hr.txt"
employee-assistant
```

该文件必须包含实际文本；空文件会在启动时明确报错。支持 UTF-8、UTF-8
with BOM 和 GB18030 编码。修改文档后重启程序即可重新切分和建立索引。

如需继续使用内置样例：

```powershell
employee-assistant --demo
```

示例问题：

```text
年假有多少天？
那试用期员工呢？
上海办公室如何报销出租车？
```

## 目录

```text
src/employee_assistant/
  graph.py       LangGraph 状态图与节点
  retrieval.py   BM25、哈希向量、RRF 融合、ACL
  chunking.py    结构感知 parent-child 切分
  cache.py       权限与版本安全的 TTL 缓存
  document_loader.py 外部 HR 文本文档加载
  sample_data.py      `--demo` 使用的演示政策
tests/           标准库 unittest 测试
```

> 原型中的哈希向量和抽取式回答仅用于本地教学，不代表生产模型质量。
