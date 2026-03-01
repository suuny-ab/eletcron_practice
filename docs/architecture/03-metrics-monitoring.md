# 监控系统设计文档

## 概述

系统内置了完整的指标监控体系，提供实时指标采集、时序数据存储、持久化和可视化展示能力。整体采用 **Prometheus 风格指标命名** + **环形缓冲区时序存储** + **JSONL 持久化** + **recharts 前端可视化** 的架构。

**技术栈**：

| 组件 | 技术 |
|------|------|
| 指标采集器 | MetricsCollector（自研，线程安全） |
| 时序存储 | deque 环形缓冲区 + JSONL 文件 |
| HTTP 中间件 | Starlette BaseHTTPMiddleware |
| 前端图表 | recharts |
| UI 组件 | Ant Design |

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         采集层                                    │
│  ┌───────────────┐ ┌──────────────┐ ┌───────────────────────┐   │
│  │MetricsMiddle- │ │LLMTaskService│ │UnifiedAgent           │   │
│  │ware (HTTP)    │ │(LLM 调用)    │ │(Agent 工作流+节点)    │   │
│  └───────┬───────┘ └──────┬───────┘ └───────────┬───────────┘   │
│          │                │                     │               │
│  ┌───────┴───────┐ ┌──────┴──────┐ ┌───────────┴───────────┐   │
│  │IndexService   │ │UnifiedMemory│ │SessionMetadataManager │   │
│  │(RAG 索引/检索)│ │(记忆操作)   │ │(会话生命周期)         │   │
│  └───────┬───────┘ └──────┬──────┘ └───────────┬────────────┘   │
└──────────┼────────────────┼─────────────────────┼───────────────┘
           │                │                     │
           ▼                ▼                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                   MetricsCollector (全局单例)                      │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ _counters       │  │ _histograms      │  │ _timeseries_   │  │
│  │ (计数器)        │  │ (直方图)         │  │  buffer (环形) │  │
│  └─────────────────┘  └──────────────────┘  └───────┬────────┘  │
│                                                      │           │
│  ┌──────────────────────────────────────────────────┐│           │
│  │ _snapshot_worker (后台线程, 10s 间隔)             ││           │
│  │  → 创建快照 → 写入缓冲区 → 批量持久化            ││           │
│  └──────────────────────────────────────────────────┘│           │
└──────────────────────────────────────────────────────┼───────────┘
                                                       │
                                                       ▼
                                              .data/metrics.jsonl
                                              (JSONL 持久化, 7天保留)
                                                       │
                                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                        API 层                                     │
│  GET /api/health/detail     — 详细健康检查（含服务状态）           │
│  GET /api/health/metrics    — 实时指标快照（counters+histograms） │
│  GET /api/health/timeseries — 时序数据（支持 1-60 分钟窗口）      │
└──────────────────────────────────────────────────────────────────┘
                                                       │
                                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                       前端可视化层                                 │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐  │
│  │ metrics.js       │  │ MetricsDashboard                     │  │
│  │ (API 客户端)     │→│ 系统概览 + 服务状态 + 4个趋势图      │  │
│  └──────────────────┘  │ + HTTP/RAG/LLM/Agent/会话指标卡片    │  │
│                        └──────────────────────────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐  │
│  │ TimeSeriesChart  │  │ MetricsPage                          │  │
│  │ (通用图表组件)   │  │ (全屏监控页面)                       │  │
│  └──────────────────┘  └──────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## 后端实现

### 1. 指标采集器（MetricsCollector）

**文件**：`backend/infrastructure/metrics/collector.py`

#### 数据结构

| 类型 | 类 | 字段 | 用途 |
|------|-----|------|------|
| Counter | `CounterMetric` | value, last_updated | 累计计数（请求数、错误数） |
| Histogram | `HistogramMetric` | count, total, min_value, max_value, avg | 耗时分布统计 |

#### 核心 API

```python
metrics = get_metrics()

# 计数器：递增
metrics.increment("http.requests.count")
metrics.increment("rag.index.files_indexed", 10)

# 直方图：记录观察值
metrics.observe("rag.retrieval.duration_seconds", elapsed)

# 计时器：上下文管理器，自动记录耗时
with metrics.timer("agent.node.classify.duration_seconds"):
    result = classify(input)

# 查询
snapshot = metrics.get_snapshot()          # 所有指标快照
points = metrics.get_timeseries(minutes=30) # 最近30分钟时序
```

