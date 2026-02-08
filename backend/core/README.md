# 全局异常处理器方案

## 方案概述

本方案为FastAPI应用提供了完整的全局异常处理机制，统一管理所有异常的捕获、日志记录和响应格式。

## 架构设计

### 1. 自定义异常类 (`core/exceptions.py`)

定义了3种业务异常类，所有异常都继承自 `BaseBusinessException`：

```python
- BaseBusinessException: 基础业务异常类
- NotFoundException: 资源不存在 (404)
- ValidationException: 数据验证失败 (422)
- ExternalServiceException: 外部服务异常 (502)
```

每个异常包含：
- `message`: 错误消息
- `error_code`: 自定义错误码（可选）
- `status_code`: HTTP状态码

### 2. 全局异常处理器 (`core/exception_handlers.py`)

定义了5个异常处理器：

1. **`http_exception_handler`**: 处理 FastAPI 的 `HTTPException`
2. **`validation_exception_handler`**: 处理 Pydantic 验证异常
3. **`business_exception_handler`**: 处理自定义业务异常
4. **`generic_exception_handler`**: 处理所有未捕获的异常（兜底）

### 3. 日志系统 (`core/logger.py`)

统一的日志配置：

- 同时输出到控制台和文件
- 按日期滚动日志文件
- 分级别存储（info、error）
- 格式化日志输出
- 配置第三方库日志级别

## 使用方法

### 1. 在路由中抛出异常

```python
@router.post("/upload")
async def upload_file(file: UploadFile):
    if not file.filename:
        raise ValidationException("文件名不能为空")
    
    result = await save_uploaded_file(file.filename, contents)
    return DataResponse[FileUploadData](data=result, message="上传成功")
```

### 2. 在工具层抛出异常

```python
def read_file(filename: str):
    if not file_path.exists():
        raise NotFoundException(f"文件不存在: {filename}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content
```

### 3. 在服务层抛出异常

```python
async def optimize_markdown_layout_stream(self, filename: str):
    # 不捕获异常，直接透传
    file_info = read_file(filename)
    content = file_info["content"]
    async for chunk in self.markdown_optimizer.optimize_layout_stream(content):
        yield chunk
```

## 响应格式

### 成功响应

```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... },
  "timestamp": "2026-02-07T12:00:00"
}
```

### 错误响应

```json
{
  "success": false,
  "message": "文件不存在",
  "error_code": "NOT_FOUND",
  "timestamp": "2026-02-07T12:00:00"
}
```

## 日志输出

### 控制台日志

```
2026-02-07 12:00:00 | INFO     | backend.main | 应用初始化完成
2026-02-07 12:00:05 | WARNING  | backend.routes.file_routes | HTTP异常: 404 - 文件不存在
2026-02-07 12:00:10 | ERROR    | backend.services.ai_service | 排版优化失败: AI服务不可用
```

### 文件日志

- `logs/all_2026-02-07.log`: 所有日志
- `logs/error_2026-02-07.log`: 错误日志

## 异常处理流程

### 非流式响应

```
路由层 -> 工具层/服务层 -> 抛出异常
                           ↓
                  全局异常处理器捕获
                           ↓
                    记录日志
                           ↓
                    返回统一错误响应（JSONResponse）
```

### 流式响应

```
路由层 -> 流式工具层（stream_utils）-> 服务层 -> AI引擎层
                                            ↓
                              所有层直接抛出异常，不捕获
                                            ↓
                                 流式工具层统一捕获所有异常
                                            ↓
                                      记录日志（统一一次）
                                            ↓
                              返回StreamError（通过流式通道）
```

**重要区别**：
- **非流式响应**：由全局异常处理器处理，返回标准 JSONResponse
- **流式响应**：由 `create_json_stream` 捕获所有异常，返回 StreamError

**为什么流式响应不使用全局异常处理器**：
1. 流式响应已经开始发送数据，不能中断流返回标准错误
2. 必须通过流式通道发送错误信息（StreamError）
3. 客户端需要统一处理流式错误和完成信号

## 优势

1. **统一性**: 非流式响应使用相同的响应格式，流式响应使用统一的错误通道
2. **类型安全**: 使用自定义异常类，代码更清晰
3. **日志完整**: 所有异常都会被记录，便于排查问题
4. **易于扩展**: 新增异常类型只需添加新的异常类
5. **开发友好**: 开发环境返回详细错误，生产环境返回简化错误
6. **分层清晰**: 
   - 非流式响应：每层只处理自己的职责，异常统一在全局处理器处理
   - 流式响应：异常在流式工具层统一处理，保证响应的完整性
