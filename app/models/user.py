from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class User(SQLModel, table=True):
    """
    User model supporting dual authentication:
    - OAuth providers (Google, GitHub, etc.)
    - Local authentication (email/password)
    """
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)

    # OAuth provider information (optional for local auth)
    provider: Optional[str] = Field(default="local", index=True)  # "local", "google", "github"
    provider_user_id: Optional[str] = Field(default=None, index=True)  # User ID from provider

    # User profile information
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None
    picture: Optional[str] = None  # Avatar URL

    # Local authentication (only for provider="local")
    hashed_password: Optional[str] = None  # Only used for local auth

    # Account status
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)  # Email verification status

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    # Relationships (commented to avoid circular imports, used in services)
    # roles: List["Role"] = Relationship(back_populates="users", link_model=UserRole)


class UserCreate(SQLModel):
    """Schema for creating a user"""
    provider: str
    provider_user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class UserRead(SQLModel):
    """Schema for reading a user (public data)"""
    id: int
    provider: str
    email: str
    name: Optional[str]
    picture: Optional[str]
    is_active: bool
    created_at: datetime


class UserUpdate(SQLModel):
    """Schema for updating a user"""
    name: Optional[str] = None
    picture: Optional[str] = None
    is_active: Optional[bool] = None


# Authentication Schemas

class UserRegister(SQLModel):
    """Schema for user registration (local auth)"""
    email: str
    password: str
    name: Optional[str] = None


class UserLogin(SQLModel):
    """Schema for user login"""
    email: str
    password: str


class Token(SQLModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Schema for token payload data"""
    email: Optional[str] = None
