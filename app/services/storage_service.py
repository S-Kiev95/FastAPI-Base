"""
Generic storage service that supports both S3/MinIO and local filesystem.
Automatically switches based on configuration.
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from datetime import datetime, timedelta

from app.config import settings


class StorageService:
    """
    Generic storage service with S3/MinIO and local filesystem support.

    Features:
    - Automatic backend selection (S3 or local)
    - Upload, download, delete operations
    - Pre-signed URL generation (for S3)
    - File metadata extraction
    - Automatic file organization by date
    """

    def __init__(self):
        self.use_s3 = settings.USE_S3
        self.s3_client = None
        self.bucket_name = settings.S3_BUCKET_NAME
        self.media_folder = Path(settings.MEDIA_FOLDER)

        if self.use_s3:
            self._init_s3()
        else:
            self._init_local_storage()

    def _init_s3(self):
        """Initialize S3/MinIO client"""
        try:
            import boto3
            from botocore.config import Config

            # Configure boto3 client
            config = Config(
                region_name=settings.S3_REGION,
                signature_version='s3v4',
            )

            # If endpoint_url is provided, use it (for MinIO)
            # Otherwise, use default AWS S3
            client_kwargs = {
                'service_name': 's3',
                'aws_access_key_id': settings.S3_ACCESS_KEY,
                'aws_secret_access_key': settings.S3_SECRET_KEY,
                'config': config
            }

            if settings.S3_ENDPOINT_URL:
                client_kwargs['endpoint_url'] = settings.S3_ENDPOINT_URL

            self.s3_client = boto3.client(**client_kwargs)

            # Create bucket if it doesn't exist
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"S3 bucket '{self.bucket_name}' is ready")
            except:
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    print(f"Created S3 bucket: {self.bucket_name}")
                except Exception as e:
                    print(f"Warning: Could not create bucket '{self.bucket_name}': {e}")

        except ImportError:
            print("WARNING: boto3 not installed. Install with: uv add boto3")
            print("Falling back to local storage")
            self.use_s3 = False
            self._init_local_storage()
        except Exception as e:
            print(f"WARNING: Failed to initialize S3: {e}")
            print("Falling back to local storage")
            self.use_s3 = False
            self._init_local_storage()

    def _init_local_storage(self):
        """Initialize local storage folder"""
        self.media_folder.mkdir(parents=True, exist_ok=True)
        print(f"Local storage initialized at: {self.media_folder.absolute()}")

    def _generate_file_path(self, original_filename: str) -> str:
        """
        Generate a unique file path organized by date.
        Format: YYYY/MM/DD/uuid_filename.ext
        """
        now = datetime.utcnow()
        date_path = f"{now.year}/{now.month:02d}/{now.day:02d}"

        # Generate unique filename
        file_ext = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        return f"{date_path}/{unique_filename}"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal attacks"""
        return Path(filename).name

    async def upload_file(
        self,
        file: BinaryIO,
        original_filename: str,
        content_type: Optional[str] = None
    ) -> Tuple[str, int]:
        """
        Upload a file to storage.

        Args:
            file: File-like object (file content)
            original_filename: Original filename
            content_type: MIME type (optional)

        Returns:
            Tuple of (file_path, file_size)
        """
        # Sanitize filename
        safe_filename = self._sanitize_filename(original_filename)

        # Generate storage path
        storage_path = self._generate_file_path(safe_filename)

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        if self.use_s3:
            return await self._upload_to_s3(storage_path, file_content, content_type, file_size)
        else:
            return await self._upload_to_local(storage_path, file_content, file_size)

    async def _upload_to_s3(
        self,
        storage_path: str,
        file_content: bytes,
        content_type: Optional[str],
        file_size: int
    ) -> Tuple[str, int]:
        """Upload file to S3/MinIO"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=storage_path,
                Body=file_content,
                **extra_args
            )

            print(f"Uploaded to S3: {storage_path}")
            return storage_path, file_size

        except Exception as e:
            raise Exception(f"Failed to upload to S3: {e}")

    async def _upload_to_local(
        self,
        storage_path: str,
        file_content: bytes,
        file_size: int
    ) -> Tuple[str, int]:
        """Upload file to local filesystem"""
        try:
            full_path = self.media_folder / storage_path

            # Create directory if it doesn't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(full_path, 'wb') as f:
                f.write(file_content)

            print(f"Uploaded locally: {storage_path}")
            return storage_path, file_size

        except Exception as e:
            raise Exception(f"Failed to upload to local storage: {e}")

    async def download_file(self, file_path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            file_path: Path to the file in storage

        Returns:
            File content as bytes
        """
        if self.use_s3:
            return await self._download_from_s3(file_path)
        else:
            return await self._download_from_local(file_path)

    async def _download_from_s3(self, file_path: str) -> bytes:
        """Download file from S3/MinIO"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return response['Body'].read()
        except Exception as e:
            raise Exception(f"Failed to download from S3: {e}")

    async def _download_from_local(self, file_path: str) -> bytes:
        """Download file from local filesystem"""
        try:
            full_path = self.media_folder / file_path

            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to download from local storage: {e}")

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Path to the file in storage

        Returns:
            True if deleted successfully
        """
        if self.use_s3:
            return await self._delete_from_s3(file_path)
        else:
            return await self._delete_from_local(file_path)

    async def _delete_from_s3(self, file_path: str) -> bool:
        """Delete file from S3/MinIO"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            print(f"Deleted from S3: {file_path}")
            return True
        except Exception as e:
            print(f"Failed to delete from S3: {e}")
            return False

    async def _delete_from_local(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            full_path = self.media_folder / file_path

            if full_path.exists():
                full_path.unlink()
                print(f"Deleted locally: {file_path}")

                # Clean up empty directories
                try:
                    full_path.parent.rmdir()
                except OSError:
                    pass  # Directory not empty, that's fine

                return True
            return False
        except Exception as e:
            print(f"Failed to delete from local storage: {e}")
            return False

    def get_presigned_url(
        self,
        file_path: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a pre-signed URL for direct file access (S3 only).
        For local storage, returns None (use download endpoint instead).

        Args:
            file_path: Path to the file in storage
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Pre-signed URL or None
        """
        if not self.use_s3:
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Failed to generate presigned URL: {e}")
            return None

    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            file_path: Path to the file in storage

        Returns:
            True if file exists
        """
        if self.use_s3:
            try:
                self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )
                return True
            except:
                return False
        else:
            full_path = self.media_folder / file_path
            return full_path.exists()

    def get_storage_info(self) -> dict:
        """Get storage backend information"""
        return {
            "backend": "s3" if self.use_s3 else "local",
            "bucket_name": self.bucket_name if self.use_s3 else None,
            "media_folder": str(self.media_folder.absolute()) if not self.use_s3 else None,
            "endpoint_url": settings.S3_ENDPOINT_URL if self.use_s3 else None
        }


# Singleton instance
storage_service = StorageService()
