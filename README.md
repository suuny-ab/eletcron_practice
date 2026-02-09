# AI 知识库助手

基于 Electron + React + Python FastAPI 的桌面应用，提供 AI 驱动的知识库管理和编辑功能。

## 功能特性

### 知识库管理
- 📁 可视化文件树浏览
- 🔍 Markdown 文件预览和编辑
- 💾 本地文件实时保存

### AI 智能功能
- **AI 建议**: 与 AI 对话获取知识建议
- **AI 编辑**: 根据要求智能编辑笔记内容
- **一键排版**: 自动优化 Markdown 格式和结构
- 🔄 实时流式输出显示
- ⏸️ 生成过程中支持中断取消

### 技术栈
- **前端**: Electron + React + Ant Design + ReactMarkdown
- **后端**: Python FastAPI
- **AI引擎**: LangChain
- **日志系统**: 统一日志管理，按日期滚动存储

## 项目结构

```
test/
├── backend/              # Python 后端
│   ├── ai_engine/        # AI 核心引擎
│   ├── core/             # 核心模块（日志配置等）
│   ├── routes/           # API 路由
│   ├── schemas/          # 数据模型
│   ├── services/         # 业务逻辑
│   ├── utils/            # 工具函数
│   └── logs/             # 日志文件目录
├── frontend/             # React 前端
│   └── src/
│       ├── api/          # API 调用
│       ├── pages/        # 页面组件
│       └── ...
├── main.js              # Electron 主进程
└── package.json         # 项目配置
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
```

### 启动应用

```bash
# 启动后端服务
cd backend
python main.py

# 启动前端（新终端窗口）
cd frontend
npm start

# 启动 Electron 应用
cd ..
npm start
```

## 配置

首次使用需要在应用的"配置"页面设置 Obsidian 知识库路径。

## 使用说明

### 知识库浏览
1. 在左侧文件树中选择 Markdown 文件
2. 点击"编辑"按钮进入编辑模式
3. 编辑完成后点击"保存"

### AI 功能使用

#### AI 建议
1. 选择 AI 模式为"AI 建议"
2. 在输入框中输入问题
3. 点击"发送"获取 AI 回复

#### AI 编辑
1. 选择 AI 模式为"AI 编辑"
2. 输入编辑要求（如"优化结构"、"补充内容"等）
3. 点击"发送"，AI 将生成编辑后的内容
4. 预览后点击"确认保存"或"取消"

#### 一键排版
1. 点击"一键排版"按钮
2. AI 自动优化 Markdown 格式
3. 预览后点击"确认保存"或"取消生成"

### 取消生成
在 AI 生成过程中，点击"取消生成"按钮可中断请求。

## 开发

### 后端 API
- `/api/config` - 配置管理
- `/api/file` - 文件操作
- `/ai/advise` - AI 建议
- `/ai/edit` - AI 编辑
- `/ai/optimize` - 一键排版

### 日志查看
日志文件位于 `backend/logs/` 目录：
- `all_YYYY-MM-DD.log` - 所有日志
- `error_YYYY-MM-DD.log` - 错误日志

## 许可证

ISC
