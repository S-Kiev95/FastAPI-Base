from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime
import re

from app.models.cors_origin import CorsOrigin, CorsOriginCreate, CorsOriginUpdate, CorsOriginRead
from app.services.cache_service import cache_service
from app.config import settings


class CorsService:
    """
    Service for managing CORS origins with caching.

    Features:
    - Get active origins from database
    - Fallback to "*" if database is empty
    - Cache origins for performance
    - Validate origin URLs
    """

    CACHE_KEY = "cors:origins"
    CACHE_TTL = 3600  # 1 hour (CORS doesn't change frequently)

    def get_active_origins(self, session: Session) -> List[str]:
        """
        Get list of active CORS origins.
        Returns ["*"] if database is empty (default behavior).

        Args:
            session: Database session

        Returns:
            List of active origin URLs or ["*"] if empty
        """
        # Try to get from cache first
        cached = cache_service.get(self.CACHE_KEY)
        if cached:
            return cached

        # Get from database
        statement = select(CorsOrigin).where(CorsOrigin.is_active == True)
        origins = session.exec(statement).all()

        # If database is empty, return ["*"] (allow all)
        if not origins:
            result = ["*"]
        else:
            result = [origin.origin for origin in origins]

        # Cache the result
        cache_service.set(self.CACHE_KEY, result, ttl=self.CACHE_TTL)

        return result

    def get_all(self, session: Session, include_inactive: bool = False) -> List[CorsOrigin]:
        """
        Get all CORS origins (for admin panel).

        Args:
            session: Database session
            include_inactive: Whether to include inactive origins

        Returns:
            List of CorsOrigin objects
        """
        statement = select(CorsOrigin)
        if not include_inactive:
            statement = statement.where(CorsOrigin.is_active == True)

        return list(session.exec(statement.order_by(CorsOrigin.created_at.desc())).all())

    def get_by_id(self, session: Session, origin_id: int) -> Optional[CorsOrigin]:
        """Get CORS origin by ID"""
        return session.get(CorsOrigin, origin_id)

    def create(self, session: Session, data: CorsOriginCreate, created_by: Optional[str] = None) -> CorsOrigin:
        """
        Create a new CORS origin.

        Args:
            session: Database session
            data: CORS origin data
            created_by: Username of creator (optional)

        Returns:
            Created CorsOrigin object

        Raises:
            ValueError: If origin URL is invalid
        """
        # Validate origin format
        self._validate_origin(data.origin)

        # Create origin
        origin = CorsOrigin(
            **data.model_dump(),
            created_by=created_by
        )
        session.add(origin)
        session.commit()
        session.refresh(origin)

        # Invalidate cache
        cache_service.delete(self.CACHE_KEY)

        return origin

    def update(self, session: Session, origin_id: int, data: CorsOriginUpdate) -> Optional[CorsOrigin]:
        """
        Update an existing CORS origin.

        Args:
            session: Database session
            origin_id: ID of origin to update
            data: Updated data

        Returns:
            Updated CorsOrigin object or None if not found

        Raises:
            ValueError: If origin URL is invalid
        """
        origin = session.get(CorsOrigin, origin_id)
        if not origin:
            return None

        # Validate new origin if provided
        if data.origin:
            self._validate_origin(data.origin)

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(origin, key, value)

        origin.updated_at = datetime.utcnow()
        session.add(origin)
        session.commit()
        session.refresh(origin)

        # Invalidate cache
        cache_service.delete(self.CACHE_KEY)

        return origin

    def delete(self, session: Session, origin_id: int) -> bool:
        """
        Delete a CORS origin.

        Args:
            session: Database session
            origin_id: ID of origin to delete

        Returns:
            True if deleted, False if not found
        """
        origin = session.get(CorsOrigin, origin_id)
        if not origin:
            return False

        session.delete(origin)
        session.commit()

        # Invalidate cache
        cache_service.delete(self.CACHE_KEY)

        return True

    def _validate_origin(self, origin: str) -> None:
        """
        Validate origin URL format.

        Args:
            origin: Origin URL to validate

        Raises:
            ValueError: If origin is invalid
        """
        # Allow wildcard
        if origin == "*":
            return

        # Validate URL format
        url_pattern = r'^https?://[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*?(:[0-9]{1,5})?$'

        if not re.match(url_pattern, origin):
            raise ValueError(
                f"Invalid origin URL: {origin}. "
                "Must be in format: http://example.com or https://example.com:3000"
            )

        # Prevent dangerous wildcards
        if '*' in origin and origin != '*':
            raise ValueError(
                f"Invalid origin: {origin}. "
                "Wildcards are not allowed in URLs. Use '*' alone or specific URLs."
            )

    def invalidate_cache(self) -> None:
        """Manually invalidate CORS origins cache"""
        cache_service.delete(self.CACHE_KEY)


# Singleton instance
cors_service = CorsService()
