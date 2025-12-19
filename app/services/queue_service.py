"""
Queue service for enqueuing async tasks using ARQ

This service provides a high-level interface to enqueue tasks
that will be processed by ARQ workers.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from arq import create_pool
from arq.connections import ArqRedis
from redis.asyncio import Redis

from app.config import settings
from app.utils.logger import get_structured_logger

logger = get_structured_logger(__name__)


class QueueService:
    """
    Service for managing task queues with ARQ

    Features:
    - Enqueue media processing tasks
    - Enqueue email sending tasks
    - Track task status
    - Defer tasks (schedule for later)

    Usage:
        queue_service = QueueService()
        await queue_service.initialize()

        task_id = await queue_service.enqueue_media_processing(
            media_id=123,
            file_path="/path/to/file.jpg"
        )
    """

    def __init__(self):
        """Initialize queue service"""
        self.redis: Optional[ArqRedis] = None
        self.initialized = False

    async def initialize(self):
        """Initialize Redis connection pool for ARQ"""
        if self.initialized:
            return

        try:
            self.redis = await create_pool(
                {
                    'host': settings.REDIS_HOST,
                    'port': settings.REDIS_PORT,
                    'database': settings.REDIS_DB,
                    'password': settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                }
            )
            self.initialized = True
            logger.info("ARQ Queue initialized",
                       host=settings.REDIS_HOST,
                       port=settings.REDIS_PORT)
        except Exception as e:
            logger.error("Failed to initialize ARQ queue", error=str(e))
            raise

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self.initialized = False

    # Media Processing Tasks

    async def enqueue_media_processing(
        self,
        media_id: int,
        file_path: str,
        operations: list = None
    ) -> str:
        """
        Enqueue media processing task

        Args:
            media_id: ID of the media record
            file_path: Path to the media file
            operations: List of operations ['thumbnail', 'optimize']

        Returns:
            Task ID (ARQ job ID)
        """
        if not self.initialized:
            await self.initialize()

        job = await self.redis.enqueue_job(
            'process_media',
            media_id,
            file_path,
            operations or ['thumbnail', 'optimize']
        )

        logger.info("Enqueued media processing task",
                   media_id=media_id,
                   job_id=job.job_id,
                   operations=operations or ['thumbnail', 'optimize'])
        return job.job_id

    async def enqueue_thumbnail_generation(
        self,
        media_id: int,
        file_path: str,
        thumbnail_size: tuple = (300, 300)
    ) -> str:
        """
        Enqueue thumbnail generation task

        Args:
            media_id: ID of the media record
            file_path: Path to the image
            thumbnail_size: Target size (width, height)

        Returns:
            Task ID
        """
        if not self.initialized:
            await self.initialize()

        job = await self.redis.enqueue_job(
            'generate_thumbnail',
            media_id,
            file_path,
            thumbnail_size
        )

        logger.info("Enqueued thumbnail generation task",
                   media_id=media_id,
                   job_id=job.job_id,
                   thumbnail_size=thumbnail_size)
        return job.job_id

    async def enqueue_image_optimization(
        self,
        media_id: int,
        file_path: str,
        quality: int = 85
    ) -> str:
        """
        Enqueue image optimization task

        Args:
            media_id: ID of the media record
            file_path: Path to the image
            quality: JPEG quality (1-100)

        Returns:
            Task ID
        """
        if not self.initialized:
            await self.initialize()

        job = await self.redis.enqueue_job(
            'optimize_image',
            media_id,
            file_path,
            quality
        )

        logger.info("Enqueued image optimization task",
                   media_id=media_id,
                   job_id=job.job_id,
                   quality=quality)
        return job.job_id

    # Email Tasks

    async def enqueue_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str = None,
        user_id: int = None
    ) -> str:
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
        """
        if not self.initialized:
            await self.initialize()

        job = await self.redis.enqueue_job(
            'send_single_email',
            to_email,
            subject,
            body,
            html_body,
            user_id
        )

        logger.info("Enqueued email sending task",
                   to_email=to_email,
                   job_id=job.job_id,
                   subject=subject)
        return job.job_id

    async def enqueue_bulk_emails(
        self,
        emails: list,
        rate_limit: int = 10,
        user_id: int = None
    ) -> str:
        """
        Enqueue bulk email sending task

        Args:
            emails: List of dicts with email data
            rate_limit: Max emails per minute
            user_id: User who triggered this

        Returns:
            Task ID
        """
        if not self.initialized:
            await self.initialize()

        job = await self.redis.enqueue_job(
            'send_bulk_emails',
            emails,
            rate_limit,
            user_id
        )

        logger.info("Enqueued bulk emails task",
                   email_count=len(emails),
                   job_id=job.job_id,
                   rate_limit=rate_limit)
        return job.job_id

    # Task Status

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task

        Args:
            task_id: ARQ job ID

        Returns:
            Dict with task status or None if not found
        """
        if not self.initialized:
            await self.initialize()

        # Get job info from ARQ
        job = await self.redis.get_job(task_id)

        if not job:
            return None

        result = {
            "task_id": task_id,
            "status": job.status,
            "enqueue_time": job.enqueue_time.isoformat() if job.enqueue_time else None,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "finish_time": job.finish_time.isoformat() if job.finish_time else None,
        }

        # Try to get additional status from Redis
        status_key = f"task_status:{task_id}"
        status_data = await self.redis.get(status_key)
        if status_data:
            result["extra"] = eval(status_data)  # Convert string back to dict

        return result

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task

        Args:
            task_id: ARQ job ID

        Returns:
            True if cancelled, False otherwise
        """
        if not self.initialized:
            await self.initialize()

        try:
            job = await self.redis.get_job(task_id)
            if job and job.status == "queued":
                await job.abort()
                logger.info("Task cancelled", task_id=task_id)
                return True
        except Exception as e:
            logger.error("Failed to cancel task", task_id=task_id, error=str(e))

        return False


# Global instance
queue_service = QueueService()
