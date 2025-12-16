"""
Task model for tracking async job status
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class Task(SQLModel, table=True):
    """
    Tracks the status of async tasks (media processing, email sending, etc.)

    Workflow:
    1. User triggers action (upload media, send email)
    2. Backend creates Task record with status='pending'
    3. Task is enqueued to Redis (ARQ)
    4. Worker picks up task and updates status='processing'
    5. Worker completes and updates status='completed' or 'failed'
    6. Worker publishes notification via Redis Pub/Sub
    7. Backend sends WebSocket notification to user
    """
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Task identification
    task_id: str = Field(index=True, unique=True)  # ARQ job ID
    task_type: str = Field(index=True)  # 'media_processing', 'email_sending', etc.

    # Task status
    status: str = Field(default="pending", index=True)  # pending, processing, completed, failed
    progress: int = Field(default=0)  # 0-100

    # Task details
    task_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Input parameters
    result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # Output result
    error: Optional[str] = Field(default=None)  # Error message if failed

    # Ownership
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Retry management
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)


class TaskCreate(SQLModel):
    """Schema for creating a new task"""
    task_type: str
    task_data: Dict[str, Any] = {}
    user_id: Optional[int] = None
    max_retries: int = 3


class TaskRead(SQLModel):
    """Schema for reading task status"""
    id: int
    task_id: str
    task_type: str
    status: str
    progress: int
    task_data: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    user_id: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int


class TaskUpdate(SQLModel):
    """Schema for updating task status"""
    status: Optional[str] = None
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: Optional[int] = None
