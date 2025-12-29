# Docker 部署指南

RiceBall 提供了完整的 Docker 支持，包括开发环境快速启动和生产环境构建方案。

## 1. 快速启动 (开发模式)

项目根目录自带的 `docker-compose.yml` 默认配置为开发模式 (`target: dev`)。此模式支持代码热重载，适合开发和体验。

### 启动服务

```bash
# 启动所有服务
docker compose -f docker-compose.prod.yml up

# 查看日志
docker-compose logs -f
```

### 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| **Frontend** | 3000 | Web 用户界面 |
| **Backend** | 8000 | API 服务 |
| **Postgres** | 5432 | 关系型数据库 |
| **MinIO** | 9000/9001 | 对象存储 (S3 兼容) |
| **ChromaDB** | 8088 | 向量数据库 |
| **MailHog** | 8025 | 邮件测试服务 |

## 2. 生产环境部署

RiceBall 提供了 `docker-compose.prod.yml` 文件，专为生产环境设计。它会自动构建优化后的生产镜像，并配置了自动重启策略。

### 2.1 部署步骤

1. **准备配置文件**:
   确保 `backend/.env` 文件存在并已配置好生产环境参数（如 `SECRET_KEY`）。

2. **启动服务**:
   使用以下命令启动生产环境：

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

   该命令会自动执行以下操作：
   - 构建后端生产镜像 (基于 `uv`，移除构建工具)
   - 构建前端生产镜像 (基于 Nginx 托管静态文件)
   - 启动所有依赖服务 (Postgres, MinIO, ChromaDB)

### 2.2 服务说明

生产环境配置 (`docker-compose.prod.yml`) 与开发环境的主要区别：

- **构建优化**: 使用多阶段构建，镜像体积更小。
- **前端托管**: 前端使用 Nginx 容器托管，端口映射为 `3000:80`。
- **自动重启**: 所有服务配置了 `restart: always`。
- **移除开发工具**: 移除了 MailHog (邮件测试) 和 Adminer (数据库管理) 等开发辅助工具。

### 2.3 数据持久化

在生产环境中，务必将以下目录挂载到宿主机，以防数据丢失：

- **PostgreSQL**: `/var/lib/postgresql/data`
- **MinIO**: `/data` (如果使用内置 MinIO)
- **ChromaDB**: `/data`

### 2.4 外部服务配置 (可选)

虽然 `docker-compose.prod.yml` 默认包含了 MinIO，但在生产环境中，你可能希望使用外部的云服务。

- **对象存储 (S3)**: MinIO 不是必须的。你可以使用 AWS S3、阿里云 OSS 或其他兼容 S3 的服务。只需在 `backend/.env` 中配置 `S3_ENDPOINT_URL`、`S3_ACCESS_KEY_ID` 等参数，并在 `docker-compose.prod.yml` 中移除 `minio` 和 `minio-mc` 服务即可。
- **邮件服务 (SMTP)**: 生产环境移除了 MailHog。请在 `backend/.env` 中配置真实的 SMTP 服务信息（如 `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD` 等）以启用邮件发送功能。

## 3. 环境变量配置

生产部署时，请务必修改默认的敏感配置：

1. 修改 `POSTGRES_PASSWORD` 和 `MINIO_ROOT_PASSWORD`。
2. 在 `backend/.env` 中更新 `SECRET_KEY`。
3. 将 `ENVIRONMENT` 设置为 `production`。

详细的环境变量说明请参考 [配置指南](../guide/configuration.md)。
