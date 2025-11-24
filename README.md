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

```bash
# 复制环境变量模板
cp .env.example .env
# 编辑 .env 文件，填入你的配置
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

3. **启动开发服务器**

```bash
npm run dev
```

前端运行在: `http://localhost:5173`

### 测试连通性

1. 后端测试: 访问 `http://127.0.0.1:8000/ping`
2. 前端测试: 访问 `http://localhost:5173`，点击"点击测试连接后端"按钮

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
agent/
├── backend/              # 后端 FastAPI 项目
│   ├── app/
│   │   ├── api/        # API 接口
│   │   ├── core/       # 核心配置
│   │   ├── services/   # 业务逻辑
│   │   ├── models/     # 数据模型
│   │   └── schemas/    # 数据验证
│   ├── main.py         # 入口文件
│   ├── .env            # 环境变量（本地）
│   ├── .env.example    # 环境变量模板
│   └── requirements.txt # Python 依赖
├── front/              # 前端 Vue 项目
│   ├── src/
│   │   ├── components/ # 组件
│   │   ├── utls/       # 工具函数
│   │   └── App.vue     # 主组件
│   ├── package.json    # Node 依赖
│   └── vite.config.ts  # Vite 配置
└── README.md           # 项目说明
```

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
