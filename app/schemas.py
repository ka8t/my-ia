import uuid
from typing import Optional
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

# Custom schemas for our specific logic
class RoleRead(BaseModel):
    id: int
    name: str
    display_name: str
    
    class Config:
        from_attributes = True
