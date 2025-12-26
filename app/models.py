import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey, DateTime, Text, JSON, Enum as SQLEnum, UniqueConstraint
import enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


# --- Enums ---

class DocumentVisibility(str, enum.Enum):
    """Visibilite d'un document pour le RAG"""
    PUBLIC = "public"      # Accessible a tous les utilisateurs
    PRIVATE = "private"    # Accessible uniquement au proprietaire
    SHARED = "shared"      # Partage avec users specifiques (prepare pour le futur)


# --- Tables de Référence ---

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # 'user', 'contributor', 'admin'
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ConversationMode(Base):
    __tablename__ = "conversation_modes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # 'chatbot', 'assistant'
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ResourceType(Base):
    __tablename__ = "resource_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AuditAction(Base):
    __tablename__ = "audit_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default='info')  # 'info', 'warning', 'critical'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# --- Tables Principales ---

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relations
    role: Mapped["Role"] = relationship()
    preferences: Mapped["UserPreference"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[List["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    top_k: Mapped[int] = mapped_column(Integer, default=4)
    show_sources: Mapped[bool] = mapped_column(Boolean, default=True)
    theme: Mapped[str] = mapped_column(String(20), default="light")
    default_mode_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversation_modes.id"), default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    user: Mapped["User"] = relationship(back_populates="preferences")
    default_mode: Mapped["ConversationMode"] = relationship()

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    mode_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversation_modes.id"), default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Archivage

    # Relations
    user: Mapped["User"] = relationship(back_populates="conversations")
    mode: Mapped["ConversationMode"] = relationship()
    messages: Mapped[List["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False) # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[dict]] = mapped_column(JSON)
    response_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Temps de reponse en secondes
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relations
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # Chemin relatif dans le storage
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    current_version: Mapped[int] = mapped_column(Integer, default=1)  # Version courante
    visibility: Mapped[DocumentVisibility] = mapped_column(
        SQLEnum(
            DocumentVisibility,
            name="document_visibility",
            create_constraint=True,
            values_callable=lambda e: [x.value for x in e]  # Utilise 'public'/'private'/'shared'
        ),
        default=DocumentVisibility.PUBLIC,
        nullable=False
    )
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Admin peut desindexer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    user: Mapped["User"] = relationship(back_populates="documents")
    versions: Mapped[List["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_number")
    shares: Mapped[List["DocumentShare"]] = relationship(back_populates="document", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    refresh_token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))

    # Relations
    user: Mapped["User"] = relationship(back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action_id: Mapped[int] = mapped_column(ForeignKey("audit_actions.id"), nullable=False)
    resource_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("resource_types.id"))
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    user: Mapped["User"] = relationship()
    action: Mapped["AuditAction"] = relationship()
    resource_type: Mapped["ResourceType"] = relationship()


# --- Tables Versioning & Partage Documents ---

class DocumentVersion(Base):
    """Historique des versions d'un document."""
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # Chemin relatif dans le storage
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)  # Nombre de chunks de cette version
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Note optionnelle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relations
    document: Mapped["Document"] = relationship(back_populates="versions")
    creator: Mapped["User"] = relationship()


class DocumentShare(Base):
    """Partage d'un document avec un utilisateur specifique (prepare pour le futur)."""
    __tablename__ = "document_shares"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission: Mapped[str] = mapped_column(String(20), default="read")  # "read" | "write" (futur)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relations
    document: Mapped["Document"] = relationship(back_populates="shares")
    shared_with: Mapped["User"] = relationship(foreign_keys=[shared_with_user_id])
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])

    # Contrainte unique: un document ne peut etre partage qu'une fois avec le meme utilisateur
    __table_args__ = (
        UniqueConstraint('document_id', 'shared_with_user_id', name='uq_document_share_user'),
    )


class UserQuota(Base):
    """Quota de stockage personnalise par utilisateur (optionnel)."""
    __tablename__ = "user_quotas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    quota_bytes: Mapped[int] = mapped_column(Integer, nullable=False)  # Quota en bytes
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relations
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