#### 时序数据存储

- **环形缓冲区**：`deque(maxlen=360)`，存储最近 1 小时数据（10s x 360 = 3600s）
- **快照线程**：`_snapshot_worker()` 守护线程，每 10 秒创建一次指标快照
- **缓冲区写入**：快照追加到 `_timeseries_buffer`
- **线程安全**：`_lock`（指标读写）+ `_timeseries_lock`（缓冲区访问）

#### JSONL 持久化

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `SNAPSHOT_INTERVAL_SECONDS` | 10 | 快照间隔 |
| `BUFFER_SIZE` | 360 | 环形缓冲区大小 |
| `PERSISTENCE_BATCH_SIZE` | 10 | 批量写入阈值（10 个点/批） |
| `DATA_RETENTION_DAYS` | 7 | 数据保留天数 |

**持久化流程**：
1. 快照线程每 10s 创建数据点，追加到 `_pending_writes`
2. 累积达到 10 个点时，批量 append 到 `metrics.jsonl`
3. 启动时 `_load_from_disk()` 加载最近 1 小时数据到内存
4. 超过 7 天的数据自动清理（原子写入：先写 `.tmp` 再 rename）

**数据格式**（每行一个 JSON）：
```json
{"timestamp": 1709276400.0, "counters": {"http.requests.count": 150, "llm.calls": 12}, "histograms": {"http.requests.duration_seconds": {"count": 150, "avg": 0.023, "min": 0.001, "max": 0.5}}}
```

### 2. HTTP 中间件（MetricsMiddleware）

**文件**：`backend/app/middleware/metrics_middleware.py`

基于 `BaseHTTPMiddleware` 实现，自动采集所有 HTTP 请求的指标。

**采集指标**：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `http.requests.count` | Counter | 总请求数 |
| `http.requests.{GET\|POST\|...}.count` | Counter | 按 HTTP 方法计数 |
| `http.responses.{2xx\|4xx\|5xx}.count` | Counter | 按状态码段计数 |
| `http.errors.count` | Counter | 5xx 错误数 |
| `http.requests.duration_seconds` | Histogram | 请求耗时分布 |

**设计细节**：
- 使用 `time.perf_counter()` 高精度计时
- 跳过 `/api/health/*` 路径，避免监控自身产生噪声
- 异常时也记录指标（在 except 块中记录为 5xx）

### 3. 健康检查端点

