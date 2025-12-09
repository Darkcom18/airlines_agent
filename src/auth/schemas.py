"""
Authentication schemas.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (no password)."""
    id: UUID
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Schema for JWT token payload."""
    user_id: UUID
    email: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
