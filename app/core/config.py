"""
Configuration centralisée avec pydantic-settings

Ce module centralise toute la configuration de l'application,
remplaçant les variables d'environnement dispersées.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration globale de l'application MY-IA"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "MY-IA API"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/myia"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    model_name: str = "mistral:7b"
    embed_model: str = "nomic-embed-text"

    # ChromaDB
    chroma_host: str = "http://localhost:8000"
    chroma_path: str = "/chroma/chroma"
    collection_name: str = "knowledge_base"

    # RAG
    top_k: int = 4

    # Security
    api_key: str = "change-me-in-production"
    secret_key: str = "change-me-in-production"

    # CORS
    cors_origins: list[str] = ["*"]

    # Rate Limiting
    rate_limit_chat: str = "30/minute"
    rate_limit_upload: str = "10/minute"
    rate_limit_stream: str = "20/minute"

    # Timeouts
    ollama_timeout: float = 600.0
    http_timeout: float = 30.0
    health_check_timeout: float = 5.0


# Instance globale
settings = Settings()
