"""
Mixins reutilizables para modelos SQLModel.
"""
from datetime import datetime
from typing import Optional
from sqlmodel import Field


class SoftDeleteMixin:
    """
    Mixin que agrega soft delete a cualquier modelo.

    Agrega el campo `deleted_at` — cuando no es None, el registro
    se considera eliminado y se filtra automáticamente en BaseService.

    Uso:
        class MyModel(SoftDeleteMixin, SQLModel, table=True):
            ...
    """
    deleted_at: Optional[datetime] = Field(default=None, index=True)
