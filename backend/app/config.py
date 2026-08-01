"""
Enterprise AI Copilot — Centralized Configuration
All environment variables and derived settings for the platform.
"""
from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ─── Application ──────────────────────────────────────
    PROJECT_NAME: str = "Enterprise AI Copilot"
    VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # ─── Security ─────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ENCRYPTION_KEY: str = ""

    # ─── CORS ─────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # ─── PostgreSQL ───────────────────────────────────────
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "copilot_db"
    POSTGRES_PORT: str = "5432"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ─── Qdrant ───────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "enterprise_documents"

    # ─── Neo4j ────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ─── Redis ────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    # ─── Celery ───────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── LLM Providers ───────────────────────────────────
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ─── Connector Credentials ────────────────────────────
    GITHUB_TOKEN: str = ""
    JIRA_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    SLACK_BOT_TOKEN: str = ""
    NOTION_TOKEN: str = ""
    CONFLUENCE_URL: str = ""
    CONFLUENCE_EMAIL: str = ""
    CONFLUENCE_API_TOKEN: str = ""

    # ─── File Upload ──────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 100

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
