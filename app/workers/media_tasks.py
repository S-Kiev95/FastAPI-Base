"""
Media processing tasks for ARQ workers

Tasks:
- generate_thumbnail: Create thumbnail from image
- optimize_image: Compress and optimize image
- process_media: Complete media processing pipeline
"""
import os
import io
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from PIL import Image

from app.config import settings
from app.utils.logger import get_structured_logger, LogContext

logger = get_structured_logger(__name__)


async def generate_thumbnail(
    ctx: Dict[str, Any],
    media_id: int,
    file_path: str,
    thumbnail_size: tuple = (300, 300)
) -> Dict[str, Any]:
    """
    Generate thumbnail for an image

    Args:
        ctx: ARQ context (includes redis, job_id, etc.)
        media_id: ID of the media record
        file_path: Path to the original image
        thumbnail_size: Target thumbnail size (width, height)

    Returns:
        Dict with thumbnail path and metadata
    """
    job_id = ctx.get("job_id")
    with LogContext(job_id=job_id, media_id=media_id, task="generate_thumbnail"):
        logger.info("Starting thumbnail generation", thumbnail_size=thumbnail_size)

        # Update task status to processing
        await _update_task_status(ctx, "processing", progress=10)

        try:
            # Load image
            img = Image.open(file_path)

            await _update_task_status(ctx, "processing", progress=30)

            # Create thumbnail
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            await _update_task_status(ctx, "processing", progress=60)

            # Save thumbnail
            file_path_obj = Path(file_path)
            thumbnail_path = file_path_obj.parent / f"{file_path_obj.stem}_thumb{file_path_obj.suffix}"
            img.save(thumbnail_path, optimize=True, quality=85)

            await _update_task_status(ctx, "processing", progress=90)

            result = {
                "media_id": media_id,
                "thumbnail_path": str(thumbnail_path),
                "thumbnail_size": img.size,
                "original_size": Image.open(file_path).size,
            }

            # Publish notification
            await _publish_notification(ctx, media_id, "thumbnail_generated", result)

            logger.info("Thumbnail generated successfully", thumbnail_path=str(thumbnail_path))
            return result

        except Exception as e:
            error_msg = f"Failed to generate thumbnail: {str(e)}"
            logger.error("Thumbnail generation failed", error=str(e))
            await _publish_notification(ctx, media_id, "thumbnail_failed", {"error": error_msg})
            raise


async def optimize_image(
    ctx: Dict[str, Any],
    media_id: int,
    file_path: str,
    quality: int = 85,
    max_size: tuple = (2048, 2048)
) -> Dict[str, Any]:
    """
    Optimize image: compress and resize if too large

    Args:
        ctx: ARQ context
        media_id: ID of the media record
        file_path: Path to the image
        quality: JPEG quality (1-100)
        max_size: Maximum dimensions

    Returns:
        Dict with optimized image info
    """
    job_id = ctx.get("job_id")
    with LogContext(job_id=job_id, media_id=media_id, task="optimize_image"):
        logger.info("Starting image optimization", quality=quality, max_size=max_size)

        await _update_task_status(ctx, "processing", progress=10)

        try:
            # Load image
            img = Image.open(file_path)
            original_size = os.path.getsize(file_path)

            await _update_task_status(ctx, "processing", progress=30)

            # Resize if too large
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

            await _update_task_status(ctx, "processing", progress=60)

            # Save optimized version
            file_path_obj = Path(file_path)
            optimized_path = file_path_obj.parent / f"{file_path_obj.stem}_optimized{file_path_obj.suffix}"

            # Convert RGBA to RGB if saving as JPEG
            if img.mode == 'RGBA' and file_path_obj.suffix.lower() in ['.jpg', '.jpeg']:
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img

            img.save(optimized_path, optimize=True, quality=quality)

            await _update_task_status(ctx, "processing", progress=90)

            optimized_size = os.path.getsize(optimized_path)
            compression_ratio = (1 - optimized_size / original_size) * 100

            result = {
                "media_id": media_id,
                "optimized_path": str(optimized_path),
                "original_size_bytes": original_size,
                "optimized_size_bytes": optimized_size,
                "compression_ratio_percent": round(compression_ratio, 2),
                "dimensions": img.size,
            }

            # Publish notification
            await _publish_notification(ctx, media_id, "image_optimized", result)

            logger.info("Image optimized successfully",
                       optimized_path=str(optimized_path),
                       compression_ratio=round(compression_ratio, 2))
            return result

        except Exception as e:
            error_msg = f"Failed to optimize image: {str(e)}"
            logger.error("Image optimization failed", error=str(e))
            await _publish_notification(ctx, media_id, "optimization_failed", {"error": error_msg})
            raise


