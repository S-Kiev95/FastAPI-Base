from datetime import datetime
from typing import Generic, TypeVar, Optional, Type, List
from sqlmodel import Session, SQLModel, select, func
from app.services.websocket.channels import ChannelManager
from app.services.filters import FilterMixin
from app.services.cache_service import cache_service

# Type variables for generic service
ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)
ReadSchemaType = TypeVar("ReadSchemaType", bound=SQLModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ReadSchemaType], FilterMixin):
    """
    Generic base service with automatic WebSocket broadcasting, Redis caching, and advanced filtering.

    All CRUD services should inherit from this class to get:
    - Automatic WebSocket notifications on create/update/delete
    - Optional Redis caching for read operations (if REDIS_ENABLED=True)
    - Automatic cache invalidation on write operations
    - Advanced filtering, sorting and pagination via FilterMixin
    - Type-safe operations with generics
    - Consistent interface across all models

    Usage:
        class UserService(BaseService[User, UserCreate, UserUpdate, UserRead]):
            def __init__(self):
                super().__init__(
                    model=User,
                    channel=users_channel,
                    read_schema=UserRead,
                    cache_prefix="users"  # Optional: for Redis caching
                )

        # Using filters:
        from app.services.filters import QueryFilter, Condition, FilterOperator

        filters = QueryFilter(
            conditions=[
                Condition(field="email", operator=FilterOperator.CONTAINS, value="gmail")
            ],
            order_by="created_at",
            limit=10
        )
        results = user_service.filter(session, filters)

    Cache Behavior:
    - GET operations check cache first, fall back to DB if not found
    - POST/PUT/DELETE operations automatically invalidate related caches
    - Cache is completely optional - disabled if Redis not configured
    - No code changes needed - caching is transparent
    """

    def __init__(
        self,
        model: Type[ModelType],
        channel: ChannelManager,
        read_schema: Type[ReadSchemaType],
        cache_prefix: Optional[str] = None
    ):
        """
        Initialize the base service.

        Args:
            model: SQLModel class for the database table
            channel: ChannelManager instance for WebSocket broadcasts
            read_schema: Schema for reading/serializing objects
            cache_prefix: Prefix for cache keys (e.g., "users", "posts")
                         If not provided, uses model.__tablename__ or model.__name__
        """
        self.model = model
        self.channel = channel
        self.read_schema = read_schema

        # Cache prefix (e.g., "users", "posts")
        if cache_prefix:
            self.cache_prefix = cache_prefix
        elif hasattr(model, '__tablename__'):
            self.cache_prefix = model.__tablename__
        else:
            self.cache_prefix = model.__name__.lower()

    def get_by_id(self, session: Session, obj_id: int) -> Optional[ModelType]:
        """
        Get an object by ID (with caching).

        Args:
            session: Database session
            obj_id: Object ID

        Returns:
            Object if found, None otherwise

        Cache: Checks cache first, stores result on cache miss
        """
        # Try to get from cache
        cached = cache_service.get(self.cache_prefix, id=obj_id)
        if cached:
            # Return from cache (convert dict back to model)
            return self.read_schema(**cached)

        # Not in cache, get from database
        obj = session.get(self.model, obj_id)

        # Store in cache if found
        if obj:
            obj_dict = self.read_schema.model_validate(obj).model_dump()
            cache_service.set(self.cache_prefix, obj_dict, id=obj_id)

        return obj

    def get_all(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Get all objects with pagination (with caching).

        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of objects

        Cache: Caches paginated results based on skip/limit
        """
        # Try to get from cache
        cache_key = f"{self.cache_prefix}:list"
        cached = cache_service.get(cache_key, skip=skip, limit=limit)
        if cached:
            # Return from cache (convert list of dicts to models)
            return [self.read_schema(**item) for item in cached]

        # Not in cache, get from database
        statement = select(self.model).offset(skip).limit(limit)
        results = list(session.exec(statement).all())

        # Store in cache
        if results:
            results_dict = [self.read_schema.model_validate(obj).model_dump() for obj in results]
            cache_service.set(cache_key, results_dict, skip=skip, limit=limit)

        return results

    def get_all_paginated(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> dict:
        """
        Get all objects with complete pagination metadata (with caching).

        Args:
            session: Database session
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            Dict with pagination metadata:
            {
                "data": [...],        # List of objects
                "total": 150,         # Total count of records
                "limit": 100,         # Requested limit
                "offset": 0,          # Requested offset
                "has_more": True      # Whether more records exist
            }

        Cache: Caches complete paginated result including metadata

        Example:
            result = user_service.get_all_paginated(session, skip=0, limit=10)
            print(f"Page 1 of {result['total'] // result['limit']}")
            for user in result['data']:
                print(user.email)
        """
        # Try to get from cache
        cache_key = f"{self.cache_prefix}:list:paginated"
        cached = cache_service.get(cache_key, skip=skip, limit=limit)
        if cached:
            return cached

        # Not in cache, get total count
        count_statement = select(func.count()).select_from(self.model)
        total = session.exec(count_statement).one()

        # Get paginated data
        statement = select(self.model).offset(skip).limit(limit)
        results = list(session.exec(statement).all())

        # Convert to dict for serialization
        results_dict = [self.read_schema.model_validate(obj).model_dump() for obj in results]

        # Build response
        response = {
            "data": results_dict,
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": (skip + len(results)) < total
        }

        # Store in cache
        cache_service.set(cache_key, response, skip=skip, limit=limit)

        return response

    async def create(
        self,
        session: Session,
        data: CreateSchemaType,
        broadcast: bool = True
    ) -> ModelType:
        """
        Create a new object and optionally broadcast to WebSocket clients.

        Args:
            session: Database session
            data: Data for creating the object
            broadcast: Whether to broadcast the creation event (default: True)

        Returns:
            The created object

        Cache: Invalidates all related caches (lists, filters, etc.)
        """
        obj = self.model(**data.model_dump())
        session.add(obj)
        session.commit()
        session.refresh(obj)

        # Invalidate all caches for this resource
        cache_service.invalidate_all(self.cache_prefix)

        if broadcast:
            obj_dict = self.read_schema.model_validate(obj).model_dump()
            await self.channel.broadcast_created(obj_dict)

        return obj

    async def update(
        self,
        session: Session,
        obj_id: int,
        data: UpdateSchemaType,
        broadcast: bool = True
    ) -> Optional[ModelType]:
        """
        Update an object and optionally broadcast to WebSocket clients.

        Args:
            session: Database session
            obj_id: ID of object to update
            data: Updated data
            broadcast: Whether to broadcast the update event (default: True)

        Returns:
            The updated object if found, None otherwise

        Cache: Invalidates all related caches (lists, filters, and specific object)
        """
        obj = session.get(self.model, obj_id)
        if not obj:
            return None

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(obj, key, value)

        # Update timestamp if exists
        if hasattr(obj, 'updated_at'):
            obj.updated_at = datetime.utcnow()

        session.add(obj)
        session.commit()
        session.refresh(obj)

        # Invalidate all caches for this resource
        cache_service.invalidate_all(self.cache_prefix)

        if broadcast:
            obj_dict = self.read_schema.model_validate(obj).model_dump()
            await self.channel.broadcast_updated(obj_dict)

        return obj

    async def delete(
        self,
        session: Session,
        obj_id: int,
        broadcast: bool = True
    ) -> bool:
        """
        Delete an object and optionally broadcast to WebSocket clients.

        Args:
            session: Database session
            obj_id: ID of object to delete
            broadcast: Whether to broadcast the deletion event (default: True)

        Returns:
            True if deleted, False if not found

        Cache: Invalidates all related caches
        """
        obj = session.get(self.model, obj_id)
        if not obj:
            return False

        session.delete(obj)
        session.commit()

        # Invalidate all caches for this resource
        cache_service.invalidate_all(self.cache_prefix)

        if broadcast:
            await self.channel.broadcast_deleted(obj_id)

        return True

    def count(self, session: Session) -> int:
        """
        Count total number of objects.

        Args:
            session: Database session

        Returns:
            Total count
        """
        statement = select(self.model)
        return len(list(session.exec(statement).all()))
