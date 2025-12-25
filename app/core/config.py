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
    model_name: str
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

    # Timeouts
    ollama_timeout: float
    http_timeout: float
    health_check_timeout: float

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
