from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models.cors_origin import CorsOriginCreate, CorsOriginRead, CorsOriginUpdate
from app.services.cors_service import cors_service

router = APIRouter(prefix="/cors", tags=["CORS Management"])


@router.get("/origins", response_model=List[CorsOriginRead])
def get_all_cors_origins(
    include_inactive: bool = False,
    session: Session = Depends(get_session)
):
    """
    Get all CORS origins (admin only).

    Args:
        include_inactive: Include inactive origins in results

    Returns:
        List of CORS origin configurations
    """
    origins = cors_service.get_all(session, include_inactive=include_inactive)
    return origins


@router.get("/origins/active")
def get_active_cors_origins(
    session: Session = Depends(get_session)
):
    """
    Get currently active CORS origins (same as used by middleware).
    Returns ["*"] if database is empty.

    Returns:
        List of active origin URLs
    """
    origins = cors_service.get_active_origins(session)
    return {"origins": origins}


@router.get("/origins/{origin_id}", response_model=CorsOriginRead)
def get_cors_origin(
    origin_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific CORS origin by ID"""
    origin = cors_service.get_by_id(session, origin_id)
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CORS origin with id {origin_id} not found"
        )
    return origin


@router.post("/origins", response_model=CorsOriginRead, status_code=status.HTTP_201_CREATED)
def create_cors_origin(
    origin_data: CorsOriginCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new CORS origin (admin only).

    The origin must be in format: http://example.com or https://example.com:3000
    Wildcards are not allowed except "*" alone.

    After creating, the CORS cache is invalidated.
    Server restart is NOT required - changes take effect on next request.

    Example:
    ```json
    {
        "origin": "http://localhost:3000",
        "description": "React development server",
        "is_active": true
    }
    ```
    """
    try:
        origin = cors_service.create(session, origin_data)
        return origin
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/origins/{origin_id}", response_model=CorsOriginRead)
def update_cors_origin(
    origin_id: int,
    origin_data: CorsOriginUpdate,
    session: Session = Depends(get_session)
):
    """
    Update a CORS origin (admin only).

    After updating, the CORS cache is invalidated.
    Server restart is NOT required - changes take effect on next request.
    """
    try:
        origin = cors_service.update(session, origin_id, origin_data)
        if not origin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CORS origin with id {origin_id} not found"
            )
        return origin
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/origins/{origin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cors_origin(
    origin_id: int,
    session: Session = Depends(get_session)
):
    """
    Delete a CORS origin (admin only).

    After deleting, the CORS cache is invalidated.
    Server restart is NOT required - changes take effect on next request.

    Warning: If you delete all origins, CORS will default to "*" (allow all).
    """
    deleted = cors_service.delete(session, origin_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CORS origin with id {origin_id} not found"
        )
    return None


@router.post("/cache/invalidate", status_code=status.HTTP_200_OK)
def invalidate_cors_cache():
    """
    Manually invalidate CORS cache (admin only).

    Forces reload of CORS origins from database on next request.
    Useful after bulk updates or if cache gets stale.
    """
    cors_service.invalidate_cache()
    return {"message": "CORS cache invalidated successfully"}
