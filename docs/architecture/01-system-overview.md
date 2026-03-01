# 系统架构设计文档

## 项目概述

AI 知识库助手是一个基于 Electron + React + FastAPI 的桌面应用，集成了大语言模型（LLM）和 RAG 检索增强技术，提供智能化的 Markdown 笔记管理和 AI 辅助功能。

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 桌面框架 | Electron | ^40.2.1 |
| 前端 | React + Vite | ^19.2.0 |
| UI 组件 | Ant Design | ^6.2.3 |
| 后端 | FastAPI | 0.128.4 |
| AI 框架 | LangChain | 1.2.9 |
| 向量数据库 | ChromaDB | 1.5.1 |
| 检索 | rank-bm25 | 0.2.2 |
| LLM | 通义千问 (dashscope) | - |

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Electron 桌面应用                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    React 前端 (Vite)                          │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │ 文件树   │  │ 笔记编辑 │  │ AI 侧边栏│  │ 配置页面 │     │  │
│  │  │ FileTree │  │ Editor   │  │ AISidebar│  │ Config   │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │  ┌──────────┐  ┌────────────────┐                            │  │
│  │  │ 指标监控 │  │ 时序图表       │                            │  │
│  │  │ Metrics  │  │ TimeSeriesChart│                            │  │
│  │  └──────────┘  └────────────────┘                            │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐     │  │
│  │  │               自定义 Hooks                           │     │  │
│  │  │  useFileTree | useAIChat | useRAG | useNoteEditor   │     │  │
│  │  └─────────────────────────────────────────────────────┘     │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐     │  │
│  │  │               API 调用层                             │     │  │
│  │  │  knowledge.js | ai.js | config.js | metrics.js      │     │  │
│  │  └─────────────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              │ HTTP/REST API                        │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   FastAPI 后端服务                            │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐     │  │
│  │  │              Application Layer (应用层)              │     │  │
│  │  │                                                      │     │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │     │  │
│  │  │  │AI Routes │  │Knowledge │  │Config    │          │     │  │
│  │  │  │          │  │Routes    │  │Routes    │          │     │  │
│  │  │  └────┬─────┘  └────┬─────┘  └────┬─────┘          │     │  │
│  │  │       │             │             │                 │     │  │
│  │  │  ┌──────────┐  ┌──────────────────────────┐        │     │  │
│  │  │  │Health    │  │ MetricsMiddleware         │        │     │  │
│  │  │  │Routes    │  │ (HTTP 请求指标采集)       │        │     │  │
│  │  │  └────┬─────┘  └──────────────────────────┘        │     │  │
│  │  │       │             │             │                 │     │  │
│  │  │  ┌────┴─────────────┴─────────────┴────┐           │     │  │
│  │  │  │         Services (服务层)            │           │     │  │
│  │  │  │  AIService | KnowledgeService        │           │     │  │
│  │  │  └────────────────────────────────────┘           │     │  │
│  │  └─────────────────────────────────────────────────────┘     │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐     │  │
│  │  │               Domain Layer (领域层)                  │     │  │
│  │  │                                                      │     │  │
│  │  │  ┌──────────────────┐  ┌──────────────────┐         │     │  │
│  │  │  │   AI Domain      │  │ Knowledge Domain │         │     │  │
│  │  │  │                  │  │                  │         │     │  │
│  │  │  │ - ModelProvider  │  │ - RAGService     │         │     │  │
│  │  │  │ - ChatModel      │  │ - IndexService   │         │     │  │
│  │  │  │ - LLMTaskService │  │ - RetrievalSvc   │         │     │  │
│  │  │  │ - UnifiedAgent   │  │ - BM25Index      │         │     │  │
│  │  │  │ - UnifiedMemory  │  │                  │         │     │  │
│  │  │  │ - PromptFactory  │  │                  │         │     │  │
│  │  │  └──────────────────┘  └──────────────────┘         │     │  │
│  │  └─────────────────────────────────────────────────────┘     │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐     │  │
│  │  │          Infrastructure Layer (基础设施层)           │     │  │
│  │  │                                                      │     │  │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │     │  │
│  │  │  │Config  │ │Logging │ │Storage │ │Metrics │       │     │  │
│  │  │  │Context │ │        │ │        │ │        │       │     │  │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘       │     │  │
│  │  └─────────────────────────────────────────────────────┘     │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐     │  │
│  │  │                Core Layer (核心层)                   │     │  │
│  │  │                                                      │     │  │
│  │  │  Container | Interfaces | Exceptions | ErrorHandler │     │  │
│  │  └─────────────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │        外部服务/存储           │
              ├───────────────────────────────┤
              │  - ChromaDB (向量数据库)      │
              │  - 本地文件系统 (Markdown)    │
              │  - 通义千问 API               │
              └───────────────────────────────┘
