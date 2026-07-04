from datetime import datetime
from typing import Optional, List
import re
from sqlmodel import Field, SQLModel, Relationship
from pydantic import field_validator
from app.models.mixins import SoftDeleteMixin


class User(SoftDeleteMixin, SQLModel, table=True):
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
    is_superadmin: bool = Field(default=False)  # Acceso global al admin panel

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
    is_verified: bool
    created_at: datetime


class UserUpdate(SQLModel):
    """Schema for updating a user"""
    name: Optional[str] = None
    picture: Optional[str] = None
    is_active: Optional[bool] = None


# Authentication Schemas

class UserRegister(SQLModel):
    """Schema for user registration (local auth). Crea user + org + membership."""
    email: str
    password: str
    name: Optional[str] = None
    organization_name: Optional[str] = None  # Si no se pasa, se genera del email

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Valida formato y bloquea dominios temporales."""
        from app.config import settings

        v = v.lower().strip()
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError("Formato de email inválido")

        # Bloquear dominios temporales (solo si enforcement está habilitado)
        if settings.ENFORCE_STRONG_PASSWORDS:
            disposable = ["tempmail.com", "throwaway.email", "guerrillamail.com", "mailinator.com"]
            domain = v.split("@")[1]
            if domain in disposable:
                raise ValueError("No se permiten emails temporales")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valida fortaleza del password (opcional via ENFORCE_STRONG_PASSWORDS)."""
        from app.config import settings

        # Skip validation si no está habilitado (útil para testing)
        if not settings.ENFORCE_STRONG_PASSWORDS:
            return v

        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not re.search(r"[a-z]", v):
            raise ValueError("La contraseña debe contener al menos una minúscula")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe contener al menos un número")

        # Passwords comunes bloqueados
        common = ["password", "12345678", "qwerty", "abc123", "password123"]
        if v.lower() in common:
            raise ValueError("Contraseña demasiado común")
        return v


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
