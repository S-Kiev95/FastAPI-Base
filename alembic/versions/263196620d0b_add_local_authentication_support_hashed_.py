"""Add local authentication support - hashed_password field

Revision ID: 263196620d0b
Revises: ba722cc53bb5
Create Date: 2025-12-06 19:57:41.313824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '263196620d0b'
down_revision: Union[str, Sequence[str], None] = 'ba722cc53bb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if we're using PostgreSQL or SQLite
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # PostgreSQL doesn't need batch mode
        op.add_column('users', sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        op.alter_column('users', 'provider',
                   existing_type=sa.VARCHAR(),
                   nullable=True)
        op.alter_column('users', 'provider_user_id',
                   existing_type=sa.VARCHAR(),
                   nullable=True)
        op.drop_index('ix_users_provider_user_id', table_name='users')
        op.create_index('ix_users_provider_user_id', 'users', ['provider_user_id'], unique=False)
    else:
        # SQLite doesn't support ALTER COLUMN, use batch mode
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
            batch_op.alter_column('provider',
                       existing_type=sa.VARCHAR(),
                       nullable=True)
            batch_op.alter_column('provider_user_id',
                       existing_type=sa.VARCHAR(),
                       nullable=True)
            batch_op.drop_index('ix_users_provider_user_id')
            batch_op.create_index('ix_users_provider_user_id', ['provider_user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Check if we're using PostgreSQL or SQLite
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # PostgreSQL doesn't need batch mode
        op.drop_index('ix_users_provider_user_id', table_name='users')
        op.create_index('ix_users_provider_user_id', 'users', ['provider_user_id'], unique=True)
        op.alter_column('users', 'provider_user_id',
                   existing_type=sa.VARCHAR(),
                   nullable=False)
        op.alter_column('users', 'provider',
                   existing_type=sa.VARCHAR(),
                   nullable=False)
        op.drop_column('users', 'hashed_password')
    else:
        # SQLite doesn't support ALTER COLUMN, use batch mode
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_index('ix_users_provider_user_id')
            batch_op.create_index('ix_users_provider_user_id', ['provider_user_id'], unique=True)
            batch_op.alter_column('provider_user_id',
                       existing_type=sa.VARCHAR(),
                       nullable=False)
            batch_op.alter_column('provider',
                       existing_type=sa.VARCHAR(),
                       nullable=False)
            batch_op.drop_column('hashed_password')
