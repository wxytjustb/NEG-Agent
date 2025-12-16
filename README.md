# NEG-Agent

AI 对话助手，基于 LangGraph 工作流编排，集成 Laminar 可观测性追踪。

## 技术栈

### 后端
- **框架**: FastAPI
- **LLM 框架**: LangChain + LangGraph
- **LLM 提供商**: Ollama (本地) / DeepSeek (云端)
- **可观测性**: Laminar
- **缓存/会话**: Redis
- **运行环境**: Python 3.10+

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **运行环境**: Node.js 16+

---

## 快速开始

### 后端启动

1. **进入后端目录**

```bash
cd backend
```

2. **创建虚拟环境（推荐）**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

创建 `.env` 文件，配置以下关键参数：

```bash
# LLM 配置（选择一种）
LLM_PROVIDER=ollama  # 或 deepseek

# Ollama 配置（本地模型）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TEMPERATURE=0.7

# DeepSeek 配置（云端 API）
# LLM_API_KEY=your_deepseek_api_key
# LLM_API_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL=deepseek-chat

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 如果有密码

# 会话配置
SESSION_TOKEN_EXPIRE_MINUTES=30

# 认证服务器配置（Go 服务器）
GOLANG_API_BASE_URL=https://app-api.roky.work
GOLANG_VERIFY_ENDPOINT=/open-api/auth/verify-app-user

# Laminar 配置（可观测性追踪）
LAMINAR_ENABLED=true
LAMINAR_API_KEY=your_laminar_api_key  # 从 Laminar 控制台获取
LAMINAR_BASE_URL=http://localhost  # 自托管服务器地址（可选）
LAMINAR_HTTP_PORT=8080
LAMINAR_GRPC_PORT=8081
LAMINAR_ENVIRONMENT=development
```

5. **启动后端服务**

```bash
uvicorn main:app --reload --port 8000
```

后端运行在: `http://127.0.0.1:8000`

### 前端启动

1. **进入前端目录**

```bash
cd front
```

2. **安装依赖**

```bash
npm install
```

3. **配置环境变量**

创建 `.env` 文件：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

4. **启动开发服务器**

```bash
npm run dev
```

前端运行在: `http://localhost:5173`

### 测试连通性

1. 后端测试: 访问 `http://127.0.0.1:8000/ping`
2. 前端测试: 访问 `http://localhost:5173`，点击“点击测试连接后端”按钮

---

## 使用指南

### 会话初始化流程

1. **获取 access_token**
   - 从你的认证系统（Go 服务器）获取有效的 `access_token`

2. **访问前端页面**
   ```
   # 普通对话模式
   http://localhost:5173/?access_token=your_access_token
   
   # 工作流模式（LangGraph）
   http://localhost:5173/langgraph?access_token=your_access_token
   ```

3. **自动初始化会话**
   - 前端会自动调用 `/api/agent/init` 接口
   - 后端验证 `access_token` 并生成 `session_token`
   - `session_token` 保存到 `localStorage` 和 Redis

4. **后续请求**
   - 使用 `session_token` 进行对话
   - 会话默认有效期 30 分钟

### 两种对话模式

#### 1. 普通对话模式
- **路由**: `/`
- **接口**: `/api/agent/chat`
- **特点**: 直接调用 LLM，简单快速
- **适用**: 日常对话场景

#### 2. 工作流模式（LangGraph）
- **路由**: `/langgraph`
- **接口**: `/api/workflow/chat`
- **特点**: 
  - 自动分析用户意图
  - 多节点工作流编排
  - 完整的 Laminar 可观测性追踪
- **适用**: 复杂业务场景、需要监控和调试

### Laminar 可观测性

开启 Laminar 后，所有 LLM 调用和工作流执行会被自动追踪：

1. **访问 Laminar 控制台**
   - 云版: https://www.lmnr.ai
   - 自托管: `http://localhost:8080`

2. **查看追踪信息**
   - 蓝色 span: 工作流节点
   - 紫色 span: LLM 调用
   - Tags: 自定义标签用于筛选

