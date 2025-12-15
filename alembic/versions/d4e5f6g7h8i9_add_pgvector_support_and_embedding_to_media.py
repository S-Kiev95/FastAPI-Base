"""add pgvector support and embedding to media

Revision ID: d4e5f6g7h8i9
Revises: 263196620d0b
Create Date: 2025-12-14 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Conditional import for pgvector
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None

# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = '263196620d0b'
branch_labels = None
depends_on = None


def upgrade():
    """
    Enable pgvector extension and add embedding column to media table.

    The embedding column will be:
    - Vector(512) if PostgreSQL with pgvector extension
    - Text if SQLite or PostgreSQL without pgvector

    Developers can use this for various embedding types:
    - Text embeddings (OpenAI, Cohere, etc.)
    - Image embeddings (CLIP, ResNet, etc.)
    - Face embeddings (DeepFace, FaceNet, etc.)
    - Audio embeddings (Resemblyzer, VGGish, etc.)
    """

    # Check if we're using PostgreSQL
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # Enable pgvector extension
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')

        # Add embedding column as vector type
        if PGVECTOR_AVAILABLE:
            op.add_column('media', sa.Column('embedding', Vector(512), nullable=True))

            # Create HNSW index for fast similarity search (optional but recommended)
            # HNSW (Hierarchical Navigable Small World) is great for high-dimensional vectors
            op.execute("""
                CREATE INDEX IF NOT EXISTS idx_media_embedding_hnsw
                ON media USING hnsw (embedding vector_l2_ops)
                WITH (m = 16, ef_construction = 64)
            """)
        else:
            # Fallback to text if pgvector not available
            op.add_column('media', sa.Column('embedding', sa.Text(), nullable=True))
    else:
        # For SQLite or other databases, use Text
        op.add_column('media', sa.Column('embedding', sa.Text(), nullable=True))


def downgrade():
    """Remove embedding column and pgvector extension"""

    connection = op.get_bind()

    # Drop index if exists
    if connection.dialect.name == 'postgresql':
        op.execute('DROP INDEX IF EXISTS idx_media_embedding_hnsw')

    # Drop column
    op.drop_column('media', 'embedding')

    # Note: We don't drop the pgvector extension as other tables might use it
    # If you want to drop it, uncomment the line below
    # op.execute('DROP EXTENSION IF EXISTS vector')
