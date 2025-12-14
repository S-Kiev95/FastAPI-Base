from datetime import datetime
from typing import Optional
from sqlmodel import Session, select
from app.models.user import User, UserCreate, UserUpdate, UserRead
from app.services.base_service import BaseService
from app.services.websocket import users_channel


class UserService(BaseService[User, UserCreate, UserUpdate, UserRead]):
    """
    Service layer for user operations.

    Inherits from BaseService to get automatic CRUD operations with WebSocket broadcasting:
    - create() - Create user with broadcast
    - update() - Update user with broadcast
    - delete() - Delete user with broadcast
    - get_by_id() - Get user by ID
    - get_all() - Get all users with pagination

    Additional user-specific methods are defined below.
    """

    def __init__(self):
        """Initialize UserService with User model and users WebSocket channel."""
        super().__init__(
            model=User,
            channel=users_channel,
            read_schema=UserRead
        )

    def get_user_by_email(self, session: Session, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Args:
            session: Database session
            email: User email address

        Returns:
            User if found, None otherwise
        """
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()

    def get_user_by_provider(
        self,
        session: Session,
        provider: str,
        provider_user_id: str
    ) -> Optional[User]:
        """
        Get a user by OAuth provider and provider user ID.

        Args:
            session: Database session
            provider: OAuth provider name (e.g., "google", "github")
            provider_user_id: User ID from the OAuth provider

        Returns:
            User if found, None otherwise
        """
        statement = select(User).where(
            User.provider == provider,
            User.provider_user_id == provider_user_id
        )
        return session.exec(statement).first()

    def update_last_login(self, session: Session, user_id: int) -> Optional[User]:
        """
        Update user's last login timestamp.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            Updated user if found, None otherwise
        """
        user = session.get(User, user_id)
        if not user:
            return None

        user.last_login = datetime.utcnow()
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    async def get_or_create_user(
        self,
        session: Session,
        provider: str,
        provider_user_id: str,
        user_data: UserCreate,
        broadcast: bool = True
    ) -> tuple[User, bool]:
        """
        Get existing user or create new one (useful for OAuth login).

        Args:
            session: Database session
            provider: OAuth provider name
            provider_user_id: User ID from the OAuth provider
            user_data: User data for creation if user doesn't exist
            broadcast: Whether to broadcast if user is created (default: True)

        Returns:
            Tuple of (user, created) where created is True if user was just created
        """
        user = self.get_user_by_provider(session, provider, provider_user_id)

        if user:
            # Update last login for existing user
            user.last_login = datetime.utcnow()
            session.add(user)
            session.commit()
            session.refresh(user)
            return user, False

        # Create new user using inherited create method
        user = await self.create(session, user_data, broadcast=broadcast)
        return user, True


# Create a singleton instance for easy access
user_service = UserService()
