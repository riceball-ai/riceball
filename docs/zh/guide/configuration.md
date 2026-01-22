# 配置指南

RiceBall 使用环境变量和配置文件进行管理。

## 环境变量

RiceBall 支持通过 `.env` 文件或直接设置系统环境变量来进行配置。**系统环境变量的优先级高于 `.env` 文件**。这意味着在 Docker 容器或生产环境中，你可以直接注入环境变量来覆盖默认配置。

### 后端配置 (`backend/.env`)

复制 `backend/.env.example` 到 `backend/.env` 并修改以下值：

| 变量名 | 描述 | 默认值 / 示例 |
|--------|------|---------------|
| `ENVIRONMENT` | 运行环境 | `development` 或 `production` |
| `LOG_LEVEL` | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_NAME` | 项目名称 | `RiceBall` |
| `DATABASE_URL` | PostgreSQL 数据库连接字符串 | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | 用于加密和 JWT 的密钥 | **生产环境请务必修改！** |
| `EXTERNAL_URL` | 后端 API 的外部访问 URL | `http://localhost:8000` |
| `FRONTEND_URL` | 前端访问 URL | `http://localhost:3000` |

#### Redis 缓存设置 (新增)
用于系统配置缓存、停止信号管理等。

| 变量名 | 描述 | 默认值 / 示例 |
|--------|------|---------------|
| `CACHE_DRIVER` | 缓存驱动 | `memory` (默认) 或 `redis` |
| `REDIS_URL` | Redis 连接字符串 (仅当驱动为 redis 时生效) | `redis://localhost:6379/0` |
| `CACHE_PREFIX` | 缓存Key前缀 (用于同一Redis实例下区分多应用) | `riceball:` |

#### 邮件设置
用于发送验证邮件和通知。

| 变量名 | 描述 |
|--------|------|
| `MAIL_SERVER` | SMTP 服务器地址 (如 `smtp.gmail.com`) |
| `MAIL_PORT` | SMTP 端口 (如 `587`) |
| `MAIL_USERNAME` | SMTP 用户名 |
| `MAIL_PASSWORD` | SMTP 密码 |
| `MAIL_FROM` | 发件人邮箱地址 |
| `MAIL_STARTTLS` | 是否启用 STARTTLS (`true`/`false`) |
| `MAIL_SSL_TLS` | 是否启用 SSL/TLS (`true`/`false`) |

#### 文件存储 (S3 兼容)
RiceBall 使用 S3 兼容存储（如 MinIO 或 AWS S3）来存储文件。

| 变量名 | 描述 |
|--------|------|
| `S3_ENDPOINT_URL` | S3 API 端点 URL |
| `S3_ACCESS_KEY_ID` | Access Key |
| `S3_SECRET_ACCESS_KEY` | Secret Key |
| `S3_BUCKET_NAME` | 用于存储文件的 Bucket 名称 |
| `S3_REGION` | AWS 区域 (MinIO 可选) |

#### 代码解释器 (Sandbox)
用于配置代码执行的隔离沙箱环境。

| 变量名 | 描述 | 默认值 / 示例 |
|--------|------|---------------|
| `SANDBOX_IMAGE_NAME` | 沙箱使用的 Docker 镜像 | `ghcr.io/riceball-ai/riceball-sandbox:latest` |
| `SANDBOX_WORK_DIR` | 容器内的用来执行代码的工作目录 | `/home/sandbox` |
| `SANDBOX_MEMORY_LIMIT` | 每个容器的最大内存限制 | `512m` |
| `SANDBOX_CPU_LIMIT` | 每个容器的最大 CPU 核数 | `1.0` |
| `SANDBOX_ENABLE_NETWORK` | 是否允许沙箱连接互联网 | `false` (建议关闭以确保安全) |

#### 向量数据库 (ChromaDB)
用于 RAG 的向量数据库配置。

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `CHROMA_SERVER_HOST` | ChromaDB 服务器地址 | `chromadb` |
| `CHROMA_SERVER_PORT` | ChromaDB 服务器端口 | `8000` |

### 前端配置

前端配置主要通过构建时环境变量或 Docker 环境变量进行设置。

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `API_BASE_URL` | 后端 API 的 URL (用于代理转发) | `http://localhost:8000/api` |
| `APP_NAME` | 应用程序显示的名称 | `RiceBall` |

## 系统配置

系统级别的配置（如“允许注册”、“默认模型”等）存储在数据库中，可以通过 Web 界面中的 **管理后台 (Admin Dashboard)** 进行修改，无需重启服务。
