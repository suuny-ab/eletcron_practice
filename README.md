# AI 知识库助手

基于 Electron + React + Python FastAPI 的桌面应用，提供 AI 驱动的 Obsidian 知识库管理和编辑功能。

## 功能特性

### 知识库管理
- 📁 可视化文件树浏览（支持展开/收起）
- 📝 Markdown 文件预览和编辑
- 💾 本地文件实时保存
- 📑 多标签页支持同时打开多个文件
- 🖱️ 可拖动调整左右侧边栏宽度

### AI 智能功能
- **AI 建议**: 与 AI 对话获取知识建议，支持上下文记忆，专业友好的回复
- **AI 编辑**: 根据要求智能编辑笔记内容，支持预览后确认保存
- **一键排版**: 自动优化 Markdown 格式和结构，提升文档可读性
- 🔄 实时流式输出显示，用户体验流畅
- ⏸️ 生成过程中支持中断取消，灵活可控
- 🧠 对话历史记忆：自动保存对话上下文，支持多轮对话
- 📝 智能摘要滚动：超过 20 轮对话自动摘要，总结最早6轮对话生成summary
- ⚙️ 提示词热加载：通过配置界面实时修改 AI 提示词

## 技术栈

### 桌面应用框架
| 技术 | 版本 | 用途 |
|------|------|------|
| Electron | ^40.2.1 | 桌面应用容器 |
| electron-builder | ^25.1.8 | 应用打包 |

### 前端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| React | ^19.2.0 | UI 框架 |
| Vite | ^7.2.4 | 构建工具 |
| Ant Design | ^6.2.3 | UI 组件库 |
| Axios | ^1.13.5 | HTTP 客户端 |
| ReactMarkdown | ^10.1.0 | Markdown 渲染 |
| remark-gfm | ^4.0.1 | GitHub 风格 Markdown |
| rehype-highlight | ^7.0.2 | 代码高亮 |
| rehype-raw | ^7.0.0 | 原始 HTML 支持 |

### 后端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.128.4 | Web 框架 |
| Uvicorn | 0.40.0 | ASGI 服务器 |
| Pydantic | 2.12.5 | 数据验证 |
| LangChain | 1.2.9 | AI 框架 |
| dashscope | 1.25.11 | 通义千问 SDK |

## 项目结构

