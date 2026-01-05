from pathlib import Path
from enum import Enum
from typing import ClassVar

from pydantic import AnyHttpUrl, EmailStr, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATE_DIR = BASE_DIR / "templates"

class EnvironmentType(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class StorageType(Enum):
    S3 = "s3"
    LOCAL = "local"

class ChromaClientType(Enum):
    HTTP = "http"
    PERSISTENT = "persistent"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file
        env_file=".env",
        env_file_encoding='utf-8',
        env_ignore_empty=True,
        extra="ignore",
    )

    APP_NAME: str = "RiceBall"
    APP_LOGO: str | None = None
    APP_FAVICON: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    SHOW_DOCS_ENVIRONMENT: ClassVar[list[EnvironmentType]] = [EnvironmentType.DEVELOPMENT]
    
    FRONTEND_URL: AnyHttpUrl = 'http://localhost:3000'

    EXTERNAL_URL: AnyHttpUrl | None = None  # External API URL, used for OAuth callbacks etc.

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///storage/database/riceball.db"

    # Auth
    SECRET_KEY: str = "insecure-secret-key-for-dev"
    
    # Token Configuration
    ACCESS_TOKEN_LIFETIME_SECONDS: int = 60 * 30  # 30 minutes
    REFRESH_TOKEN_LIFETIME_SECONDS: int = 60 * 60 * 24 * 30  # 30 days
    REFRESH_TOKEN_ROTATION_ENABLED: bool = True  # Token rotation for better security
    REFRESH_TOKEN_MAX_PER_USER: int = 5  # Max active refresh tokens per user
    
    # Cookie Configuration (Security Enhancement)
    ACCESS_TOKEN_COOKIE_NAME: str = "access-token"
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh-token"
    REFRESH_TOKEN_COOKIE_PATH: str = "/api/v1/auth/refresh"  # Limit refresh token to refresh endpoint only
    
    # Email Server
    MAIL_SERVER: str = ""
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: SecretStr = SecretStr("")
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    MAIL_FROM: EmailStr = "noreply@example.com"

    # Storage Directory
    STORAGE_DIR: Path = BASE_DIR / "storage"

    # File Storage
    STORAGE_TYPE: StorageType = StorageType.LOCAL
    LOCAL_STORAGE_PATH: Path | None = None  # Defaults to STORAGE_DIR / "files"

    # File Storage (S3 Configuration)
    S3_ENDPOINT_URL: str = "http://minio:9000"  # Set in environment
    S3_EXTERNAL_ENDPOINT_URL: str = "" # External URL for accessing S3, if different from internal
    S3_ACCESS_KEY_ID: str = "minioadmin"  # Set in environment
    S3_SECRET_ACCESS_KEY: SecretStr = "minioadmin"  # Set in environment  
    S3_BUCKET_NAME: str = "test"  # Default bucket name
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False
    S3_ADDRESSING_STYLE: str = "path"  # Use path-style for MinIO compatibility
    S3_SIGNATURE_VERSION: str = "s3v4"  # Use signature version 4
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB default
    ALLOWED_IMAGE_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"]
    ALLOWED_DOCUMENT_EXTENSIONS: list[str] = [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"]
    
    # Vector Store
    CHROMA_CLIENT_TYPE: ChromaClientType = ChromaClientType.PERSISTENT
    CHROMA_PERSIST_DIRECTORY: Path | None = None  # Defaults to STORAGE_DIR / "chroma_db"
    CHROMA_SERVER_HOST: str = "chromadb"  # Chroma service address
    CHROMA_SERVER_PORT: int = 8000
    
    # OAuth Settings
    OAUTH_CREATE_USER_WITHOUT_EMAIL: bool = True  # Whether to create new user when email is missing
    OAUTH_REQUIRE_EMAIL_VERIFICATION: bool = False  # Whether OAuth users require email verification
    OAUTH_EMAIL_DOMAIN: str = "oauth.example.com"  # Domain used when generating virtual emails
    
    # Agent Configuration
    AGENT_MAX_ITERATIONS: int = 10  # Agent max iterations
    AGENT_TIMEOUT_SECONDS: int = 300  # Agent execution timeout (seconds)
    AGENT_ENABLE_MEMORY: bool = True  # Whether to enable Agent memory
    
    # MCP Configuration
    MCP_ENABLED: bool = True  # Whether to enable MCP features
    MCP_SERVERS_CONFIG_PATH: str = "/app/mcp_servers.json"  # MCP servers config file path

settings = Settings()
