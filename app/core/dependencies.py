"""
Authentication dependencies for protecting routes.
Supports both JWT and OAuth authentication.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from typing import Optional

from app.database import get_session
from app.core.security import verify_token
from app.services.user_service import user_service
from app.models.user import UserRead

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> UserRead:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        session: Database session

    Returns:
        UserRead: Current user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token and get email
    token = credentials.credentials
    email = verify_token(token)

    if email is None:
        raise credentials_exception

    # Get user from database
    user = user_service.get_user_by_email(session, email)

    if user is None:
        raise credentials_exception

    # Convert to UserRead
    return UserRead.model_validate(user)


async def get_current_active_user(
    current_user: UserRead = Depends(get_current_user)
) -> UserRead:
    """
    Ensure current user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        UserRead: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: UserRead = Depends(get_current_active_user)
) -> UserRead:
    """
    Ensure current user has verified email.

    Args:
        current_user: Current active user

    Returns:
        UserRead: Current verified user

    Raises:
        HTTPException: If email is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    return current_user


# Optional authentication (returns None if no token)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    session: Session = Depends(get_session)
) -> Optional[UserRead]:
    """
    Get current user if authenticated, None otherwise.
    Useful for endpoints that work with or without authentication.

    Args:
        credentials: Optional HTTP Authorization credentials
        session: Database session

    Returns:
        UserRead or None: Current user if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        email = verify_token(token)

        if email is None:
            return None

        user = user_service.get_user_by_email(session, email)
        return UserRead.model_validate(user) if user else None

    except Exception:
        return None