async def process_media(
    ctx: Dict[str, Any],
    media_id: int,
    file_path: str,
    operations: list = None
) -> Dict[str, Any]:
    """
    Complete media processing pipeline

    Args:
        ctx: ARQ context
        media_id: ID of the media record
        file_path: Path to the media file
        operations: List of operations to perform ['thumbnail', 'optimize']

    Returns:
        Dict with all processing results
    """
    if operations is None:
        operations = ['thumbnail', 'optimize']

    job_id = ctx.get("job_id")
    with LogContext(job_id=job_id, media_id=media_id, task="process_media"):
        logger.info("Starting media processing", operations=operations)

        await _update_task_status(ctx, "processing", progress=5)

        results = {
            "media_id": media_id,
            "operations": {},
        }

        try:
            # Check if file is an image
            try:
                img = Image.open(file_path)
                img.verify()  # Verify it's a valid image
            except Exception:
                raise ValueError("File is not a valid image")

            total_ops = len(operations)

            # Generate thumbnail
            if 'thumbnail' in operations:
                await _update_task_status(ctx, "processing", progress=20)
                thumbnail_result = await generate_thumbnail(ctx, media_id, file_path)
                results["operations"]["thumbnail"] = thumbnail_result

            # Optimize image
            if 'optimize' in operations:
                progress = 50 if 'thumbnail' in operations else 20
                await _update_task_status(ctx, "processing", progress=progress)
                optimize_result = await optimize_image(ctx, media_id, file_path)
                results["operations"]["optimize"] = optimize_result

            await _update_task_status(ctx, "processing", progress=95)

            # Publish final notification
            await _publish_notification(ctx, media_id, "media_processed", results)

            logger.info("Media processing completed successfully", operations_count=len(results["operations"]))
            return results

        except Exception as e:
            error_msg = f"Failed to process media: {str(e)}"
            logger.error("Media processing failed", error=str(e))
            await _publish_notification(ctx, media_id, "processing_failed", {"error": error_msg})
            raise


# Helper functions

async def _update_task_status(ctx: Dict[str, Any], status: str, progress: int = None):
    """Update task status in Redis"""
    job_id = ctx.get("job_id")
    if not job_id:
        return

    redis = ctx["redis"]

    data = {"status": status}
    if progress is not None:
        data["progress"] = progress
    data["updated_at"] = datetime.utcnow().isoformat()

    # Store in Redis with TTL of 1 hour
    await redis.setex(
        f"task_status:{job_id}",
        3600,  # 1 hour TTL
        str(data)
    )


async def _publish_notification(
    ctx: Dict[str, Any],
    media_id: int,
    event_type: str,
    data: Dict[str, Any]
):
    """Publish notification via Redis Pub/Sub for WebSocket relay"""
    redis = ctx["redis"]
    job_id = ctx.get("job_id")

    notification = {
        "job_id": job_id,
        "media_id": media_id,
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Publish to channel that WebSocket handler will listen to
    channel = f"task_notifications:{media_id}"
    await redis.publish(channel, str(notification))

    logger.debug("Published notification", channel=channel, event_type=event_type)
