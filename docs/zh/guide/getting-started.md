# 快速开始

## 环境要求

- Docker & Docker Compose
- Python 3.10+ (如果不使用 Docker)
- Node.js 18+ (如果不使用 Docker)

## 快速开始 (All-in-One Docker)

> **注意**: 此设置仅用于**预览和测试目的**。生产环境请谨慎使用。

使用我们的 All-in-One Docker 镜像（包含 SQLite 和本地存储）一键运行 RiceBall：

```bash
docker run -d \
  -p 8000:8000 \
  -v riceball_storage:/app/storage \
  --name riceball \
  ghcr.io/riceball-ai/riceball:all-in-one-latest
```

访问 [http://localhost:8000](http://localhost:8000) 即可开始使用 RiceBall。

默认管理员账号：
- 邮箱：`admin@admin.com`
- 密码：`admin123456`

## 生产环境部署 (源码)

对于需要 PostgreSQL 和 S3 的生产环境，你可以从源码部署：

1. **克隆仓库**:
   ```bash
   git clone https://github.com/riceball-ai/riceball.git
   cd riceball
   ```

2. **配置环境变量**:
   复制后端示例配置文件：
   ```bash
   cp backend/.env.example backend/.env
   ```
   你可以根据需要修改 `backend/.env` 文件中的配置（例如数据库密码、API 密钥等）。

3. **启动服务**:
   使用 Docker Compose 启动所有服务（后端、前端、数据库）：
   ```bash
   docker compose -f docker-compose.prod.yml up
   ```
   容器启动时会自动执行数据库迁移、初始化系统配置并创建默认超级管理员用户。

4. **访问应用**:
   打开浏览器访问 [http://localhost:3000](http://localhost:3000) 即可开始使用 RiceBall。

   默认管理员账号：
   - 邮箱：`admin@admin.com`
   - 密码：`admin123456`

## 使用 Just (可选)

如果你安装了 [Just](https://github.com/casey/just)，可以使用以下快捷命令：

- 启动开发环境: `just dev`
