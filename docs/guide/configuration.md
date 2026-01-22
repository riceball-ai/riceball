# Configuration Guide

RiceBall uses environment variables and configuration files for management.

## Environment Variables

RiceBall supports configuration via `.env` files or directly setting system environment variables. **System environment variables take precedence over `.env` files**. This means you can inject environment variables directly in Docker containers or production environments to override default configurations.

### Backend Configuration (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and modify the following values:

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `ENVIRONMENT` | Runtime environment | `development` or `production` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_NAME` | Name of the project | `RiceBall` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | Secret key for encryption and JWT | **Change this in production!** |
| `EXTERNAL_URL` | Public URL of the backend API | `http://localhost:8000` |
| `FRONTEND_URL` | Public URL of the frontend | `http://localhost:3000` |

#### Redis Cache Settings (New)
Used for system configuration caching, stop signal management, etc.

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `CACHE_DRIVER` | Cache driver | `memory` (default) or `redis` |
| `REDIS_URL` | Redis connection info (if driver is redis) | `redis://localhost:6379/0` || `CACHE_PREFIX` | Cache Key Prefix (for multi-app isolation in shared Redis) | `riceball:` |
#### Email Settings
Used for sending verification emails and notifications.

| Variable | Description |
|----------|-------------|
| `MAIL_SERVER` | SMTP server hostname (e.g., `smtp.gmail.com`) |
| `MAIL_PORT` | SMTP port (e.g., `587`) |
| `MAIL_USERNAME` | SMTP username |
| `MAIL_PASSWORD` | SMTP password |
| `MAIL_FROM` | Sender email address |
| `MAIL_STARTTLS` | Enable STARTTLS (`true`/`false`) |
| `MAIL_SSL_TLS` | Enable SSL/TLS (`true`/`false`) |

#### File Storage (S3 Compatible)
RiceBall uses S3-compatible storage (like MinIO or AWS S3) for files.

| Variable | Description |
|----------|-------------|
| `S3_ENDPOINT_URL` | S3 API endpoint URL |
| `S3_ACCESS_KEY_ID` | Access Key |
| `S3_SECRET_ACCESS_KEY` | Secret Key |
| `S3_BUCKET_NAME` | Bucket name for file storage |
| `S3_REGION` | AWS Region (optional for MinIO) |

#### Code Interpreter (Sandbox)
Configuration for the isolated Python execution environment.

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `SANDBOX_IMAGE_NAME` | Docker image to use for sandbox | `ghcr.io/riceball-ai/riceball-sandbox:latest` |
| `SANDBOX_WORK_DIR` | Working directory inside container | `/home/sandbox` |
| `SANDBOX_MEMORY_LIMIT` | Max memory per container | `512m` |
| `SANDBOX_CPU_LIMIT` | Max CPU cores per container | `1.0` |
| `SANDBOX_ENABLE_NETWORK` | Allow internet access in sandbox | `false` (Recommended for security) |

#### Vector Store (ChromaDB)
Settings for the vector database used for RAG.

| Variable | Description | Default |
|----------|-------------|---------|
| `CHROMA_SERVER_HOST` | Hostname of ChromaDB server | `chromadb` |
| `CHROMA_SERVER_PORT` | Port of ChromaDB server | `8000` |

### Frontend Configuration

Frontend configuration is primarily handled via build-time environment variables or Docker environment variables.

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | URL of the backend API (for proxying) | `http://localhost:8000/api` |
| `APP_NAME` | Display name of the application | `RiceBall` |

## System Configuration

System-level configurations (like "Allow Registration", "Default Model") are stored in the database and can be modified via the **Admin Dashboard** in the web interface.
