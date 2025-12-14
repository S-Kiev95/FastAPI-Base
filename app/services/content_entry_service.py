from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select, func, or_
from sqlalchemy import and_

from app.models.content_type import ContentEntry, ContentEntryCreate, ContentEntryUpdate
from app.services.content_type_service import content_type_service


class ContentEntryService:
    """
    Service for managing dynamic content entries.

    Handles:
    - CRUD operations for content entries
    - Dynamic validation based on content type
    - Search and filtering in JSONB data
    """

    def get_all(
        self,
        session: Session,
        content_type_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContentEntry]:
        """Get all entries for a content type"""
        statement = select(ContentEntry).where(
            ContentEntry.content_type_id == content_type_id
        )

        if status:
            statement = statement.where(ContentEntry.status == status)

        statement = statement.order_by(ContentEntry.created_at.desc())
        statement = statement.offset(skip).limit(limit)

        return list(session.exec(statement).all())

    def get_by_id(
        self,
        session: Session,
        entry_id: int
    ) -> Optional[ContentEntry]:
        """Get entry by ID"""
        return session.get(ContentEntry, entry_id)

    def count(
        self,
        session: Session,
        content_type_id: int,
        status: Optional[str] = None
    ) -> int:
        """Count entries for a content type"""
        statement = select(func.count(ContentEntry.id)).where(
            ContentEntry.content_type_id == content_type_id
        )

        if status:
            statement = statement.where(ContentEntry.status == status)

        return session.exec(statement).one()

    def create(
        self,
        session: Session,
        data: ContentEntryCreate,
        created_by: Optional[int] = None,
        validate: bool = True
    ) -> ContentEntry:
        """Create a new content entry"""
        # Validate data against content type schema
        if validate:
            validated_data = content_type_service.validate_entry_data(
                session,
                data.content_type_id,
                data.data
            )
        else:
            validated_data = data.data

        # Create entry
        entry = ContentEntry(
            content_type_id=data.content_type_id,
            data=validated_data,
            status=data.status,
            created_by=created_by
        )

        session.add(entry)
        session.commit()
        session.refresh(entry)

        return entry

    def update(
        self,
        session: Session,
        entry_id: int,
        data: ContentEntryUpdate,
        updated_by: Optional[int] = None,
        validate: bool = True
    ) -> Optional[ContentEntry]:
        """Update content entry"""
        entry = self.get_by_id(session, entry_id)
        if not entry:
            return None

        # Update data
        if data.data is not None:
            # Merge with existing data
            updated_data = {**entry.data, **data.data}

            # Validate if requested
            if validate:
                updated_data = content_type_service.validate_entry_data(
                    session,
                    entry.content_type_id,
                    updated_data
                )

            entry.data = updated_data

        # Update status
        if data.status is not None:
            entry.status = data.status

            # Set published_at if publishing
            if data.status == "published" and not entry.published_at:
                entry.published_at = datetime.utcnow()

        entry.updated_by = updated_by
        entry.updated_at = datetime.utcnow()

        session.add(entry)
        session.commit()
        session.refresh(entry)

        return entry

    def delete(self, session: Session, entry_id: int) -> bool:
        """Delete content entry"""
        entry = self.get_by_id(session, entry_id)
        if not entry:
            return False

        session.delete(entry)
        session.commit()

        return True

    def search(
        self,
        session: Session,
        content_type_id: int,
        query: str,
        searchable_fields: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContentEntry]:
        """
        Search entries by query string in JSONB fields.

        For SQLite: Uses json_extract
        For PostgreSQL: Can use JSONB operators
        """
        # Get fields to search in
        if not searchable_fields:
            # Get all searchable fields from content type
            fields = content_type_service.get_fields(session, content_type_id)
            searchable_fields = [f.name for f in fields if f.is_searchable]

        if not searchable_fields:
            return []

        # Build search conditions
        # This is a basic implementation for SQLite
        # For PostgreSQL, you'd use more sophisticated JSONB queries
        search_conditions = []

        for field_name in searchable_fields:
            # SQLite JSON search
            search_conditions.append(
                func.json_extract(ContentEntry.data, f'$.{field_name}').like(f'%{query}%')
            )

        # Combine with OR
        statement = select(ContentEntry).where(
            and_(
                ContentEntry.content_type_id == content_type_id,
                or_(*search_conditions)
            )
        ).order_by(ContentEntry.created_at.desc()).offset(skip).limit(limit)

        return list(session.exec(statement).all())

    def filter_by_field(
        self,
        session: Session,
        content_type_id: int,
        field_name: str,
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContentEntry]:
        """Filter entries by a specific field value"""
        # SQLite JSON filtering
        statement = select(ContentEntry).where(
            and_(
                ContentEntry.content_type_id == content_type_id,
                func.json_extract(ContentEntry.data, f'$.{field_name}') == value
            )
        ).order_by(ContentEntry.created_at.desc()).offset(skip).limit(limit)

        return list(session.exec(statement).all())

    def get_paginated(
        self,
        session: Session,
        content_type_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get entries with pagination metadata"""
        # Get total count
        total = self.count(session, content_type_id, status=status)

        # Get entries
        entries = self.get_all(
            session,
            content_type_id,
            status=status,
            skip=skip,
            limit=limit
        )

        return {
            "data": entries,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + len(entries)) < total
        }

    def publish(
        self,
        session: Session,
        entry_id: int,
        updated_by: Optional[int] = None
    ) -> Optional[ContentEntry]:
        """Publish an entry"""
        return self.update(
            session,
            entry_id,
            ContentEntryUpdate(status="published"),
            updated_by=updated_by,
            validate=False
        )

    def unpublish(
        self,
        session: Session,
        entry_id: int,
        updated_by: Optional[int] = None
    ) -> Optional[ContentEntry]:
        """Unpublish an entry (set to draft)"""
        return self.update(
            session,
            entry_id,
            ContentEntryUpdate(status="draft"),
            updated_by=updated_by,
            validate=False
        )

    def archive(
        self,
        session: Session,
        entry_id: int,
        updated_by: Optional[int] = None
    ) -> Optional[ContentEntry]:
        """Archive an entry"""
        return self.update(
            session,
            entry_id,
            ContentEntryUpdate(status="archived"),
            updated_by=updated_by,
            validate=False
        )


# Singleton instance
content_entry_service = ContentEntryService()