**文件**：`backend/app/api/routes/health_routes.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 基础健康检查（status, version, uptime） |
| `/api/health/detail` | GET | 详细健康检查，含各服务状态 |
| `/api/health/metrics` | GET | 实时指标快照（counters + histograms） |
| `/api/health/timeseries?minutes=60` | GET | 时序数据（1-60 分钟窗口） |

**服务状态检查**（`/api/health/detail`）：

| 服务 | 检查方式 |
|------|---------|
| config | 验证 ConfigContext 和 vault_path 是否配置 |
| rag | 检查索引状态、已索引文件数和分块数 |
| ai | 通过 DI 容器 resolve `IModelProvider`，检查是否可用 |

**时序数据响应格式**（`/api/health/timeseries`）：
```json
{
  "interval_seconds": 10,
  "data_points": [
    {
      "timestamp": 1709276400.0,
      "counters": {"http.requests.count": 150},
      "histograms": {"http.requests.duration_seconds": {"count": 150, "avg": 0.023, "min": 0.001, "max": 0.5}}
    }
  ]
}
```

### 4. 业务指标埋点

#### LLM 服务（`backend/domain/ai/services/llm_task_service.py`）

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `llm.call.duration_seconds` | Histogram | 全局 LLM 调用耗时 |
| `llm.calls` | Counter | 全局 LLM 调用总数 |
| `llm.{task_type}.duration_seconds` | Histogram | 按任务类型耗时 |
| `llm.{task_type}.calls` | Counter | 按任务类型调用次数 |
| `llm.{task_type}.chunks` | Counter | 流式输出块数 |

在 `stream()` 和 `invoke()` 的 `finally` 块中记录，确保异常时也能采集。

#### Agent 工作流（`backend/domain/ai/agent/graphs/unified_agent.py`）

**节点级指标**（通过 `metrics.timer()` 上下文管理器）：

| 指标名 | 说明 |
|--------|------|
| `agent.node.load_history.duration_seconds` | 历史加载耗时 |
| `agent.node.classify.duration_seconds` | 意图分类耗时 |
| `agent.node.check_doc.duration_seconds` | 文档检查耗时 |
| `agent.node.analyze.duration_seconds` | 问题分析耗时 |
| `agent.node.retrieve.duration_seconds` | 知识检索耗时 |
| `agent.node.evaluate.duration_seconds` | 结果评估耗时 |
| `agent.node.rewrite.duration_seconds` | 策略优化耗时 |

**工作流级指标**：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `agent.workflow.count` | Counter | 工作流执行次数 |
| `agent.workflow.duration_seconds` | Histogram | 工作流总耗时 |
| `agent.workflow.error.count` | Counter | 工作流错误次数 |
| `agent.intent.{type}.count` | Counter | 意图类型统计 |

#### RAG 模块

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `rag.retrieval.duration_seconds` | Histogram | 检索耗时 |
| `rag.retrieval.queries` | Counter | 检索查询次数 |
| `rag.index.duration_seconds` | Histogram | 索引耗时 |
| `rag.index.files_indexed` | Counter | 已索引文件数 |
| `rag.index.chunks_created` | Counter | 已创建分块数 |

#### 会话与记忆

| 指标名 | 类型 | 来源 |
|--------|------|------|
| `memory.history.load.count` | Counter | UnifiedMemory |
| `memory.turn.add.count` | Counter | UnifiedMemory |
| `memory.summary.rollup.count` | Counter | UnifiedMemory |
| `session.create.count` | Counter | SessionMetadataManager |
| `session.delete.count` | Counter | SessionMetadataManager |

## 前端实现

### 1. API 客户端（metrics.js）

**文件**：`frontend/src/api/metrics.js`

```javascript
fetchHealthDetail()          // GET /api/health/detail
fetchMetrics()               // GET /api/health/metrics
fetchTimeseries(minutes)     // GET /api/health/timeseries?minutes=N
```

配置：baseURL 从 `VITE_API_BASE_URL` 读取，超时 10s。

### 2. 时序图表组件（TimeSeriesChart）

**文件**：`frontend/src/components/Metrics/TimeSeriesChart.jsx`

基于 recharts 封装的通用时序可视化组件。

**Props**：

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dataPoints` | Array | `[]` | 后端时序数据点 |
| `series` | Array | `[]` | 系列定义 `[{key, label, extract, color}]` |
| `height` | Number | 240 | 图表高度 |
| `unit` | String | `''` | Y 轴单位后缀 |
| `areaMode` | Boolean | `true` | 面积图模式 |

**series 定义示例**：
```javascript
const HTTP_SERIES = [
  {
    key: 'http_req',
    label: 'HTTP 请求数',
    extract: (dp) => dp.counters?.['http.requests.count'] ?? 0,
    color: '#1890ff',
  },
];
```

**特性**：
- `useMemo` 缓存数据转换，避免重复计算
- 时间轴格式化：轴标签 `HH:MM`，Tooltip `HH:MM:SS`
- 支持多系列显示，8 色预设调色板
- 空数据友好提示

### 3. 监控仪表盘（MetricsDashboard）

**文件**：`frontend/src/components/RAGDebug/MetricsDashboard.jsx`

**布局结构**：