```

## DDD 分层架构

### 1. Application Layer (应用层)

**职责**：处理 HTTP 请求，协调领域服务

```
app/
├── api/routes/          # API 路由
│   ├── ai_routes.py     # AI 功能路由
│   ├── knowledge_routes.py  # 知识库路由
│   ├── config_routes.py # 配置路由
│   └── health_routes.py # 健康检查与监控路由
│       # GET /health           - 基础健康检查
│       # GET /health/detail    - 详细服务状态
│       # GET /health/metrics   - 实时指标快照
│       # GET /health/timeseries - 时序数据 (1-60分钟)
├── middleware/           # 请求中间件
│   └── metrics_middleware.py  # HTTP 请求指标采集
├── services/            # 应用服务
│   ├── ai_service.py    # AI 服务编排
│   └── cleanup_service.py   # 会话清理
├── schemas/             # 数据模型
│   ├── requests.py      # 请求模型
│   └── responses.py     # 响应模型
└── dependencies.py      # 依赖注入
```

### 2. Domain Layer (领域层)

**职责**：封装核心业务逻辑

```
domain/
├── ai/                  # AI 领域
│   ├── models/          # 模型管理
│   │   ├── model_provider.py
│   │   └── chat_model_service.py
│   ├── agent/           # Agent 工作流（LangGraph 状态机）
│   │   ├── graphs/
│   │   │   └── unified_agent.py   # 统一 Agent 图（含节点级指标）
│   │   ├── nodes/       # 工作流节点（15 个节点实现）
│   │   └── state.py     # Agent 状态定义
│   ├── memory/          # 会话记忆
│   │   ├── unified_memory.py          # 统一记忆管理（JSONL + 摘要滚动）
│   │   └── session_metadata_manager.py # 会话元数据
│   ├── template/        # 提示词模板
│   │   └── config.py
│   └── services/
│       └── llm_task_service.py
```

> Agent 工作流支持 5 种意图（chitchat/rag_query/doc_advise/doc_edit/doc_format），
> 通过条件路由实现 RAG 检索循环、文档检查、权限校验等流程。
> 详细设计参见 [04-agent-workflow.md](04-agent-workflow.md)
│
└── knowledge/           # 知识库领域
    ├── rag/             # RAG 模块
    │   ├── rag_service.py
    │   ├── retrieval_service.py
    │   ├── index_service.py
    │   └── bm25_index.py
    ├── repositories/
    │   └── knowledge_repository.py
    └── services/
        └── knowledge_service.py
```

### 3. Infrastructure Layer (基础设施层)

**职责**：提供技术支撑服务

```
infrastructure/
├── config/              # 配置管理
│   └── config_context.py    # 配置上下文（热加载）
├── logging/             # 日志系统
│   └── logger.py        # 结构化日志
├── storage/             # 存储服务
│   ├── document_processor.py
│   └── file_watcher.py
└── metrics/             # 指标收集与监控
    └── collector.py     # MetricsCollector（计数器/直方图/时序缓冲/JSONL 持久化）
```

### 4. Core Layer (核心层)

**职责**：提供基础设施抽象

```
core/
├── container.py         # DI 容器
├── interfaces.py        # 接口定义
├── exceptions.py        # 自定义异常
└── exception_handlers.py    # 异常处理器
```

## 设计模式应用

### 1. 依赖注入容器

```python
# 容器配置
container.register(IConfigContext, ConfigContext, Lifetime.SINGLETON)
container.register(IModelProvider, ModelProvider, Lifetime.SINGLETON)
container.register(AIService, AIService, Lifetime.SINGLETON)

# 依赖解析
def get_ai_service() -> AIService:
    return get_container().resolve(AIService)
```

### 2. 观察者模式 - 配置热加载

```python
class ConfigContext:
    def __init__(self):
        self._listeners: dict[str, Callable] = {}
    
    def register_listener(self, listener, name):
        self._listeners[name] = listener
    
    def update(self, new_config, persist=True):
        # 通知所有监听器
        for listener in self._listeners.values():
            listener(new_config)
```

**监听器链**：
1. `configure_models` - 配置模型提供者
2. `update_prompts` - 更新提示词
3. `update_ai_service` - 更新 AI 服务
4. `update_cleanup_notes_root` - 更新清理服务
5. `init_rag_service` - 初始化 RAG 服务

### 3. 工厂模式 - 提示词配置

```python
class PromptConfigFactory:
    _configs = {
        "optimize": OptimizeConfig,
        "advise": AdviseConfig,
        "edit": EditConfig,
        "rag_qa": RagQaConfig,
        "rerank": RerankConfig,
    }
    
    @classmethod
    def get_config(cls, task_type: str):
        return cls._configs.get(task_type)
```

### 4. 门面模式 - RAG 服务

```python
class RAGService:
    """RAG 服务门面，简化外部调用"""
    
    def __init__(self, index_service, retrieval_service):
        self._index_service = index_service
        self._retrieval_service = retrieval_service
    
    def retrieve_context(self, question, top_k=3):
        return self._retrieval_service.retrieve_context(question, top_k)
    
    def start_indexing(self):
        self._index_service.start_indexing()
```

### 5. 仓储模式 - 知识库访问

```python
class IKnowledgeRepository(ABC):
    @abstractmethod
    def read_file(self, relative_path: str) -> FileReadResult: ...
    
    @abstractmethod
    def write_file(self, relative_path: str, content: str) -> FileWriteResult: ...
    
    @abstractmethod
    def get_file_tree(self) -> list[FileTreeNode]: ...
```