```
test/
├── backend/              # Python 后端（36 个核心文件）
│   ├── main.py          # FastAPI 应用入口，路由注册，生命周期管理
│   ├── requirements.txt # Python 依赖清单
│   ├── ai_engine/       # AI 核心引擎
│   │   ├── core.py      # AI 引擎核心（通义千问调用）
│   │   ├── base_handler.py  # AI 处理器基类
│   │   ├── config/      # 提示词配置
│   │   │   └── prompt_config.py       # 提示词管理（热加载支持）
│   │   ├── memory/      # 对话记忆模块
│   │   │   ├── chat_history.py      # 会话持久化存储（JSONL）
│   │   │   ├── session_resolver.py   # 会话 ID 解析
│   │   │   └── summarizer.py         # 摘要生成器
│   │   ├── history/      # 历史记录管理
│   │   │   └── manager.py            # 历史链管理
│   │   └── template/     # 提示词模板
│   │       └── builder.py            # 模板构建器
│   ├── core/            # 核心模块
│   │   ├── exceptions.py        # 自定义异常类
│   │   ├── exception_handlers.py # 全局异常处理器
│   │   ├── logger.py             # 日志系统配置
│   │   ├── error_handler.py      # 异常日志工具
│   │   ├── config_context.py    # 配置上下文与监听器
│   │   └── README.md             # 核心模块文档
│   ├── routes/          # API 路由（9 个端点）
│   │   ├── ai_routes.py      # AI 相关路由（3 个流式端点）
│   │   ├── config_routes.py   # 配置管理路由（3 个端点）
│   │   └── knowledge_routes.py # 知识库路由（3 个端点）
│   ├── schemas/         # 数据模型
│   │   ├── requests.py      # 请求模型（5 个）
│   │   ├── responses.py     # 响应模型（7 个）
│   │   └── stream_models.py # 流式响应模型
│   ├── services/        # 业务逻辑层
│   │   ├── ai_service.py   # AI 服务层（业务逻辑编排）
│   │   ├── cleanup_service.py  # 会话清理服务（单例模式）
│   │   └── dependencies.py  # FastAPI 依赖注入
│   ├── utils/           # 工具函数
│   │   ├── config_manager.py   # 配置文件读写管理
│   │   ├── knowledge_utils.py  # 知识库文件操作（186 行）
│   │   └── stream_utils.py     # 流式响应工具
│   ├── data/            # 数据目录
│   │   └── ai_sessions/         # AI 会话历史存储
│   └── logs/            # 日志文件目录
├── frontend/             # React 前端
│   ├── package.json     # 前端依赖配置
│   ├── vite.config.js   # Vite 配置
│   ├── index.html       # HTML 入口
│   ├── README.md        # 前端模板说明
│   ├── src/
│   │   ├── main.jsx      # React 入口
│   │   ├── App.jsx       # 根组件（布局 123 行）
│   │   ├── api/          # API 调用（3 个文件）
│   │   │   ├── ai.js     # AI 相关 API（流式读取）
│   │   │   ├── config.js # 配置 API
│   │   │   └── knowledge.js # 知识库 API
│   │   └── pages/        # 页面组件（2 个）
│   │       ├── Knowledge.jsx  # 知识库主页面（1153 行）
│   │       └── Config.jsx    # 配置页面（402 行）
│   └── public/          # 静态资源
├── main.js              # Electron 主进程入口（209 行）
├── package.json         # 项目根配置（Electron + 构建脚本）
├── start-dev.bat        # 开发环境一键启动（Windows）
├── build-dist.bat      # 一键打包脚本（智能处理 gitignore）
├── setup-python.bat    # Python 运行时配置助手
└── README.md          # 项目主文档（本文件）
```

## 安装与使用

### 从源码运行（开发者）

**环境要求：**
- Node.js >= 18
- Python >= 3.10

**方式 1：一键启动（推荐）**

```bash
# 克隆项目
git clone https://github.com/suuny-ab/eletcron_practice.git
cd eletcron_practice

# 一键启动开发环境
.\start-dev.bat
```

**`start-dev.bat` 会自动完成：**
- ✅ 检查 Python 和 Node.js 环境
- ✅ 安装 Python 依赖到 `backend/.pydeps`
- ✅ 安装根目录 Node.js 依赖
- ✅ 安装前端依赖
- ✅ 启动后端服务（http://127.0.0.1:8000，热重载）
- ✅ 启动前端开发服务器（http://localhost:5173）
- ✅ 启动 Electron 桌面应用

**方式 2：手动启动**

```bash
# 安装依赖
npm install
cd frontend && npm install && cd ..

# 终端 1：后端
cd backend
python -m uvicorn main:app --reload

# 终端 2：前端
cd frontend
npm run dev

# 终端 3：Electron
npm start
```

### 使用预编译安装包