7. **流式响应健壮性**: 流式异常不会中断连接，客户端能正确处理错误

## 异常处理最佳实践

### 1. 非流式响应：只在最外层（路由层）不捕获，全局处理器处理

**推荐做法**：
```python
@router.post("/upload")
async def upload_file(file: UploadFile):
    # 不捕获异常，让全局异常处理器处理
    result = await save_uploaded_file(file.filename, contents)
    return DataResponse[FileUploadData](data=result, message="上传成功")
```

**避免的做法**：
```python
@router.post("/upload")
async def upload_file(file: UploadFile):
    try:  # ❌ 不要在路由层捕获异常
        result = await save_uploaded_file(file.filename, contents)
        return DataResponse[FileUploadData](data=result)
    except Exception as e:
        return ErrorResponse(message=str(e))  # ❌ 让全局处理器处理
```

### 2. 流式响应：只在工具层（stream_utils）捕获，内层不捕获

**推荐做法**：

ai_engine/core.py (最底层):
```python
async def stream_generate(self, messages):
    # 不捕获异常，直接抛出
    async for chunk in stream.astream(input=messages):
        if chunk:
            yield chunk
```

ai_service.py (服务层):
```python
async def optimize_markdown_layout_stream(self, filename):
    # 不捕获异常，直接透传
    file_info = read_file(filename)  # 可能抛出 NotFoundException
    async for chunk in self.markdown_optimizer.optimize_layout_stream(content):
        yield chunk
```

stream_utils.py (工具层，唯一捕获异常的地方):
```python
async def generate():
    try:
        async for chunk in stream_generator(*args, **kwargs):
            yield StreamChunk(content=chunk).model_dump_json() + "\n"
    except Exception as e:
        # 统一记录日志
        logger.error(f"流式处理异常: {str(e)}", exc_info=True)
        # 转换为 StreamError
        yield StreamError(message=str(e)).model_dump_json() + "\n"
```

**避免的做法**：

ai_service.py:
```python
async def optimize_markdown_layout_stream(self, filename):
    try:  # ❌ 不要在服务层捕获
        async for chunk in self.markdown_optimizer.optimize_layout_stream(content):
            yield chunk
    except Exception as e:
        logger.error(f"异常: {e}")  # ❌ 导致重复记录日志
        raise  # ❌ 不必要的异常重新抛出
```

### 3. 为什么这样设计？

**避免重复日志记录**：
```
❌ 旧设计（每层都捕获）：
ai_engine层: 记录日志
    ↓
ai_service层: 记录日志（重复！）
    ↓
stream_utils层: 记录日志（重复！）

✅ 新设计（只在外层捕获）：
ai_engine层: 直接抛出
    ↓
ai_service层: 直接透传
    ↓
stream_utils层: 统一捕获和记录（只记录一次）
```

**保持原始堆栈信息**：
```
❌ 旧设计：多次异常转换，堆栈信息可能丢失
ExternalServiceException → [自定义异常] → StreamError

✅ 新设计：保留原始异常类型和堆栈
原始异常类型直接透传，在工具层统一记录完整堆栈
```

**简化代码逻辑**：
```
❌ 旧设计：每层都有 try-except，代码重复
✅ 新设计：只有最外层有异常处理，代码简洁
```

### 4. 什么时候应该捕获异常？

**应该捕获异常的情况**：
- ✅ 工具层（非流式）：不捕获，让全局处理器处理
- ✅ 工具层（流式）：在 `create_json_stream` 中统一捕获
- ✅ 业务逻辑转换：需要将底层异常转换为业务异常时
- ✅ 特定错误处理：需要针对特定异常做特殊处理时

**不应该捕获异常的情况**：
- ❌ 路由层（非流式）：让全局异常处理器处理
- ❌ 服务层：直接透传，让工具层处理
- ❌ 只是记录日志然后重新抛出：这会导致重复记录

## 异常类型透传机制

### 流式响应中的异常类型

流式响应中，异常从底层透传到最外层，不会进行类型转换：

```
ai_engine/core.py
    ↓ 抛出原始异常 (ConnectionError, TimeoutError, ValueError, etc.)
ai_service.py
    ↓ 直接透传原始异常
stream_utils.py
    ↓ 捕获所有异常，转换为 StreamError，但保留原始错误消息
```