### 6. 可观测性 - 指标收集与监控

系统内置了完整的指标监控体系，通过 `MetricsCollector` 全局单例进行多层级指标采集：

**指标类型**：
- **Counter**：计数器（请求数、错误数、调用次数）
- **Histogram**：直方图（耗时分布，含 min/max/avg）
- **TimeSeries**：时序数据（环形缓冲区，10s 快照间隔）

**采集层级**：

| 层级 | 组件 | 典型指标 |
|------|------|---------|
| HTTP | MetricsMiddleware | http.requests.count, http.requests.duration_seconds |
| LLM | LLMTaskService | llm.call.duration_seconds, llm.calls |
| Agent | UnifiedAgent | agent.workflow.duration_seconds, agent.node.*.duration_seconds |
| RAG | IndexService / RetrievalService | rag.index.duration_seconds, rag.retrieval.queries |
| Memory | UnifiedMemory / SessionMetadataManager | memory.turn.add.count, session.create.count |

**持久化**：JSONL 格式存储到 `.data/metrics.jsonl`，支持 7 天数据保留和启动时恢复。

**前端可视化**：MetricsDashboard 提供 4 类时序趋势图（HTTP/LLM/RAG/Agent）、指标卡片和时间窗口选择（5/15/30/60 分钟）。

> 详细设计参见 [03-metrics-monitoring.md](03-metrics-monitoring.md)

## 流式响应架构

```
客户端
  │
  │ POST /ai/advise
  ▼
┌─────────────────┐
│   路由层        │  create_streaming_response()
│   (Routes)      │  → StreamingResponse
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   工具层        │  create_json_stream()
│   (Utils)       │  → 包装为 NDJSON 流
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   服务层        │  chat_suggestion_stream()
│   (Services)    │  → AsyncGenerator[str]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LLM 服务      │  stream()
│   (LLMTask)     │  → 原始文本流
└─────────────────┘
```

**流式数据格式（NDJSON）**：
```json
{"type": "chunk", "content": "文本片段"}
{"type": "chunk", "content": "更多内容"}
{"type": "complete", "status": "done"}
```

## 异常处理机制

```python
# 自定义异常层级
class AppException(Exception): ...
class NotFoundException(AppException): ...      # 404
class ValidationException(AppException): ...    # 400
class ExternalServiceException(AppException): ...  # 503
class ConfigError(AppException): ...            # 500

# 全局异常处理
@app.exception_handler(NotFoundException)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"error": str(exc)})
```

## 日志系统

```python
# 结构化日志
logger.info(
    "操作完成",
    extra={"context": LogContext(
        operation="rag.retrieval",
        duration_ms=elapsed * 1000,
        extra={"top_k": 3, "results": 3}
    )}
)

# 输出格式
# 2024-02-27T19:30:00 | INFO | domain.knowledge.rag | 操作完成 | op=rag.retrieval | 150.23ms | top_k=3 results=3
```

## 配置管理

```python
# 配置存储位置
CONFIG_PATH = "~/.myapp/config.json"

# 配置结构
{
    "obsidian_vault_path": "/path/to/vault",
    "api_key": "sk-xxx",
    "model_name": "qwen3-max",
    "prompts": {
        "optimize_system": "...",
        "advise_system": "..."
    }
}
```

## 前端架构

```
frontend/src/
├── api/                 # API 调用
│   ├── ai.js
│   ├── knowledge.js
│   ├── config.js
│   └── metrics.js       # 监控指标 API（健康检查/实时指标/时序数据）
├── components/          # 可复用组件
│   ├── FileTree/
│   ├── NoteEditor/
│   ├── AISidebar/       # AI 侧边栏（含智能滚动检测）
│   ├── Metrics/         # 监控组件
│   │   └── TimeSeriesChart.jsx  # 通用时序图表（recharts）
│   ├── RAGDebug/
│   │   └── MetricsDashboard.jsx # 指标监控仪表盘
│   └── common/
├── hooks/               # 自定义 Hooks
│   ├── useFileTree.js
│   ├── useAIChat.js
│   └── useRAG.js
├── pages/               # 页面组件
│   ├── Knowledge.jsx
│   ├── Config.jsx
│   └── MetricsPage.jsx  # 全屏指标监控页面
└── utils/               # 工具函数
```

## 测试架构

```
tests/
├── unit/                # 单元测试
│   ├── test_bm25_index.py
│   ├── test_retrieval_service.py
│   ├── test_index_service.py
│   └── test_document_processor.py
├── integration/         # 集成测试
│   └── test_api_routes.py
└── mocks/               # Mock 服务
    └── mock_services.py
```

## 部署架构

```
AI 知识库助手/
├── main.js              # Electron 主进程
├── frontend/dist/       # 前端构建产物
├── backend/             # Python 后端
│   └── .pydeps/         # 打包依赖
├── python/              # 嵌入式 Python
└── resources/           # 应用资源
```

**打包方式**：
- electron-builder 打包 Electron 应用
- 嵌入式 Python 运行时（无需用户安装）
- 依赖预打包到 .pydeps 目录
