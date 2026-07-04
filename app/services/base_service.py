import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar, Optional, Type, List
from sqlmodel import Session, SQLModel, select, func
from sqlalchemy import or_
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
    Servicio base genérico con WebSocket broadcasting, Redis caching,
    filtrado avanzado y **soft delete** automático.

    Soft delete:
    - Si el modelo incluye `SoftDeleteMixin`, `delete()` marca `deleted_at`
      en vez de borrar la fila. Todas las queries filtran registros eliminados.
    - `purge()` realiza hard delete. `restore()` recupera un registro.
    - `get_deleted()` lista registros eliminados (para admin).
    """

    def __init__(
        self,
        model: Type[ModelType],
        channel: ChannelManager,
        read_schema: Type[ReadSchemaType],
        cache_prefix: Optional[str] = None
    ):
        self.model = model
        self.channel = channel
        self.read_schema = read_schema

        # Detectar si el modelo soporta soft delete
        self._has_soft_delete = hasattr(model, "deleted_at")

        # Cache prefix
        if cache_prefix:
            self.cache_prefix = cache_prefix
        elif hasattr(model, '__tablename__'):
            self.cache_prefix = model.__tablename__
        else:
            self.cache_prefix = model.__name__.lower()

    # ------------------------------------------------------------------ #
    # Filtros internos
    # ------------------------------------------------------------------ #

    def _apply_soft_delete_filter(self, query):
        """Excluye registros soft-deleted si el modelo lo soporta."""
        if self._has_soft_delete:
            query = query.where(self.model.deleted_at.is_(None))
        return query

    def _apply_tenant_filter(self, query, *, organization_id=None, include_shared=False):
        """
        Aplica filtrado por tenant si el modelo tiene organization_id.
        Si include_shared=True, incluye también registros de la org sistema.
        """
        if not organization_id or not hasattr(self.model, "organization_id"):
            return query

        if include_shared:
            from app.services.organization_service import organization_service
            from sqlmodel import Session
            from app.database import engine
            with Session(engine) as temp_session:
                system_org = organization_service.get_system_organization(temp_session)
            if system_org:
                query = query.where(or_(
                    self.model.organization_id == organization_id,
                    self.model.organization_id == system_org.id,
                ))
            else:
                query = query.where(self.model.organization_id == organization_id)
        else:
            query = query.where(self.model.organization_id == organization_id)
        return query

    # ------------------------------------------------------------------ #
    # Lectura
    # ------------------------------------------------------------------ #

    def get_by_id(self, session: Session, obj_id: int) -> Optional[ModelType]:
        """Get an object by ID (with caching). Excluye soft-deleted."""
        cached = cache_service.get(self.cache_prefix, id=obj_id)
        if cached:
            return self.read_schema(**cached)

        obj = session.get(self.model, obj_id)

        # Excluir soft-deleted
        if obj and self._has_soft_delete and obj.deleted_at is not None:
            return None

        if obj:
            obj_dict = self.read_schema.model_validate(obj).model_dump()
            cache_service.set(self.cache_prefix, obj_dict, id=obj_id)

        return obj

    def get_all(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
        *,
        organization_id=None,
        include_shared: bool = False,
    ) -> List[ModelType]:
        """Get all objects with pagination. Excluye soft-deleted."""
        cache_key = f"{self.cache_prefix}:list"
        cached = cache_service.get(cache_key, skip=skip, limit=limit)
        if cached and not organization_id:
            return [self.read_schema(**item) for item in cached]

        statement = select(self.model)
        statement = self._apply_soft_delete_filter(statement)
        statement = self._apply_tenant_filter(
            statement, organization_id=organization_id, include_shared=include_shared
        )
        statement = statement.offset(skip).limit(limit)
        results = list(session.exec(statement).all())

        if results and not organization_id:
            results_dict = [self.read_schema.model_validate(obj).model_dump() for obj in results]
            cache_service.set(cache_key, results_dict, skip=skip, limit=limit)

        return results

    def get_all_paginated(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
        *,
        organization_id=None,
        include_shared: bool = False,
    ) -> dict:
        """Get all objects with pagination metadata. Excluye soft-deleted."""
        cache_key = f"{self.cache_prefix}:list:paginated"
        cached = cache_service.get(cache_key, skip=skip, limit=limit)
        if cached and not organization_id:
            return cached

        # Count (sin soft-deleted)
        count_statement = select(func.count()).select_from(self.model)
        count_statement = self._apply_soft_delete_filter(count_statement)
        count_statement = self._apply_tenant_filter(
            count_statement, organization_id=organization_id, include_shared=include_shared
        )
        total = session.exec(count_statement).one()

        # Data
        statement = select(self.model)
        statement = self._apply_soft_delete_filter(statement)
        statement = self._apply_tenant_filter(
            statement, organization_id=organization_id, include_shared=include_shared
        )
        statement = statement.offset(skip).limit(limit)
        results = list(session.exec(statement).all())

        results_dict = [self.read_schema.model_validate(obj).model_dump() for obj in results]

        response = {
            "data": results_dict,
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": (skip + len(results)) < total
        }

        if not organization_id:
            cache_service.set(cache_key, response, skip=skip, limit=limit)

        return response

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #

    def _get_resource_type(self) -> str:
        """Nombre del recurso para audit log (usa __tablename__)."""
        if hasattr(self.model, '__tablename__'):
            return self.model.__tablename__
        return self.model.__name__.lower()

    def _audit(
        self,
        session: Session,
        *,
        action: str,
        resource_id=None,
        changes=None,
        user_id=None,
        organization_id=None,
        ip_address=None,
        user_agent=None,
    ):
        """Hook de auditoría — registra la acción si AUDIT_LOG_ENABLED."""
        try:
            from app.services.audit_service import audit_service
            audit_service.record(
                session,
                user_id=user_id,
                organization_id=organization_id,
                action=action,
                resource_type=self._get_resource_type(),
                resource_id=str(resource_id) if resource_id else None,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            pass  # Auditoría no debe romper la operación principal

    async def create(
        self,
        session: Session,
        data: CreateSchemaType,
        broadcast: bool = True,
        *,
        audit_user_id: Optional[int] = None,
        audit_ip: Optional[str] = None,
        audit_ua: Optional[str] = None,
    ) -> ModelType:
        """Create a new object and optionally broadcast to WebSocket."""
        obj = self.model(**data.model_dump())
        session.add(obj)
        session.commit()
        session.refresh(obj)

        cache_service.invalidate_all(self.cache_prefix)

        # Audit
        obj_id = getattr(obj, 'id', None)
        self._audit(
            session, action="create", resource_id=obj_id,
            changes=data.model_dump(),
            user_id=audit_user_id, ip_address=audit_ip, user_agent=audit_ua,
        )

        if broadcast:
            obj_dict = self.read_schema.model_validate(obj).model_dump()
            await self.channel.broadcast_created(obj_dict)

        return obj

    async def update(
        self,
        session: Session,
        obj_id: int,
        data: UpdateSchemaType,
        broadcast: bool = True,
        *,
        audit_user_id: Optional[int] = None,
        audit_ip: Optional[str] = None,
        audit_ua: Optional[str] = None,
    ) -> Optional[ModelType]:
        """Update an object and optionally broadcast to WebSocket."""
        obj = session.get(self.model, obj_id)
        if not obj:
            return None

        # No permitir actualizar registros soft-deleted
        if self._has_soft_delete and obj.deleted_at is not None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Calcular cambios para audit antes de aplicar
        from app.services.audit_service import AuditService
        changes = AuditService.compute_changes(obj, update_data)

        for key, value in update_data.items():
            setattr(obj, key, value)

        if hasattr(obj, 'updated_at'):
            obj.updated_at = datetime.now(timezone.utc)

        session.add(obj)
        session.commit()
        session.refresh(obj)

        cache_service.invalidate_all(self.cache_prefix)

        # Audit
        if changes:
            self._audit(
                session, action="update", resource_id=obj_id,
                changes=changes,
                user_id=audit_user_id, ip_address=audit_ip, user_agent=audit_ua,
            )

        if broadcast:
            obj_dict = self.read_schema.model_validate(obj).model_dump()
            await self.channel.broadcast_updated(obj_dict)

        return obj

    async def delete(
        self,
        session: Session,
        obj_id: int,
        broadcast: bool = True,
        *,
        audit_user_id: Optional[int] = None,
        audit_ip: Optional[str] = None,
        audit_ua: Optional[str] = None,
    ) -> bool:
        """
        Soft delete si el modelo lo soporta, hard delete si no.
        Broadcast opcional del evento de eliminación.
        """
        obj = session.get(self.model, obj_id)
        if not obj:
            return False

        if self._has_soft_delete:
            # Soft delete: marcar deleted_at
            obj.deleted_at = datetime.now(timezone.utc)
            session.add(obj)
            session.commit()
        else:
            # Hard delete
            session.delete(obj)
            session.commit()

        cache_service.invalidate_all(self.cache_prefix)

        # Audit
        self._audit(
            session, action="delete", resource_id=obj_id,
            user_id=audit_user_id, ip_address=audit_ip, user_agent=audit_ua,
        )

        if broadcast:
            await self.channel.broadcast_deleted(obj_id)

        return True

    # ------------------------------------------------------------------ #
    # Soft delete: restaurar, purgar, listar eliminados
    # ------------------------------------------------------------------ #

    def restore(self, session: Session, obj_id: int) -> Optional[ModelType]:
        """Restaurar un registro soft-deleted. Retorna None si no existe o no estaba eliminado."""
        if not self._has_soft_delete:
            return None

        obj = session.get(self.model, obj_id)
        if not obj or obj.deleted_at is None:
            return None

        obj.deleted_at = None
        if hasattr(obj, 'updated_at'):
            obj.updated_at = datetime.now(timezone.utc)
        session.add(obj)
        session.commit()
        session.refresh(obj)

        cache_service.invalidate_all(self.cache_prefix)
        return obj

    async def purge(self, session: Session, obj_id: int) -> bool:
        """Eliminación permanente (hard delete). Para admin/cleanup."""
        obj = session.get(self.model, obj_id)
        if not obj:
            return False

        session.delete(obj)
        session.commit()
        cache_service.invalidate_all(self.cache_prefix)
        return True

    def get_deleted(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        """Listar registros soft-deleted (para admin)."""
        if not self._has_soft_delete:
            return []

        statement = (
            select(self.model)
            .where(self.model.deleted_at.is_not(None))
            .offset(skip)
            .limit(limit)
        )
        return list(session.exec(statement).all())

    # ------------------------------------------------------------------ #
    # Count
    # ------------------------------------------------------------------ #

    def count(self, session: Session) -> int:
        """Count total de objetos activos (excluye soft-deleted)."""
        statement = select(func.count()).select_from(self.model)
        statement = self._apply_soft_delete_filter(statement)
        return session.exec(statement).one()
