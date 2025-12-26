"""
Configuration centralisée avec pydantic-settings

Ce module centralise toute la configuration de l'application,
remplaçant les variables d'environnement dispersées.
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Chemin vers le fichier .env à la racine du projet
# En local : /path/to/my-ia/.env
# En Docker : les variables sont passées via docker-compose env_file
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Configuration globale de l'application MY-IA"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str
    app_version: str
    debug: bool = False
    log_level: str
    environment: str

    # Server
    app_host: str
    app_port: int

    # Database
    database_url: str

    # Ollama
    ollama_host: str
    ollama_port: int
    llm_model: str  # Nom du modèle LLM (ex: mistral, llama3)
    embed_model: str

    # ChromaDB
    chroma_host: str
    chroma_port: int
    chroma_path: str = "/chroma/chroma"
    collection_name: str

    # RAG
    top_k: int
    chunk_size: int
    chunk_overlap: int
    chunking_strategy: str
    datasets_dir: str

    # Security
    api_key: str
    secret_key: str

    # Encryption (PII)
    # Clé de chiffrement AES-256 (64 caractères hex = 32 bytes)
    # Générer avec: openssl rand -hex 32
    encryption_key: Optional[str] = None

    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    # CORS
    cors_origins: list[str] = ["*"]

    # Rate Limiting
    rate_limit_chat: str
    rate_limit_upload: str
    rate_limit_stream: str
    rate_limit_admin: str = "30/minute"

    # Timeouts
    ollama_timeout: float
    http_timeout: float
    health_check_timeout: float

    # === Storage ===
    storage_backend: str = "local"  # "local" | "minio" | "s3"
    storage_local_path: str = "/data/uploads"

    # Quotas
    storage_default_quota_mb: int = 100  # Quota par défaut par utilisateur (MB)
    storage_max_file_size_mb: int = 50  # Taille max par fichier (MB)
    storage_allowed_mime_types: str = (
        "application/pdf,"
        "text/plain,"
        "text/csv,"
        "text/markdown,"
        "application/json,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
        "application/msword,"
        "application/vnd.ms-excel,"
        "application/vnd.ms-powerpoint"
    )
    storage_blocked_extensions: str = ".exe,.bat,.sh,.cmd,.ps1,.dll,.so,.bin"

    # MinIO (futur)
    storage_minio_endpoint: Optional[str] = None
    storage_minio_access_key: Optional[str] = None
    storage_minio_secret_key: Optional[str] = None
    storage_minio_bucket: str = "documents"
    storage_minio_secure: bool = False

    # S3 (futur)
    storage_s3_bucket: Optional[str] = None
    storage_s3_region: Optional[str] = None
    storage_s3_access_key: Optional[str] = None
    storage_s3_secret_key: Optional[str] = None

    @property
    def ollama_url(self) -> str:
        """URL complète pour Ollama (http://host:port)"""
        return f"http://{self.ollama_host}:{self.ollama_port}"

    @property
    def chroma_url(self) -> str:
        """URL complète pour ChromaDB (http://host:port)"""
        return f"http://{self.chroma_host}:{self.chroma_port}"


# Instance globale
settings = Settings()
