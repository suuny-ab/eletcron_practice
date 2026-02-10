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
- **AI 建议**: 与 AI 对话获取知识建议，专业友好的回复
- **AI 编辑**: 根据要求智能编辑笔记内容，支持预览后确认保存
- **一键排版**: 自动优化 Markdown 格式和结构，提升文档可读性
- 🔄 实时流式输出显示，用户体验流畅
- ⏸️ 生成过程中支持中断取消，灵活可控

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
| ReactMarkdown | ^10.1.0 | Markdown 渲染 |
| remark-gfm | ^4.0.1 | GitHub 风格 Markdown |
| rehype-highlight | ^7.0.2 | 代码高亮 |

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
├── backend/              # Python 后端
│   ├── main.py          # FastAPI 应用入口
│   ├── requirements.txt # Python 依赖
│   ├── ai_engine/       # AI 核心引擎
│   │   ├── core.py      # AI 引擎核心（通义千问调用）
│   │   ├── base_handler.py  # AI 处理器基类
│   │   └── config/      # 提示词配置
│   │       └── prompt_config.py
│   ├── core/            # 核心模块
│   │   ├── exceptions.py        # 自定义异常类
│   │   ├── exception_handlers.py # 全局异常处理器
│   │   ├── logger.py             # 日志系统配置
│   │   └── README.md             # 异常处理文档
│   ├── routes/          # API 路由
│   │   ├── ai_routes.py      # AI 相关路由
│   │   ├── config_routes.py   # 配置管理路由
│   │   └── knowledge_routes.py # 知识库路由
│   ├── schemas/         # 数据模型
│   │   ├── requests.py      # 请求模型
│   │   ├── responses.py     # 响应模型
│   │   └── stream_models.py # 流式响应模型
│   ├── services/        # 业务逻辑层
│   │   └── ai_service.py   # AI 服务层
│   ├── utils/           # 工具函数
│   │   ├── config_manager.py   # 配置管理器
│   │   ├── knowledge_utils.py  # 知识库文件操作
│   │   └── stream_utils.py     # 流式响应工具
│   └── logs/            # 日志文件目录
├── frontend/             # React 前端
│   ├── package.json     # 前端依赖配置
│   ├── vite.config.js   # Vite 配置
│   └── src/
│       ├── main.jsx      # React 入口
│       ├── App.jsx       # 根组件
│       ├── api/          # API 调用
│       │   ├── ai.js     # AI 相关 API
│       │   ├── config.js # 配置 API
│       │   └── knowledge.js # 知识库 API
│       └── pages/        # 页面组件
│           ├── Knowledge.jsx  # 知识库主页面
│           └── Config.jsx    # 配置页面
├── main.js              # Electron 主进程入口
├── package.json         # 项目根配置
└── python/              # 内嵌 Python 运行时
```

## 快速开始

### 环境要求
- Node.js >= 16
- Python >= 3.10

### 安装依赖

```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install

# 安装根目录依赖
cd ..
npm install
```

### 启动应用

```bash
# 启动后端服务
cd backend
python -m uvicorn main:app --reload

# 启动前端（新终端窗口）
cd frontend
npm run dev

# 启动 Electron 应用（新终端窗口）
cd ..
npm start
```

### 打包应用

```bash
# 安装 Python 依赖到 .pydeps 目录
npm run build:pydeps

# 构建前端
npm run build:renderer

# 构建全部
npm run build:all

# 打包应用
npm run dist
```

## 配置

首次使用需要在应用的"配置"页面设置：
- **Obsidian Vault 路径**: 你的 Obsidian 知识库文件夹
- **API Key**: 通义千问 API Key（从阿里云获取）
- **模型名称**: 默认 qwen3-max，可改为 qwen3-turbo 等其他模型

配置文件位置：`~/.myapp/config.json`

## 使用说明

### 知识库浏览
1. 在左侧文件树中选择 Markdown 文件
2. 点击"编辑"按钮进入编辑模式
3. 编辑完成后点击"保存"
4. 支持同时打开多个文件，使用标签页切换

### AI 功能使用

#### AI 建议
1. 选择 AI 模式为"AI 建议"
2. 在输入框中输入问题
3. 点击"发送"获取 AI 回复

#### AI 编辑
1. 选择 AI 模式为"AI 编辑"
2. 输入编辑要求（如"优化结构"、"补充内容"、"总结要点"等）
3. 点击"发送"，AI 将生成编辑后的内容
4. 预览后点击"确认保存"或"取消"

#### 一键排版
1. 点击"一键排版"按钮
2. AI 自动优化 Markdown 格式和结构
3. 预览后点击"确认保存"或"取消生成"

### 取消生成
在 AI 生成过程中，点击"取消生成"按钮可中断请求。

## API 路由

### 配置管理路由
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/config` | 获取配置 |
| PUT | `/config` | 更新配置 |
| DELETE | `/config` | 删除配置 |

### 知识库路由
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/knowledge/tree` | 获取文件树 |
| GET | `/knowledge/file/{relative_path}` | 读取文件内容 |
| PUT | `/knowledge/file/{relative_path}` | 更新文件内容 |

### AI 路由（流式响应）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ai/optimize` | 一键排版优化 |
| POST | `/ai/advise` | AI 建议对话 |
| POST | `/ai/edit` | AI 文档编辑 |

## 核心设计

### 异常处理系统
- 统一的异常处理机制，区分流式和非流式响应
- 自定义异常类：`NotFoundException`、`ValidationException`、`ExternalServiceException`、`ConfigError`
- 全局异常处理器自动记录日志并返回标准错误响应

### 日志系统
- 按日期滚动存储日志文件
- 分级别存储：`all_YYYY-MM-DD.log`（所有日志）、`error_YYYY-MM-DD.log`（错误日志）
- 同时输出到控制台和文件

### 流式响应机制
1. 服务层返回纯文本流
2. 工具层包装为 JSON 格式，统一异常处理
3. 路由层返回 StreamingResponse
4. 前端使用 Fetch API + ReadableStream 读取

### 配置管理
- 配置文件位置：`~/.myapp/config.json`
- 使用 Pydantic 模型验证配置
- 支持热重载（更新配置后自动重新初始化 AI 服务）

### AI 提示词配置
- 提示词模板化，易于维护和扩展
- 支持排版优化、AI 建议、文档编辑等多种场景
- 可通过修改 `ai_engine/config/prompt_config.py` 自定义提示词

## 许可证

ISC
