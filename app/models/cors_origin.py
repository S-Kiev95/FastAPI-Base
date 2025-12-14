from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class CorsOrigin(SQLModel, table=True):
    """
    CORS Origin configuration stored in database.
    Allows dynamic management of allowed origins without server restart.
    """
    __tablename__ = "cors_origins"

    id: Optional[int] = Field(default=None, primary_key=True)
    origin: str = Field(
        index=True,
        unique=True,
        description="Allowed origin URL (e.g., https://myapp.com or http://localhost:3000)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description for this origin (e.g., 'Production frontend', 'Admin panel')"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this origin is currently active"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    created_by: Optional[str] = Field(
        default=None,
        description="User who created this origin"
    )


# Pydantic schemas for API
class CorsOriginCreate(SQLModel):
    """Schema for creating a new CORS origin"""
    origin: str = Field(
        min_length=1,
        max_length=500,
        description="Origin URL (must start with http:// or https://)"
    )
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)


class CorsOriginUpdate(SQLModel):
    """Schema for updating an existing CORS origin"""
    origin: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = Field(default=None)


class CorsOriginRead(SQLModel):
    """Schema for reading CORS origin data"""
    id: int
    origin: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[str]
