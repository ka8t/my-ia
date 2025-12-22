import uuid
from typing import Optional
from datetime import datetime
from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Field

class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str
    full_name: Optional[str] = None
    role_id: int

    class Config:
        from_attributes = True

class UserCreate(schemas.BaseUserCreate):
    username: str = Field(..., min_length=3, max_length=30)
    full_name: Optional[str] = None

class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    full_name: Optional[str] = None

# --- Schemas pour Tables de Référence ---

class RoleRead(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None

class ConversationModeRead(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationModeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None

class ConversationModeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None

class ResourceTypeRead(BaseModel):
    id: int
    name: str
    display_name: str
    created_at: datetime

    class Config:
        from_attributes = True

class ResourceTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)

class ResourceTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)

class AuditActionRead(BaseModel):
    id: int
    name: str
    display_name: str
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True

class AuditActionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    display_name: str = Field(..., min_length=2, max_length=200)
    severity: str = Field(default='info', pattern='^(info|warning|critical)$')

class AuditActionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    display_name: Optional[str] = Field(None, min_length=2, max_length=200)
    severity: Optional[str] = Field(None, pattern='^(info|warning|critical)$')

# --- Schemas pour Données Utilisateurs ---

class UserPreferenceRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    top_k: int
    show_sources: bool
    theme: str
    default_mode_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserPreferenceUpdate(BaseModel):
    top_k: Optional[int] = Field(None, ge=1, le=20)
    show_sources: Optional[bool] = None
    theme: Optional[str] = Field(None, pattern='^(light|dark)$')
    default_mode_id: Optional[int] = None

class ConversationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    mode_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: str
    content: str
    sources: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    file_hash: str
    file_size: int
    file_type: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class SessionRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    expires_at: datetime
    created_at: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True
