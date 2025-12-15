"""
Media model for storing multimedia files metadata.
Actual files are stored in S3/MinIO or local filesystem.
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Text

# Conditional import for pgvector support
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None


class Media(SQLModel, table=True):
    """
    Media model for storing file metadata.
    The actual file is stored in S3/MinIO or local filesystem.
    """
    __tablename__ = "media"

    id: Optional[int] = Field(default=None, primary_key=True)

    # File information
    filename: str = Field(index=True)  # Original filename
    storage_path: str = Field(unique=True, index=True)  # Path in storage (S3 key or local path)
    file_size: int  # File size in bytes
    mime_type: Optional[str] = None  # MIME type (e.g., image/jpeg)

    # File type categorization
    file_type: str = Field(index=True)  # image, video, audio, document, other

    # Metadata
    description: Optional[str] = None
    alt_text: Optional[str] = None  # For accessibility

    # Vector embedding (optional - for semantic search, face recognition, audio similarity, etc.)
    # The developer can use this for:
    # - Text embeddings (OpenAI, Cohere, etc.)
    # - Image embeddings (CLIP, ResNet, etc.)
    # - Face embeddings (DeepFace, FaceNet, etc.)
    # - Audio embeddings (Resemblyzer, VGGish, etc.)
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(512)) if PGVECTOR_AVAILABLE else Column(Text)
    )

    # Ownership (optional - link to user)
    user_id: Optional[int] = Field(default=None, index=True)

    # Storage backend
    storage_backend: str = Field(default="local")  # 's3' or 'local'

    # URLs (generated on retrieval)
    # Note: These are not stored in DB, computed on-the-fly
    # url: str (computed)
    # download_url: str (computed)

    # Status
    is_public: bool = Field(default=False)  # Public access without authentication
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MediaCreate(SQLModel):
    """Schema for creating media (used internally by upload endpoint)"""
    filename: str
    storage_path: str
    file_size: int
    mime_type: Optional[str] = None
    file_type: str
    description: Optional[str] = None
    alt_text: Optional[str] = None
    embedding: Optional[List[float]] = None  # Optional vector embedding
    user_id: Optional[int] = None
    storage_backend: str = "local"
    is_public: bool = False


class MediaRead(SQLModel):
    """Schema for reading media (public data)"""
    id: int
    filename: str
    storage_path: str
    file_size: int
    mime_type: Optional[str]
    file_type: str
    description: Optional[str]
    alt_text: Optional[str]
    embedding: Optional[List[float]] = None  # Vector embedding (if available)
    user_id: Optional[int]
    storage_backend: str
    is_public: bool
    is_active: bool
    created_at: datetime

    # URLs (computed, not in DB)
    url: Optional[str] = None
    download_url: Optional[str] = None


class MediaUpdate(SQLModel):
    """Schema for updating media metadata"""
    filename: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    embedding: Optional[List[float]] = None  # Update vector embedding
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class MediaUploadResponse(SQLModel):
    """Response schema for file upload"""
    id: int
    filename: str
    file_size: int
    file_type: str
    url: Optional[str] = None
    download_url: str
    message: str = "File uploaded successfully"
