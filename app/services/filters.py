"""
Sistema genérico de filtros avanzados para BaseService.

Proporciona capacidades de filtrado, ordenamiento y paginación
para cualquier modelo que herede de BaseService.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Union
from sqlmodel import select
from app.services.cache_service import cache_service
import hashlib
import json
from sqlalchemy import and_, or_, desc, asc
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LogicalOperator(str, Enum):
    """Operadores lógicos para combinar condiciones"""
    AND = "and"
    OR = "or"


class FilterOperator(str, Enum):
    """Operadores de comparación soportados"""
    EQ = "eq"              # Igual
    NE = "ne"              # No igual
    GT = "gt"              # Mayor que
    GTE = "gte"            # Mayor o igual que
    LT = "lt"              # Menor que
    LTE = "lte"            # Menor o igual que
    CONTAINS = "contains"   # Contiene (case sensitive)
    ICONTAINS = "icontains" # Contiene (case insensitive)
    STARTSWITH = "startswith" # Comienza con
    ENDSWITH = "endswith"   # Termina con
    IN = "in"              # En lista
    NOT_IN = "not_in"      # No en lista
    IS_NULL = "is_null"    # Es nulo
    IS_NOT_NULL = "is_not_null" # No es nulo


class Condition(BaseModel):
    """Una condición de filtro individual"""
    field: str = Field(..., description="Campo a filtrar")
    operator: FilterOperator = Field(..., description="Operador de comparación")
    value: Any = Field(default=None, description="Valor a comparar")

    @field_validator('field')
    @classmethod
    def validate_field(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El campo no puede estar vacío")
        return v.strip()


class ConditionGroup(BaseModel):
    """Grupo de condiciones con operador lógico"""
    conditions: List[Union[Condition, "ConditionGroup"]] = Field(default_factory=list)
    operator: LogicalOperator = Field(default=LogicalOperator.AND)


class QueryFilter(BaseModel):
    """
    Filtro completo para queries con condiciones, ordenamiento y paginación.

    Ejemplo:
        filter = QueryFilter(
            conditions=[
                Condition(field="email", operator=FilterOperator.CONTAINS, value="@gmail"),
                Condition(field="is_active", operator=FilterOperator.EQ, value=True)
            ],
            order_by="created_at",
            order_direction="desc",
            limit=10,
            offset=0
        )
    """
    conditions: Optional[List[Union[Condition, ConditionGroup]]] = None
    operator: LogicalOperator = Field(default=LogicalOperator.AND)
    order_by: Optional[str] = None
    order_direction: Optional[str] = Field(default="asc", pattern="^(asc|desc)$")
    limit: Optional[int] = Field(default=100, ge=1, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)

    class Config:
        use_enum_values = True


# Fix forward references para soporte de grupos anidados
ConditionGroup.model_rebuild()


class QueryBuilder:
    """
    Constructor de queries SQL con soporte para filtros complejos.

    Usage:
        builder = QueryBuilder(User)
        builder.apply_filters(query_filter)
        query = builder.build()
        results = session.exec(query).all()
    """

    def __init__(self, model_class):
        self.model_class = model_class
        self.query = select(model_class)

    def apply_filters(self, filters: QueryFilter):
        """Aplica todos los filtros, ordenamiento y paginación"""
        if filters.conditions:
            self._apply_conditions(filters.conditions, filters.operator)

        if filters.order_by:
            self._apply_ordering(filters.order_by, filters.order_direction)

        if filters.limit is not None:
            self.query = self.query.limit(filters.limit)

        if filters.offset is not None:
            self.query = self.query.offset(filters.offset)

        return self

    def _apply_conditions(
        self,
        conditions: List[Union[Condition, ConditionGroup]],
        operator: LogicalOperator
    ):
        """Aplica condiciones con soporte para grupos"""
        if not conditions:
            return

        clauses = []
        for condition in conditions:
            if isinstance(condition, Condition):
                clause = self._build_condition_clause(condition)
                if clause is not None:
                    clauses.append(clause)
            elif isinstance(condition, ConditionGroup):
                group_clause = self._apply_condition_group(condition)
                if group_clause is not None:
                    clauses.append(group_clause)

        if clauses:
            combined = or_(*clauses) if operator == LogicalOperator.OR else and_(*clauses)
            self.query = self.query.where(combined)

    def _apply_condition_group(self, group: ConditionGroup):
        """Aplica un grupo de condiciones recursivamente"""
        if not group.conditions:
            return None

        clauses = []
        for condition in group.conditions:
            if isinstance(condition, Condition):
                clause = self._build_condition_clause(condition)
                if clause is not None:
                    clauses.append(clause)
            elif isinstance(condition, ConditionGroup):
                nested_clause = self._apply_condition_group(condition)
                if nested_clause is not None:
                    clauses.append(nested_clause)

        if not clauses:
            return None

        return or_(*clauses) if group.operator == LogicalOperator.OR else and_(*clauses)

    def _build_condition_clause(self, condition: Condition):
        """Construye una cláusula SQL para una condición"""
        try:
            # Verificar que el campo existe en el modelo
            if not hasattr(self.model_class, condition.field):
                logger.warning(f"Campo '{condition.field}' no existe en {self.model_class.__name__}")
                return None

            column = getattr(self.model_class, condition.field)

            # Mapeo de operadores a métodos SQL
            operators = {
                FilterOperator.EQ: lambda col, val: col == val,
                FilterOperator.NE: lambda col, val: col != val,
                FilterOperator.GT: lambda col, val: col > val,
                FilterOperator.GTE: lambda col, val: col >= val,
                FilterOperator.LT: lambda col, val: col < val,
                FilterOperator.LTE: lambda col, val: col <= val,
                FilterOperator.CONTAINS: lambda col, val: col.contains(str(val)),
                FilterOperator.ICONTAINS: lambda col, val: col.ilike(f'%{val}%'),
                FilterOperator.STARTSWITH: lambda col, val: col.startswith(str(val)),
                FilterOperator.ENDSWITH: lambda col, val: col.endswith(str(val)),
                FilterOperator.IN: lambda col, val: col.in_(val if isinstance(val, list) else [val]),
                FilterOperator.NOT_IN: lambda col, val: ~col.in_(val if isinstance(val, list) else [val]),
                FilterOperator.IS_NULL: lambda col, val: col.is_(None),
                FilterOperator.IS_NOT_NULL: lambda col, val: col.is_not(None),
            }

            return operators[condition.operator](column, condition.value)

        except Exception as e:
            logger.error(f"Error construyendo condición para '{condition.field}': {e}")
            return None

    def _apply_ordering(self, order_by: str, direction: str):
        """Aplica ordenamiento"""
        try:
            if not hasattr(self.model_class, order_by):
                logger.warning(f"Campo de ordenamiento '{order_by}' no existe")
                return

            column = getattr(self.model_class, order_by)

            if direction.lower() == "desc":
                self.query = self.query.order_by(desc(column))
            else:
                self.query = self.query.order_by(asc(column))

        except Exception as e:
            logger.error(f"Error aplicando ordenamiento: {e}")

    def build(self):
        """Retorna la query construida"""
        return self.query


class FilterMixin:
    """
    Mixin para agregar capacidades de filtrado a BaseService.

    Usage:
        class UserService(BaseService[...], FilterMixin):
            pass

        # Luego en tus rutas:
        results = user_service.filter(session, query_filter)
    """

    def filter(self, session, filters: QueryFilter):
        """
        Filtra registros basándose en QueryFilter.

        Args:
            session: Sesión de base de datos
            filters: Objeto QueryFilter con condiciones, ordenamiento y paginación

        Returns:
            Lista de objetos filtrados

        Example:
            filters = QueryFilter(
                conditions=[
                    Condition(field="email", operator=FilterOperator.CONTAINS, value="gmail"),
                    Condition(field="is_active", operator=FilterOperator.EQ, value=True)
                ],
                order_by="created_at",
                order_direction="desc",
                limit=10
            )
            users = user_service.filter(session, filters)
        """
        try:
            # Generate cache key from filter parameters
            cache_prefix = f"{self.cache_prefix}:filter"
            filters_dict = filters.model_dump()
            filters_json = json.dumps(filters_dict, sort_keys=True, default=str)
            filters_hash = hashlib.md5(filters_json.encode()).hexdigest()[:8]

            # Try to get from cache
            cached = cache_service.get(cache_prefix, hash=filters_hash)
            if cached:
                logger.info(f"Filtrado desde cache: {len(cached)} registros")
                return cached

            # Not in cache, execute query
            builder = QueryBuilder(self.model)
            builder.apply_filters(filters)
            query = builder.build()

            results = session.exec(query).all()
            logger.info(f"Filtrado completado: {len(results)} registros encontrados")

            # Store in cache (convert to list of dicts for JSON serialization)
            if results:
                results_list = [dict(obj.__dict__) for obj in results]
                # Remove SQLAlchemy internal state
                for item in results_list:
                    item.pop('_sa_instance_state', None)
                cache_service.set(cache_prefix, results_list, hash=filters_hash)

            return list(results)

        except Exception as e:
            logger.error(f"Error ejecutando filtro: {e}")
            raise

    def count_filtered(self, session, filters: QueryFilter) -> int:
        """
        Cuenta registros que coinciden con los filtros (sin paginación).

        Args:
            session: Sesión de base de datos
            filters: Objeto QueryFilter (solo usa conditions, ignora limit/offset)

        Returns:
            Número de registros que coinciden
        """
        try:
            # Crear filtro sin paginación
            count_filters = QueryFilter(
                conditions=filters.conditions,
                operator=filters.operator,
                order_by=None,  # No necesitamos ordenamiento para contar
                limit=None,
                offset=None
            )

            builder = QueryBuilder(self.model)

            # Solo aplicar condiciones
            if count_filters.conditions:
                builder._apply_conditions(count_filters.conditions, count_filters.operator)

            query = builder.build()
            results = session.exec(query).all()

            return len(results)

        except Exception as e:
            logger.error(f"Error contando registros filtrados: {e}")
            return 0

    def filter_paginated(self, session, filters: QueryFilter) -> dict:
        """
        Filtra registros y retorna resultado paginado con metadata.

        Args:
            session: Sesión de base de datos
            filters: Objeto QueryFilter

        Returns:
            Dict con 'data', 'total', 'limit', 'offset'

        Example:
            result = user_service.filter_paginated(session, filters)
            # {
            #     "data": [...],
            #     "total": 150,
            #     "limit": 10,
            #     "offset": 0,
            #     "has_more": True
            # }
        """
        # Generate cache key for paginated result
        cache_prefix = f"{self.cache_prefix}:filter:paginated"
        filters_dict = filters.model_dump()
        filters_json = json.dumps(filters_dict, sort_keys=True, default=str)
        filters_hash = hashlib.md5(filters_json.encode()).hexdigest()[:8]

        # Try to get from cache
        cached = cache_service.get(cache_prefix, hash=filters_hash)
        if cached:
            logger.info(f"Resultado paginado desde cache")
            return cached

        # Not in cache, execute queries
        total = self.count_filtered(session, filters)
        data = self.filter(session, filters)

        result = {
            "data": data,
            "total": total,
            "limit": filters.limit,
            "offset": filters.offset,
            "has_more": (filters.offset + len(data)) < total
        }

        # Store in cache
        cache_service.set(cache_prefix, result, hash=filters_hash)

        return result
