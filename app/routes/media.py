"""
Media routes for file upload, download, and management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from io import BytesIO

from app.database import get_session
from app.services.media_service import media_service
from app.models.media import MediaRead, MediaUpdate, MediaUploadResponse
from app.services.filters import QueryFilter
from app.config import settings


router = APIRouter(prefix="/media", tags=["media"])


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
    is_public: bool = Form(False),
    session: Session = Depends(get_session)
):
    """
    Upload a file to storage.

    - **file**: The file to upload (multipart/form-data)
    - **description**: Optional description
    - **alt_text**: Optional alt text for accessibility
    - **user_id**: Optional owner user ID
    - **is_public**: Whether the file is publicly accessible
    """
    # Validate file size
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
        )

    # Reset file pointer
    await file.seek(0)

    # Upload file
    media = await media_service.upload_file(
        session=session,
        file=file.file,
        filename=file.filename or "unnamed",
        mime_type=file.content_type,
        description=description,
        alt_text=alt_text,
        user_id=user_id,
        is_public=is_public,
        broadcast=True
    )

    # Generate URLs
    media_read = media_service.get_media_with_urls(session, media.id)

    return MediaUploadResponse(
        id=media_read.id,
        filename=media_read.filename,
        file_size=media_read.file_size,
        file_type=media_read.file_type,
        url=media_read.url,
        download_url=media_read.download_url,
        message="File uploaded successfully"
    )


@router.get("/", response_model=List[MediaRead])
def get_all_media(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all media files with URLs"""
    return media_service.get_all_with_urls(session, skip, limit)


@router.get("/{media_id}", response_model=MediaRead)
def get_media(
    media_id: int,
    session: Session = Depends(get_session)
):
    """Get media by ID with URLs"""
    media = media_service.get_media_with_urls(session, media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media {media_id} not found"
        )
    return media


@router.get("/{media_id}/download")
async def download_file(
    media_id: int,
    session: Session = Depends(get_session)
):
    """
    Download file content.
    Returns the actual file for download.
    """
    try:
        file_content, filename, mime_type = await media_service.download_file(session, media_id)

        return StreamingResponse(
            BytesIO(file_content),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media {media_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.patch("/{media_id}", response_model=MediaRead)
async def update_media(
    media_id: int,
    media_update: MediaUpdate,
    session: Session = Depends(get_session)
):
    """
    Update media metadata (not the file itself).
    To replace the file, delete and upload a new one.
    """
    media = await media_service.update(session, media_id, media_update, broadcast=True)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media {media_id} not found"
        )

    # Return with URLs
    return media_service.get_media_with_urls(session, media.id)


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: int,
    session: Session = Depends(get_session)
):
    """
    Delete media file and metadata.
    Removes both the database record and the file from storage.
    """
    success = await media_service.delete_media(session, media_id, broadcast=True)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media {media_id} not found"
        )


@router.get("/user/{user_id}", response_model=List[MediaRead])
def get_media_by_user(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all media files for a specific user"""
    media_list = media_service.get_by_user(session, user_id, skip, limit)

    # Add URLs to each media
    result = []
    for media in media_list:
        media_read = MediaRead.model_validate(media)
        media_read = media_service._add_urls_to_media(media_read)
        result.append(media_read)

    return result


@router.get("/type/{file_type}", response_model=List[MediaRead])
def get_media_by_type(
    file_type: str,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """
    Get all media files of a specific type.
    Types: image, video, audio, document, other
    """
    media_list = media_service.get_by_file_type(session, file_type, skip, limit)

    # Add URLs to each media
    result = []
    for media in media_list:
        media_read = MediaRead.model_validate(media)
        media_read = media_service._add_urls_to_media(media_read)
        result.append(media_read)

    return result


@router.get("/public/list", response_model=List[MediaRead])
def get_public_media(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all public media files"""
    media_list = media_service.get_public_media(session, skip, limit)

    # Add URLs to each media
    result = []
    for media in media_list:
        media_read = MediaRead.model_validate(media)
        media_read = media_service._add_urls_to_media(media_read)
        result.append(media_read)

    return result


@router.post("/filter", response_model=List[MediaRead])
def filter_media(
    filters: QueryFilter,
    session: Session = Depends(get_session)
):
    """
    Filter media with advanced queries.
    Supports complex conditions, ordering, and pagination.
    """
    media_list = media_service.filter(session, filters)

    # Add URLs to each media
    result = []
    for media in media_list:
        media_read = MediaRead.model_validate(media)
        media_read = media_service._add_urls_to_media(media_read)
        result.append(media_read)

    return result


@router.post("/filter/paginated")
def filter_media_paginated(
    filters: QueryFilter,
    session: Session = Depends(get_session)
):
    """
    Filter media with pagination metadata.
    Returns: {data, total, limit, offset, has_more}
    """
    result = media_service.filter_paginated(session, filters)

    # Add URLs to each media in data
    media_with_urls = []
    for media in result["data"]:
        media_read = MediaRead.model_validate(media)
        media_read = media_service._add_urls_to_media(media_read)
        media_with_urls.append(media_read)

    result["data"] = media_with_urls

    return result


@router.get("/stats/info")
def get_storage_info():
    """Get storage backend information"""
    from app.services.storage_service import storage_service
    return storage_service.get_storage_info()