```
┌────────────────────────────────────────────────────┐
│ 系统指标仪表盘          [时间窗口] [自动刷新] [刷新] │
├────────────────────────────────────────────────────┤
│ 系统概览: 状态 | 运行时间 | Python版本 | 平台       │
├────────────────────────────────────────────────────┤
│ 服务状态: 配置服务 | RAG 服务 | AI 服务             │
├──────────────────────┬─────────────────────────────┤
│ HTTP 请求趋势        │ LLM 耗时趋势               │
├──────────────────────┼─────────────────────────────┤
│ RAG 检索耗时趋势     │ Agent 工作流耗时趋势        │
├──────────────────────┴─────────────────────────────┤
│ HTTP 指标: 总请求数 | 请求耗时 | 5xx 错误数         │
│ RAG 指标:  检索耗时 | 查询次数 | 索引统计           │
│ LLM 指标:  调用次数 | Token 量 | 调用耗时           │
│ Agent 指标: 执行次数 | 工作流耗时 | 错误数          │
│ 会话/记忆: 会话创建 | 对话轮次                      │
└────────────────────────────────────────────────────┘
```

**交互功能**：
- **时间窗口选择**：5 / 15 / 30 / 60 分钟（Segmented 组件）
- **自动刷新**：10s 轮询（可手动开关）
- **手动刷新**：按钮触发
- **加载状态**：Spin + 错误 Alert

**4 类时序趋势图**：

| 图表 | 系列 | 提取逻辑 |
|------|------|---------|
| HTTP 请求趋势 | 请求数 + 5xx 错误 | `counters['http.requests.count']` |
| LLM 耗时趋势 | 平均调用耗时(ms) | `histograms['llm.call.duration_seconds'].avg * 1000` |
| RAG 检索耗时 | 检索平均耗时(ms) | `histograms['rag.retrieval.duration_seconds'].avg * 1000` |
| Agent 工作流 | 工作流平均耗时(ms) | `histograms['agent.workflow.duration_seconds'].avg * 1000` |

### 4. 监控页面（MetricsPage）

**文件**：`frontend/src/pages/MetricsPage.jsx`

全屏独立监控页面，内嵌 MetricsDashboard 组件。

## 指标命名规范

遵循 Prometheus 风格命名约定：
- 小写字母 + 点号分隔层级
- 包含单位后缀：`_seconds`、`_count`
- 层级结构：`{domain}.{component}.{metric_name}`

**完整指标清单**：

| 指标名 | 类型 | 来源 |
|--------|------|------|
| `http.requests.count` | Counter | MetricsMiddleware |
| `http.requests.{method}.count` | Counter | MetricsMiddleware |
| `http.responses.{status_group}.count` | Counter | MetricsMiddleware |
| `http.errors.count` | Counter | MetricsMiddleware |
| `http.requests.duration_seconds` | Histogram | MetricsMiddleware |
| `llm.call.duration_seconds` | Histogram | LLMTaskService |
| `llm.calls` | Counter | LLMTaskService |
| `llm.{task_type}.duration_seconds` | Histogram | LLMTaskService |
| `llm.{task_type}.calls` | Counter | LLMTaskService |
| `llm.{task_type}.chunks` | Counter | LLMTaskService |
| `agent.workflow.count` | Counter | UnifiedAgent |
| `agent.workflow.duration_seconds` | Histogram | UnifiedAgent |
| `agent.workflow.error.count` | Counter | UnifiedAgent |
| `agent.intent.{type}.count` | Counter | UnifiedAgent |
| `agent.node.{name}.duration_seconds` | Histogram | UnifiedAgent |
| `rag.retrieval.duration_seconds` | Histogram | RetrievalService |
| `rag.retrieval.queries` | Counter | RetrievalService |
| `rag.index.duration_seconds` | Histogram | IndexService |
| `rag.index.files_indexed` | Counter | IndexService |
| `rag.index.chunks_created` | Counter | IndexService |
| `memory.history.load.count` | Counter | UnifiedMemory |
| `memory.turn.add.count` | Counter | UnifiedMemory |
| `memory.summary.rollup.count` | Counter | UnifiedMemory |
| `session.create.count` | Counter | SessionMetadataManager |
| `session.delete.count` | Counter | SessionMetadataManager |

## 设计决策

### 为何选择环形缓冲 + JSONL？

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| Redis | 高性能、TTL 自动过期 | 需要外部依赖 | 本地桌面应用不适合引入 |
| SQLite | 结构化查询 | 频繁写入开销大 | 10s 写入频率不适合 |
| **JSONL** | **简单、追加友好、无依赖** | 查询需顺序扫描 | **查询需求简单，按时间范围过滤即可** |