1. 从 [GitHub Releases](https://github.com/suuny-ab/eletcron_practice/releases) 下载最新安装包
2. 运行 `AI 知识库助手 Setup 1.0.0.exe`
3. 首次启动后配置：
   - **Obsidian Vault 路径**: 你的知识库文件夹
   - **API Key**: 通义千问 API Key（从阿里云获取）
   - **模型名称**: 默认 `qwen3-max`，可改为 `qwen3-turbo` 等
4. 在配置页面的"提示词配置"标签页自定义 AI 提示词

### 打包发布

**一键打包：**
```bash
.\build-dist.bat
```

**打包流程：**
1. 检查 Python 嵌入运行时是否存在
2. 临时修改 `.gitignore`（移除 `python/`）
3. 安装 Python 依赖到 `backend/.pydeps`
4. 构建前端到 `frontend/dist`
5. 打包 Electron 应用到 `dist/`
6. 恢复 `.gitignore` 为原始状态

**生成的文件：**
- `AI 知识库助手 Setup 1.0.0.exe` - 安装程序
- `AI 知识库助手-win32-x64/` - 便携版

## 软件使用文档

### 界面布局

应用主界面分为以下几个区域：

| 区域 | 位置 | 功能 |
|------|------|------|
| **左侧文件树** | 左侧边栏 | 显示知识库文件夹结构，支持展开/收起 |
| **主编辑区** | 中间 | 显示当前文件的 Markdown 内容，支持预览和编辑 |
| **右侧 AI 面板** | 右侧边栏 | AI 对话、编辑、排版等 AI 功能 |
| **顶部标签栏** | 主编辑区上方 | 显示已打开的文件，支持切换 |

### 知识库管理

#### 浏览文件
1. 在左侧文件树中浏览文件夹结构
2. 点击文件夹前的 `▶`/`▼` 展开或收起
3. 点击 Markdown 文件查看内容

#### 编辑文件
1. 选择要编辑的文件
2. 点击工具栏的"编辑"按钮进入编辑模式
3. 使用标准 Markdown 语法编写内容
4. 编辑完成后点击"保存"按钮
5. 或点击"取消"放弃修改

#### 多标签页
- 点击文件将在新标签页中打开
- 点击标签页可切换查看不同文件
- 点击标签页上的 `×` 关闭文件
- 支持同时打开多个文件

#### 调整布局
- 拖动左侧边栏右边缘调整文件树宽度
- 拖动右侧 AI 面板左边缘调整 AI 区域宽度

### AI 功能使用

#### AI 模式选择
在右侧 AI 面板顶部，选择要使用的 AI 模式：

| 模式 | 用途 | 特点 |
|------|------|------|
| **AI 建议** | 与 AI 对话，获取知识建议 | 对话记忆、多轮交互、友好回复 |
| **AI 编辑** | 根据要求智能编辑笔记 | 预览确认、保留原文、可控编辑 |
| **一键排版** | 自动优化 Markdown 格式 | 快速整理、提升可读性 |

#### AI 建议（对话模式）

**使用场景：**
- 咨询知识、获取建议
- 学习笔记内容、理解概念
- 生成创意想法、拓展思路

**操作步骤：**
1. 选择 AI 模式为"AI 建议"
2. 在输入框中输入问题（如："解释这个概念"、"帮我总结要点"、"给出建议"等）
3. 点击"发送"按钮或按 `Enter` 键
4. AI 会实时流式输出回复
5. 可以继续提问，AI 会记住上下文进行多轮对话
6. 对话历史会自动保存，下次打开同一文件时继续

**特性：**
- ✅ 对话记忆：记住之前的对话内容
- ✅ 多轮交互：支持连续提问
- ✅ 智能摘要：超过 20 轮对话自动摘要并保留最近 14 轮
- ✅ 实时流式：逐字显示输出，体验流畅
- ✅ 可中断：随时点击"取消生成"停止

#### AI 编辑

**使用场景：**
- 优化文档结构和逻辑
- 补充缺失的内容
- 总结要点或添加标题
- 改进语言表达

**操作步骤：**
1. 选择 AI 模式为"AI 编辑"
2. 在输入框中输入编辑要求，例如：
   - "优化结构，使逻辑更清晰"
   - "补充缺失的技术细节"
   - "总结核心要点"
   - "添加适当的标题和小标题"
   - "改进语言表达，使其更专业"
3. 点击"发送"按钮
4. AI 会生成编辑后的内容预览
5. 查看预览内容后：
   - 点击"确认保存"将编辑结果保存到当前文件
   - 点击"取消"放弃编辑

**特性：**
- ✅ 预览确认：编辑前可预览结果
- ✅ 保留原文：不满意可随时取消
- ✅ 智能理解：准确理解编辑意图
- ✅ 上下文感知：基于当前文件内容编辑

#### 一键排版

**使用场景：**
- 整理格式混乱的笔记
- 统一文档结构
- 提升文档可读性

**操作步骤：**
1. 确保已打开要排版的文件
2. 选择 AI 模式为"一键排版"
3. 点击"一键排版"按钮
4. AI 会自动优化 Markdown 格式，包括：
   - 调整标题层级（#、##、###）
   - 优化列表格式
   - 规范代码块标记
   - 改善段落分隔
   - 统一标点符号
5. 查看预览内容后：
   - 点击"确认保存"应用排版结果
   - 点击"取消生成"放弃排版

**特性：**
- ✅ 快速高效：一键完成格式优化
- ✅ 智能识别：自动识别文档结构
- ✅ 预览确认：排版前可查看效果
- ✅ 保留原文：不满意可取消

#### 取消生成
在 AI 生成过程中，随时点击"取消生成"按钮可中断请求，不再消耗 API 调用。

### 配置管理

#### 基础配置
1. 点击顶部菜单的"配置"按钮打开配置页面
2. 填写必要的配置项：
   - **Obsidian Vault 路径**：选择你的知识库文件夹（如 `C:\Users\XXX\Documents\Obsidian Vault`）
   - **API Key**：输入通义千问 API Key（从阿里云控制台获取）
   - **模型名称**：选择使用的模型（默认 `qwen3-max`，可改为 `qwen3-turbo` 等更快的模型）
3. 点击"保存配置"按钮
4. 配置会保存到 `C:\Users\<用户名>\.myapp\config.json`

#### 提示词配置
1. 在配置页面点击"提示词配置"标签页
2. 选择要编辑的提示词类型：
   - 文档排版优化
   - 文档建议
   - 文档编辑
   - 对话摘要
3. 在编辑框中修改 System 和 Human 提示词内容
4. 点击"保存提示词"按钮使更改生效
5. 或点击"重置为默认"恢复初始提示词

**提示词编辑说明：**
- **System 提示词**：定义 AI 的角色和行为准则
- **Human 提示词**：定义用户输入的格式和上下文
- 修改后立即生效，无需重启应用
- 支持自定义个性化的 AI 行为

### 使用技巧

#### 高效使用 AI 编辑
- **明确目标**：清楚表达你想达到的效果（如"使逻辑更清晰"比"优化一下"更有效）
- **分步操作**：复杂编辑可以分多次完成，每次专注于一个方面
- **参考示例**：如果 AI 结果不理想，可以给出示例说明你想要的格式

#### 对话历史管理
- **定期清理**：删除不需要的对话历史文件（位于 `backend/data/ai_sessions/`）
- **利用摘要**：AI 会自动摘要旧对话，查看摘要可快速了解之前的内容
- **新建会话**：切换到不同文件会自动开始新的对话会话

#### 提示词优化建议
- **System 提示词**：明确 AI 的角色（如"你是一个专业的知识整理助手"）
- **添加约束**：指定输出格式、字数限制、风格要求等
- **测试调整**：根据实际效果反复调整提示词内容

#### 文件管理技巧
- **善用标签页**：同时打开相关文件，方便对比和参考
- **调整布局**：根据屏幕大小和工作习惯调整边栏宽度
- **定期备份**：重要笔记建议定期备份知识库文件夹

### 常见场景示例

#### 场景 1：整理混乱的会议记录
1. 打开会议记录文件
2. 使用"一键排版"优化格式
3. 使用"AI 编辑"，输入"添加参会人员和时间信息作为标题"
4. 使用"AI 建议"，输入"总结会议的核心决议"

#### 场景 2：学习笔记整理
1. 打开学习笔记
2. 使用"AI 编辑"，输入"补充相关概念的定义和说明"
3. 使用"AI 编辑"，输入"添加实践案例和应用场景"
4. 使用"AI 建议"，输入"生成知识复习问题和答案"

#### 场景 3：技术文档优化
1. 打开技术文档
2. 使用"一键排版"统一格式
3. 使用"AI 编辑"，输入"改进技术描述的准确性和专业性"
4. 使用"AI 建议"，输入"检查内容是否完整，提出补充建议"

## API 路由

### 配置管理路由
| 方法 | 路径 | 说明 | 响应模型 |
|------|------|------|----------|
| GET | `/config` | 获取配置 | `DataResponse[ConfigData]` |
| PUT | `/config` | 更新配置 | `DataResponse[ConfigData]` |
| DELETE | `/config` | 删除配置 | `BaseResponse` |

### 知识库路由
| 方法 | 路径 | 说明 | 响应模型 |
|------|------|------|----------|
| GET | `/knowledge/tree` | 获取文件树 | `DataResponse[FileTreeData]` |
| GET | `/knowledge/file/{relative_path}` | 读取文件内容 | `DataResponse[FileReadResult]` |
| PUT | `/knowledge/file/{relative_path}` | 更新文件内容 | `DataResponse[FileWriteResult]` |

### AI 路由（流式响应）
| 方法 | 路径 | 说明 | 请求模型 |
|------|------|------|----------|
| POST | `/ai/optimize` | 一键排版优化 | `OptimizeRequest` |
| POST | `/ai/advise` | AI 建议对话 | `ChatRequest` |
| POST | `/ai/edit` | AI 文档编辑 | `EditRequest` |

## 核心设计

### 架构优化

#### 三层架构
- **Routes（路由层）**: HTTP 请求响应处理，参数验证
- **Services（服务层）**: 业务逻辑编排，调用 AI 引擎
- **Utils（工具层）**: 可复用的通用函数，文件操作、流式处理

#### 服务单例模式
- **AIEngine**: 全局单例，避免每次请求创建新实例
- **AIService**: 依赖注入，通过 `app.state.ai_service` 访问
- **SessionCleanupService**: 单例模式，管理孤儿会话清理
- **ConfigContext**: 全局配置上下文，管理监听器

#### 配置热加载
- **ConfigContext**: 配置上下文管理器，支持监听器注册
- 配置更新时自动触发监听器，无需重启服务
- 自动重新初始化 AI 服务、更新提示词配置、更新清理服务路径

### 异常处理系统
- 统一的异常处理机制，区分流式和非流式响应
- 自定义异常类：
  - `NotFoundException` - 资源未找到（404）
  - `ValidationException` - 参数验证失败（400）
  - `ExternalServiceException` - 外部服务异常（通义千问）
  - `ConfigError` - 配置错误（500）
- 全局异常处理器自动记录日志并返回标准错误响应
- 区分业务异常（日志级别 WARNING）和系统异常（日志级别 ERROR）

### 日志系统
- 按日期滚动存储日志文件
- 分级别存储：
  - `all_YYYY-MM-DD.log` - 所有日志
  - `error_YYYY-MM-DD.log` - 仅错误日志
- 同时输出到控制台和文件
- 自动删除 30 天前的日志

### 流式响应机制
1. **服务层** (`ai_service.py`) - 返回纯文本流
2. **工具层** (`stream_utils.py`) - 包装为 JSON 格式，统一异常处理
3. **路由层** (`ai_routes.py`) - 返回 `StreamingResponse`
4. **前端** (`ai.js`) - 使用 Fetch API + `ReadableStream` 读取

**流式数据格式：**
```json
{"content": "片段内容", "done": false}
{"content": "片段内容", "done": false}
...
{"content": "", "done": true}  // 结束标记
```

### 对话历史记忆
- 基于 LangChain 的 `BaseChatMessageHistory` 接口
- **JSONL 格式持久化存储**：每行一个 JSON 对象，便于追加和读取
- **会话 ID 自动解析**：基于文件名自动识别会话，对业务层透明
- **启动时自动清理**：清理孤儿会话（已删除笔记的历史记录）
- **摘要滚动策略**：超过 20 轮对话时自动摘要并保留最近 14 轮

**会话历史存储位置：** `backend/data/ai_sessions/`

### AI 提示词配置
- **提示词模板化**：易于维护和扩展
- 支持多种场景：排版优化、AI 建议、文档编辑、对话摘要
- **热加载支持**：通过配置界面实时修改，无需修改代码
- **默认提示词内置**：可重置为默认值
- **ConfigModel 包含 prompts 字段**：存储到配置文件

## 问题排查

### 开发环境问题

**Q: 运行 `start-dev.bat` 时提示找不到 Python 或 Node.js？**
A: 确保已安装 Node.js >= 18 和 Python >= 3.10，并将其添加到系统环境变量 PATH 中。

**Q: 后端启动失败，提示依赖包缺失？**
A: 脚本会自动安装 Python 依赖到 `backend/.pydeps`，如果失败请手动执行：
   ```bash
   cd backend
   python -m pip install -r requirements.txt --target .pydeps
   ```

**Q: 前端开发服务器启动失败？**
A: 脚本会自动安装前端依赖，如果失败请手动执行：
   ```bash
   cd frontend
   npm install
   ```

### 应用运行问题

**Q: 应用启动后窗口空白？**
A: 可能是后端服务未正常启动，检查：
   1. 嵌入式 Python 运行时是否存在（`python/` 目录）
   2. 后端进程是否正常运行
   3. 浏览器控制台是否有错误信息（按 `Ctrl+Shift+I` 打开 DevTools）

**Q: AI 功能无法使用，显示请求失败？**
A: 检查配置是否正确：
   1. API Key 是否已配置且有效
   2. 网络连接是否正常
   3. 模型名称是否正确（如 `qwen3-max`）

**Q: 提示"后端启动失败"？**
A: 嵌入式 Python 运行时未找到，请：
   1. 重新下载完整安装包
   2. 或从源码运行开发环境

## 项目统计

### 代码规模

| 类别 | 数量 |
|--------|------|
| Python 核心文件 | 36 个 |
| React 组件文件 | 4 个 |
| API 端点 | 9 个 |
| 路由文件 | 3 个 |
| 服务类 | 3 个 |
| 配置模型 | 12 个 |

### 依赖包

**Python 核心依赖：**
- fastapi, uvicorn, pydantic（Web 框架）
- langchain, dashscope（AI 框架）
- python-multipart, python-dotenv（工具库）

**Node.js 依赖：**
- React 19.2.0（UI 框架）
- Ant Design 6.2.3（组件库）
- Vite 7.2.4（构建工具）
- Axios, ReactMarkdown 等（工具库）

## 开发者指南

### 运行开发环境

```bash
# 方式 1：一键启动（推荐）
.\start-dev.bat

# 方式 2：手动启动
# 终端 1：后端
cd backend
python -m uvicorn main:app --reload

# 终端 2：前端
cd frontend
npm run dev

# 终端 3：Electron
npm start
```

### 调试技巧

**后端调试：**
- API 文档：http://127.0.0.1:8000/docs
- 日志文件：`backend/logs/`
- 热重载：修改代码自动重启

**前端调试：**
- React DevTools：浏览器扩展
- Electron DevTools：按 `Ctrl+Shift+I`
- Vite HMR：自动热更新

### 提交规范

```bash
# 功能开发
feat: 添加新功能

# 问题修复
fix: 修复问题

# 重构
refactor: 代码重构

# 文档
docs: 更新文档
```

## 许可证

ISC

---

**项目地址**: https://github.com/suuny-ab/eletcron_practice  
**Issues**: https://github.com/suuny-ab/eletcron_practice/issues