**为什么不在底层捕获并转换为自定义异常？**

1. **保留原始异常信息**：原始异常类型包含更详细的错误信息
2. **简化代码**：避免不必要的异常转换和包装
3. **统一处理**：最外层的 `stream_utils.py` 会统一处理所有异常
4. **灵活性**：可以根据原始异常类型在工具层做不同的处理

**示例**：

ai_engine 可能抛出的异常：
```python
# 网络错误
ConnectionError("Failed to connect to API server")

# 超时错误  
TimeoutError("Request timeout after 30s")

# API 错误
RuntimeError("API quota exceeded: 401")

# 参数错误
ValueError("Invalid message format")
```

stream_utils 会统一处理：
```python
except Exception as e:
    # 根据 error_type 判断是业务异常还是系统异常
    if error_type in ('NotFoundException', 'ValidationException'):
        logger.warning(...)  # 业务异常
    else:
        logger.error(...)    # 系统异常（包括 ConnectionError, TimeoutError 等）
    
    # 转换为 StreamError 发送给客户端
    yield StreamError(message=str(e))
```

## 注意事项

1. **流式响应异常**: 流式响应的**所有异常**都在 `stream_utils.py` 的 `create_json_stream` 中捕获，转换为 `StreamError` 并通过流式通道发送。不使用全局异常处理器。
2. **非流式响应**: 路由层不要捕获异常，让全局异常处理器处理
3. **使用正确的异常类型**: 根据业务场景选择合适的异常类型
4. **提供清晰的错误消息**: 错误消息应该简洁明了，方便用户理解
5. **日志级别**:
   - WARNING: 业务异常（如参数错误、资源不存在）
   - ERROR: 系统异常（如服务故障、外部调用失败）

## 流式响应 vs 非流式响应异常处理对比

| 特性 | 非流式响应 | 流式响应 |
|------|-----------|---------|
| 异常处理器 | 全局异常处理器 | `create_json_stream` |
| 响应类型 | `ErrorResponse` | `StreamError` |
| 返回方式 | `JSONResponse` | 通过流式通道yield |
| HTTP状态码 | 根据异常类型（404, 400, 500等） | 始终200（错误在流内） |
| 客户端处理 | 检查 `success: false` | 接收到 `type: "error"` |
| 是否中断 | 立即返回错误 | 继续发送错误后结束 |

## 配置

在 `main.py` 中注册全局异常处理器：

```python
from .core import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

## 测试

### 测试非流式响应

```python
# 测试业务异常
response = client.get("/file/notfound.md")
assert response.status_code == 404
assert response.json()["success"] == False
assert response.json()["error_code"] == "NOT_FOUND"

# 测试验证异常
response = client.post("/upload", json={})
assert response.status_code == 422
assert "验证错误" in response.json()["message"]
```

### 测试流式响应

```python
# 测试流式响应错误
response = client.post("/optimize", json={"filename": "notfound.md"})
assert response.status_code == 200  # 流式响应始终返回200

chunks = []
for line in response.iter_lines():
    chunks.append(json.loads(line))

# 检查最后一个chunk是否是错误
assert chunks[-1]["type"] == "error"
assert "文件不存在" in chunks[-1]["message"]
```

## 完整的异常处理示例

### 非流式响应示例

```python
@router.get("/file/{filename}")
async def get_file(filename: str):
    # 1. 验证参数（可能抛出 ValidationException）
    if not filename.endswith('.md'):
        raise ValidationException("只支持.md文件")

    # 2. 调用工具层（可能抛出 NotFoundException）
    content = read_file(filename)

    # 3. 返回成功响应
    return DataResponse[str](data=content, message="读取成功")

# 客户端收到的错误响应（404）
{
  "success": false,
  "message": "文件不存在: test.md",
  "error_code": "NOT_FOUND",
  "timestamp": "2026-02-07T12:00:00"
}
```

### 流式响应示例

```python
@router.post("/optimize")
async def optimize_layout(request: OptimizeRequest):
    # 1. 调用工具层包装服务层
    generate = create_json_stream(
        ai_service.optimize_markdown_layout_stream,
        request.filename
    )

    # 2. 返回流式响应
    return StreamingResponse(generate(), media_type="text/plain")

# 客户端收到的流式数据（包含错误）
{"type":"chunk","content":"# 标题"}
{"type":"chunk","content":"\n内容"}
{"type":"error","message":"AI服务不可用"}
```