### 为何使用前端轮询而非 WebSocket？

- 监控数据 10s 刷新一次，实时性要求不高
- 轮询实现简单，无需维护长连接
- 与现有 REST API 架构一致

## Bug 修复记录

### 1. LLM 图表不更新

**问题**：MetricsDashboard 中 LLM 耗时趋势图始终为空。

**原因**：`LLMTaskService` 只记录了任务级指标 `llm.{task_type}.duration_seconds`，未记录前端图表查询的全局指标 `llm.call.duration_seconds`。

**修复**：在 `stream()` 和 `invoke()` 的 `finally` 块中添加全局指标记录：
```python
metrics.observe("llm.call.duration_seconds", elapsed)
metrics.increment("llm.calls")
```

### 2. AI 服务健康检查误报"未初始化"

**问题**：`/api/health/detail` 显示 AI 服务状态为 "未初始化"。

**原因**：原代码使用 `hasattr(request.app.state, "ai_service")` 判断，但新架构已移除该属性，改为 DI 容器管理。

**修复**：改用 DI 容器解析：
```python
provider = get_container().resolve(IModelProvider)
```

### 3. 思考过程显示错乱

**问题**：`checking_doc` 阶段的 thinking 消息覆盖了 `classifying` 阶段的内容。

**原因**：
1. `check_doc` 节点只发 thinking 消息，没有先发 status 消息创建新步骤
2. 前端 `ThinkingTimeline` 收到 thinking 时直接覆盖上一步的内容

**修复**：
- 后端 `check_doc.py`：在 thinking 前添加 `{"type": "status", "data": {"stage": "checking_doc"}}` 状态消息
- 前端 `ThinkingTimeline.jsx`：`STAGE_LABELS` 添加 `checking_doc: '文档检查'`
- 前端 thinking 处理逻辑从覆盖改为追加（`lastStep.thinking += '\n' + msg.content`）

### 4. 重启后对话框不在底部

**问题**：应用重启后，聊天区域显示第一条消息而非最新消息。

**原因**：历史消息加载后立即调用 `scrollToBottom`，但 DOM 尚未完成渲染。

**修复**：使用 `requestAnimationFrame` 延迟滚动，并采用 `behavior: 'instant'` 避免动画闪烁：
```javascript
requestAnimationFrame(() => {
  endRef.current?.scrollIntoView({ behavior: 'instant' });
});
```

### 5. RAG 增量索引后 Marker 不同步

**问题**：增量索引完成后 `index_marker.json` 的 `chunk_count` 未更新，重启时误判为数据不一致，触发全量重建。

**修复**：新增 `_sync_marker_to_actual()` 方法，在每次增量索引操作后同步 marker：
```python
def _sync_marker_to_actual(self):
    actual_count = self._vectorstore._collection.count()
    marker = self._load_index_marker()
    file_count = marker.get("file_count", 0) if marker else 0
    self._write_index_marker(file_count=file_count, chunk_count=actual_count)
```

> 详见 [02-rag-design.md](02-rag-design.md) 的"索引标记同步机制"章节。

## UX 改进：智能滚动检测

**文件**：`frontend/src/components/AgentSidebar/AgentSidebar.jsx`

**问题**：流式生成时，每个 chunk 都触发 `scrollToBottom`，用户向上查看历史内容时被强制拉回底部。

**解决方案**：基于滚动位置的状态感知自动滚动。

**核心机制**：

| 组件 | 作用 |
|------|------|
| `chatContainerRef` | 聊天容器 DOM 引用 |
| `userScrolledUpRef` | 用户是否主动上翻标记 |
| `initialScrollDoneRef` | 初始滚动是否完成标记 |

**检测逻辑**（`handleChatScroll`）：
```javascript
const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
userScrolledUpRef.current = distanceFromBottom > 80; // 80px 阈值
```

**行为规则**：
1. **初始加载**：使用 `requestAnimationFrame` + `behavior: 'instant'` 滚动到底部
2. **流式接收**：仅在 `!userScrolledUpRef.current` 时自动滚动（`behavior: 'smooth'`）
3. **用户发送消息**：重置 `userScrolledUpRef = false`，恢复自动滚动
