"""
Media service for handling multimedia files.
Integrates with StorageService for file storage and BaseService for CRUD operations.
"""
from typing import BinaryIO, Optional
from sqlmodel import Session, select

from app.services.base_service import BaseService
from app.services.storage_service import storage_service
from app.models.media import Media, MediaCreate, MediaUpdate, MediaRead
from app.config import settings


class MediaService(BaseService[Media, MediaCreate, MediaUpdate, MediaRead]):
    """
    Service for managing multimedia files.

    Features:
    - Upload files to S3/MinIO or local storage
    - Store file metadata in database
    - Generate access URLs
    - Automatic WebSocket broadcasting on changes
    """

    def __init__(self):
        # Import here to avoid circular dependency
        from app.services.websocket.channels import media_channel

        super().__init__(
            model=Media,
            channel=media_channel,
            read_schema=MediaRead
        )

    def _detect_file_type(self, mime_type: Optional[str]) -> str:
        """Detect file type category from MIME type"""
        if not mime_type:
            return "other"

        mime_type = mime_type.lower()

        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"
        elif mime_type.startswith("audio/"):
            return "audio"
        elif mime_type in ["application/pdf", "application/msword",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "application/vnd.ms-excel",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return "document"
        else:
            return "other"

    async def upload_file(
        self,
        session: Session,
        file: BinaryIO,
        filename: str,
        mime_type: Optional[str] = None,
        description: Optional[str] = None,
        alt_text: Optional[str] = None,
        user_id: Optional[int] = None,
        is_public: bool = False,
        broadcast: bool = True
    ) -> Media:
        """
        Upload a file and create media record.

        Args:
            session: Database session
            file: File-like object
            filename: Original filename
            mime_type: MIME type
            description: File description
            alt_text: Alt text for accessibility
            user_id: Owner user ID
            is_public: Public access flag
            broadcast: Whether to broadcast via WebSocket

        Returns:
            Created Media object
        """
        # Upload file to storage
        storage_path, file_size = await storage_service.upload_file(
            file=file,
            original_filename=filename,
            content_type=mime_type
        )

        # Detect file type
        file_type = self._detect_file_type(mime_type)

        # Create media record
        media_data = MediaCreate(
            filename=filename,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            file_type=file_type,
            description=description,
            alt_text=alt_text,
            user_id=user_id,
            storage_backend="s3" if storage_service.use_s3 else "local",
            is_public=is_public
        )

        # Use parent's create method (includes WebSocket broadcast)
        media = await self.create(session, media_data, broadcast=broadcast)

        return media

    async def get_media_with_urls(
        self,
        session: Session,
        media_id: int,
        generate_presigned: bool = True
    ) -> Optional[MediaRead]:
        """
        Get media by ID with access URLs.

        Args:
            session: Database session
            media_id: Media ID
            generate_presigned: Generate pre-signed URL for S3

        Returns:
            MediaRead with URLs or None
        """
        media = self.get_by_id(session, media_id)
        if not media:
            return None

        # Convert to read schema
        media_read = MediaRead.model_validate(media)

        # Generate URLs
        media_read = self._add_urls_to_media(media_read, generate_presigned)

        return media_read

    def get_all_with_urls(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
        generate_presigned: bool = True
    ) -> list[MediaRead]:
        """
        Get all media with access URLs.

        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            generate_presigned: Generate pre-signed URLs for S3

        Returns:
            List of MediaRead with URLs
        """
        media_list = self.get_all(session, skip, limit)

        # Convert to read schema and add URLs
        result = []
        for media in media_list:
            media_read = MediaRead.model_validate(media)
            media_read = self._add_urls_to_media(media_read, generate_presigned)
            result.append(media_read)

        return result

    def _add_urls_to_media(
        self,
        media: MediaRead,
        generate_presigned: bool = True
    ) -> MediaRead:
        """Add access URLs to media object"""
        # Base download URL (always available)
        media.download_url = f"/media/{media.id}/download"

        # Pre-signed URL for S3 (direct access, temporary)
        if storage_service.use_s3 and generate_presigned:
            presigned_url = storage_service.get_presigned_url(media.storage_path)
            if presigned_url:
                media.url = presigned_url

        # For local storage or if presigned failed, use download endpoint
        if not media.url:
            media.url = media.download_url

        return media

    async def download_file(self, session: Session, media_id: int) -> tuple[bytes, str, str]:
        """
        Download file content.

        Args:
            session: Database session
            media_id: Media ID

        Returns:
            Tuple of (file_content, filename, mime_type)
        """
        media = self.get_by_id(session, media_id)
        if not media:
            raise FileNotFoundError(f"Media {media_id} not found")

        # Download file from storage
        file_content = await storage_service.download_file(media.storage_path)

        return file_content, media.filename, media.mime_type or "application/octet-stream"

    async def delete_media(
        self,
        session: Session,
        media_id: int,
        broadcast: bool = True
    ) -> bool:
        """
        Delete media record and file from storage.

        Args:
            session: Database session
            media_id: Media ID
            broadcast: Whether to broadcast via WebSocket

        Returns:
            True if deleted successfully
        """
        media = self.get_by_id(session, media_id)
        if not media:
            return False

        # Delete file from storage
        await storage_service.delete_file(media.storage_path)

        # Delete database record (includes WebSocket broadcast)
        return await self.delete(session, media_id, broadcast=broadcast)

    def get_by_user(
        self,
        session: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Media]:
        """Get all media files for a specific user"""
        statement = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(session.exec(statement).all())

    def get_by_file_type(
        self,
        session: Session,
        file_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Media]:
        """Get all media files of a specific type (image, video, audio, document, other)"""
        statement = (
            select(self.model)
            .where(self.model.file_type == file_type)
            .offset(skip)
            .limit(limit)
        )
        return list(session.exec(statement).all())

    def get_public_media(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> list[Media]:
        """Get all public media files"""
        statement = (
            select(self.model)
            .where(self.model.is_public == True)
            .offset(skip)
            .limit(limit)
        )
        return list(session.exec(statement).all())


# Singleton instance
media_service = MediaService()
