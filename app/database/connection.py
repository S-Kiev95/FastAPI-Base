import os
from sqlmodel import Session, SQLModel, create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Create engine
# For SQLite, add check_same_thread=False
# For production with PostgreSQL/MySQL, remove connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)


def init_db() -> None:
    """
    Initialize database by creating all tables.
    This function is called on app startup.
    """
    # Import all models here to ensure they are registered with SQLModel
    from app.models import User  # noqa: F401
    from app.models.media import Media  # noqa: F401
    from app.models.role import Role, Permission, UserRole, RolePermission  # noqa: F401
    from app.models.cors_origin import CorsOrigin  # noqa: F401
    from app.models.metric import ApiMetric  # noqa: F401

    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully")


def get_session():
    """
    Dependency function to get database session.
    Use this in FastAPI route dependencies.

    Usage:
        @app.get("/users")
        def get_users(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session
