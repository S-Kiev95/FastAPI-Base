from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session

from app.database import get_session
from app.models.user import UserCreate, UserRead, UserUpdate
from app.services.user_service import user_service
from app.services.filters import QueryFilter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserRead])
def get_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """
    Get all users with basic pagination (returns list only).

    For pagination metadata (total, has_more, etc.), use GET /users/paginated
    """
    users = user_service.get_all(session, skip=skip, limit=limit)
    return users


@router.get("/paginated/list")
def get_users_paginated(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """
    Get all users with complete pagination metadata.

    Returns:
    ```json
    {
        "data": [...],        # List of users
        "total": 150,         # Total count of users
        "limit": 100,         # Requested limit
        "offset": 0,          # Requested offset (skip)
        "has_more": true      # Whether more users exist
    }
    ```

    This is useful for building pagination UI components.
    """
    result = user_service.get_all_paginated(session, skip=skip, limit=limit)
    return result


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific user by ID"""
    user = user_service.get_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return user


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    """Create a new user and broadcast to WebSocket clients"""
    # Check if user with same email already exists
    existing_user = user_service.get_user_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Check if user with same provider ID already exists
    existing_provider_user = user_service.get_user_by_provider(
        session, user_data.provider, user_data.provider_user_id
    )
    if existing_provider_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this provider ID already exists"
        )

    user = await user_service.create(session, user_data)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: Session = Depends(get_session)
):
    """Update a user and broadcast to WebSocket clients"""
    user = await user_service.update(session, user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Delete a user and broadcast to WebSocket clients"""
    deleted = await user_service.delete(session, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return None


@router.get("/email/{email}", response_model=UserRead)
def get_user_by_email(
    email: str,
    session: Session = Depends(get_session)
):
    """Get a user by email"""
    user = user_service.get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found"
        )
    return user


@router.post("/filter", response_model=List[UserRead])
def filter_users(
    filters: QueryFilter = Body(...),
    session: Session = Depends(get_session)
):
    """
    Filter users with advanced query options.

    Example request body:
    ```json
    {
        "conditions": [
            {
                "field": "email",
                "operator": "icontains",
                "value": "gmail"
            },
            {
                "field": "is_active",
                "operator": "eq",
                "value": true
            }
        ],
        "operator": "and",
        "order_by": "created_at",
        "order_direction": "desc",
        "limit": 10,
        "offset": 0
    }
    ```

    Available operators:
    - eq, ne, gt, gte, lt, lte
    - contains, icontains, startswith, endswith
    - in, not_in, is_null, is_not_null
    """
    users = user_service.filter(session, filters)
    return users


@router.post("/filter/paginated")
def filter_users_paginated(
    filters: QueryFilter = Body(...),
    session: Session = Depends(get_session)
):
    """
    Filter users with pagination metadata.

    Returns:
    ```json
    {
        "data": [...],
        "total": 150,
        "limit": 10,
        "offset": 0,
        "has_more": true
    }
    ```
    """
    result = user_service.filter_paginated(session, filters)
    return result
