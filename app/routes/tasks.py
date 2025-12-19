"""
Task status and management endpoints

Provides REST API to:
- Check task status
- Cancel tasks
- List user's tasks
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from typing import Optional

from app.services.queue_service import queue_service
from app.services.task_notification_service import task_notification_service
from app.utils.rate_limit_decorator import rate_limit


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Get the status of a task

    Args:
        task_id: ARQ job ID

    Returns:
        Task status information

    Example:
        GET /tasks/abc123/status

        Response:
        {
            "task_id": "abc123",
            "status": "processing",
            "progress": 45,
            "enqueue_time": "2025-01-15T10:30:00",
            "start_time": "2025-01-15T10:30:05"
        }
    """
    # Initialize queue service if not done
    if not queue_service.initialized:
        await queue_service.initialize()

    status = await queue_service.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a pending task

    Args:
        task_id: ARQ job ID

    Returns:
        Cancellation status

    Note:
        Can only cancel tasks that are still in queue (not started yet)
    """
    if not queue_service.initialized:
        await queue_service.initialize()

    cancelled = await queue_service.cancel_task(task_id)

    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail="Task cannot be cancelled (already running or completed)"
        )

    return {"message": "Task cancelled successfully", "task_id": task_id}


@router.post("/media/process")
@rate_limit(limit=50, window=60)  # 50 media processing tasks per minute
async def enqueue_media_processing(
    request: Request,
    media_id: int,
    file_path: str,
    operations: Optional[list] = None
):
    """
    Enqueue media processing task

    Args:
        media_id: ID of the media record
        file_path: Path to the media file
        operations: List of operations ['thumbnail', 'optimize']

    Returns:
        Task ID for tracking

    Example:
        POST /tasks/media/process
        {
            "media_id": 123,
            "file_path": "/media/image.jpg",
            "operations": ["thumbnail", "optimize"]
        }

        Response:
        {
            "task_id": "abc123",
            "message": "Media processing task enqueued",
            "media_id": 123
        }
    """
    if not queue_service.initialized:
        await queue_service.initialize()

    # Subscribe to notifications for this media
    await task_notification_service.subscribe_to_media_tasks(media_id)

    task_id = await queue_service.enqueue_media_processing(
        media_id=media_id,
        file_path=file_path,
        operations=operations
    )

    return {
        "task_id": task_id,
        "message": "Media processing task enqueued",
        "media_id": media_id,
        "operations": operations or ['thumbnail', 'optimize'],
    }


@router.post("/media/thumbnail")
@rate_limit(limit=50, window=60)  # 50 thumbnail generations per minute
async def enqueue_thumbnail_generation(
    request: Request,
    media_id: int,
    file_path: str,
    thumbnail_size: tuple = (300, 300)
):
    """
    Enqueue thumbnail generation task

    Args:
        media_id: ID of the media record
        file_path: Path to the image
        thumbnail_size: Target size [width, height]

    Returns:
        Task ID
    """
    if not queue_service.initialized:
        await queue_service.initialize()

    await task_notification_service.subscribe_to_media_tasks(media_id)

    task_id = await queue_service.enqueue_thumbnail_generation(
        media_id=media_id,
        file_path=file_path,
        thumbnail_size=tuple(thumbnail_size) if isinstance(thumbnail_size, list) else thumbnail_size
    )

    return {
        "task_id": task_id,
        "message": "Thumbnail generation task enqueued",
        "media_id": media_id,
    }


@router.post("/email/send")
@rate_limit(limit=30, window=60)  # 30 emails per minute
async def enqueue_email(
    request: Request,
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    user_id: Optional[int] = None
):
    """
    Enqueue single email sending task

    Args:
        to_email: Recipient email
        subject: Email subject
        body: Plain text body
        html_body: HTML body (optional)
        user_id: User who triggered this (optional)

    Returns:
        Task ID

    Example:
        POST /tasks/email/send
        {
            "to_email": "user@example.com",
            "subject": "Welcome!",
            "body": "Thanks for signing up",
            "user_id": 1
        }
    """
    if not queue_service.initialized:
        await queue_service.initialize()

    if user_id:
        await task_notification_service.subscribe_to_user_tasks(user_id)

    task_id = await queue_service.enqueue_email(
        to_email=to_email,
        subject=subject,
        body=body,
        html_body=html_body,
        user_id=user_id
    )

    return {
        "task_id": task_id,
        "message": "Email task enqueued",
        "to_email": to_email,
    }


@router.post("/email/bulk")
@rate_limit(limit=5, window=3600)  # 5 bulk email operations per hour
async def enqueue_bulk_emails(
    request: Request,
    emails: list,
    rate_limit_emails: int = 10,
    user_id: Optional[int] = None
):
    """
    Enqueue bulk email sending task

    Args:
        emails: List of dicts with 'to_email', 'subject', 'body', 'html_body'
        rate_limit: Max emails per minute (default: 10)
        user_id: User who triggered this

    Returns:
        Task ID

    Example:
        POST /tasks/email/bulk
        {
            "emails": [
                {
                    "to_email": "user1@example.com",
                    "subject": "Newsletter",
                    "body": "Check out our latest news"
                },
                {
                    "to_email": "user2@example.com",
                    "subject": "Newsletter",
                    "body": "Check out our latest news"
                }
            ],
            "rate_limit": 10,
            "user_id": 1
        }
    """
    if not queue_service.initialized:
        await queue_service.initialize()

    if user_id:
        await task_notification_service.subscribe_to_user_tasks(user_id)

    task_id = await queue_service.enqueue_bulk_emails(
        emails=emails,
        rate_limit=rate_limit_emails,
        user_id=user_id
    )

    return {
        "task_id": task_id,
        "message": "Bulk email task enqueued",
        "total_emails": len(emails),
        "rate_limit": rate_limit_emails,
    }
