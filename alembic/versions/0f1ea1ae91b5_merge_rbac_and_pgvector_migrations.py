"""merge rbac and pgvector migrations

Revision ID: 0f1ea1ae91b5
Revises: 081ee8141db3, d4e5f6g7h8i9
Create Date: 2025-12-15 00:53:53.751493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f1ea1ae91b5'
down_revision: Union[str, Sequence[str], None] = ('081ee8141db3', 'd4e5f6g7h8i9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
