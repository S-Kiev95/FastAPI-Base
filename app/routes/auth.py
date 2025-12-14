"""
Authentication routes for user registration and login.
Supports local authentication (email/password) alongside OAuth.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models.user import UserRegister, UserLogin, Token, UserRead, User
from app.services.user_service import user_service
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user, get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    session: Session = Depends(get_session)
):
    """
    Register a new user with email and password (local authentication).

    - **email**: Valid email address (must be unique)
    - **password**: Password (will be hashed before storage)
    - **name**: Optional user name

    Returns the created user data (without password).
    """
    # Check if user already exists
    existing_user = user_service.get_user_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user with hashed password
    user = User(
        email=user_data.email,
        name=user_data.name,
        provider="local",
        provider_user_id=None,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_verified=False  # Email verification can be implemented later
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    # Broadcast via WebSocket
    user_dict = UserRead.model_validate(user).model_dump()
    await user_service.channel.broadcast_created(user_dict)

    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    session: Session = Depends(get_session)
):
    """
    Login with email and password.

    Returns a JWT access token on successful authentication.

    - **email**: User email
    - **password**: User password

    Use the returned token in the Authorization header:
    `Authorization: Bearer <token>`
    """
    # Get user by email
    user = user_service.get_user_by_email(session, credentials.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify this is a local auth user (not OAuth)
    if user.provider != "local" or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This account uses {user.provider} authentication. Please login with {user.provider}."
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Create access token
    access_token_expires = timedelta(minutes=30)  # 30 minutes
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: UserRead = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.

    Returns the current user's profile data.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: UserRead = Depends(get_current_user)
):
    """
    Refresh access token.

    Requires valid JWT token in Authorization header.

    Returns a new JWT access token.
    """
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": current_user.email},
        expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")