3. **工作流追踪结构**
   ```
   workflow_stream (顶层)
   ├── analyze_intent_node (意图分析)
   │   └── intent_llm_call (LLM)
   ├── call_llm_node (LLM 生成)
   │   └── chat_llm_call (LLM)
   └── save_to_redis_node (保存历史)
   ```

### 访问地址

#### 后端服务
- **API 根地址**: http://127.0.0.1:8000
- **接口文档 (Swagger)**: http://127.0.0.1:8000/docs
- **接口文档 (ReDoc)**: http://127.0.0.1:8000/redoc
- **测试接口**: http://127.0.0.1:8000/ping

#### 前端服务
- **开发环境**: http://localhost:5173

---

## 项目结构

```
NEG-Agent/
├── backend/              # 后端 FastAPI 项目
│   ├── app/
│   │   ├── api/            # API 接口
│   │   │   ├── agent.py    # Agent 普通对话接口
│   │   │   ├── workflow.py # LangGraph 工作流接口
│   │   │   └── llm.py      # LLM 直接调用接口
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py   # 环境配置
│   │   │   ├── security.py # 认证验证
│   │   │   └── session_token.py # 会话管理
│   │   ├── services/       # 业务逻辑
│   │   │   ├── langgraph_service.py # LangGraph 工作流服务
│   │   │   ├── llm_service.py       # LLM 调用服务
│   │   │   ├── redis_service.py     # Redis 缓存服务
│   │   │   └── agent_service.py     # Agent 服务
│   │   ├── initialize/     # 初始化模块
│   │   │   ├── laminar.py  # Laminar 初始化
│   │   │   └── redis.py    # Redis 初始化
│   │   ├── prompts/        # 提示词模板
│   │   └── schemas/        # 数据验证
│   ├── main.py         # 入口文件
│   ├── .env            # 环境变量（本地）
│   └── requirements.txt # Python 依赖
├── front/              # 前端 Vue 项目
│   ├── src/
│   │   ├── components/     # 组件
│   │   │   ├── ChatPage.vue         # 普通对话页面
│   │   │   └── LangGraphChatPage.vue # 工作流对话页面
│   │   ├── api/            # API 调用
│   │   ├── utls/           # 工具函数
│   │   └── App.vue         # 主组件
│   ├── package.json    # Node 依赖
│   └── vite.config.ts  # Vite 配置
└── README.md           # 项目说明
```

---

## 常见问题

### 1. Token 认证失败

**错误**: `Token is invalid: {'isValid': False, 'msg': 'Token无效或已过期'}`

**原因**: `access_token` 已过期

**解决方案**:
1. 从认证系统（Go 服务器）重新获取有效的 `access_token`
2. 使用新 token 访问页面：`http://localhost:5173/?access_token=new_token`

### 2. 清除 localStorage 后无法使用

**现象**: 清除浏览器缓存后，页面无法初始化会话

**原因**: 清除 `localStorage` 会删除 `session_token`，需要用 `access_token` 重新初始化

**解决方案**:
- 确保 URL 中包含有效的 `access_token` 参数
- 刷新页面自动重新初始化会话

### 3. Redis 连接失败

**错误**: `Failed to connect to Redis`

**解决方案**:
1. 确保 Redis 服务已启动：`redis-server`
2. 检查 `.env` 中的 Redis 配置
3. 测试 Redis 连接：`redis-cli ping`

### 4. Ollama 模型无法调用

**错误**: `Connection refused to Ollama`

**解决方案**:
1. 启动 Ollama：`ollama serve`
2. 下载模型：`ollama pull qwen2.5:7b`
3. 检查 `.env` 中的 `OLLAMA_BASE_URL` 和 `OLLAMA_MODEL`

### 5. Laminar 看不到 LLM span

**现象**: Laminar UI 中只有蓝色节点，没有紫色 LLM span

**原因**: Ollama 不被 Laminar 自动 instrumentation 支持

**解决方案**: 已在代码中使用 `Laminar.start_as_current_span()` 手动创建 LLM span

---

## 常用命令

### 后端

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（热重载）
uvicorn main:app --reload --port 8000

# 生产环境启动
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

---
