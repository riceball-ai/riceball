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
