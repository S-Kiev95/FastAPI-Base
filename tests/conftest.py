"""
Fixtures compartidos para todos los tests.
Usa SQLite en memoria — no requiere PostgreSQL ni Redis.
"""
import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.connection import get_session
from main import app


@pytest.fixture(name="engine")
def engine_fixture():
    """Engine SQLite en memoria, aislado por test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Importar todos los modelos para que se registren en metadata
    from app.models.user import User  # noqa: F401
    from app.models.media import Media  # noqa: F401
    from app.models.role import Role, Permission, UserRole, RolePermission  # noqa: F401
    from app.models.cors_origin import CorsOrigin  # noqa: F401
    from app.models.metric import ApiMetric  # noqa: F401
    from app.models.task import Task  # noqa: F401
    from app.models.organization import Organization, Membership  # noqa: F401
    from app.models.refresh_token import RefreshToken  # noqa: F401
    from app.models.invitation import Invitation  # noqa: F401
    from app.models.subscription import Subscription  # noqa: F401
    from app.models.payment import Payment  # noqa: F401
    from app.models.audit_log import AuditLog  # noqa: F401
    from app.models.api_key import ApiKey  # noqa: F401
    # webhook.py usa SQLAlchemy Base (no SQLModel) — se excluye de tests por ahora

    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    """Sesión de BD aislada por test con rollback automático."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine):
    """TestClient de FastAPI con BD en memoria."""

    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="registered_user")
def registered_user_fixture(client):
    """Crea un usuario registrado y devuelve sus datos + tokens."""
    user_data = {
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User",
    }
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    # Login para obtener tokens
    login_response = client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    token = login_data["access_token"]

    return {
        "user": response.json(),
        "token": token,
        "refresh_token": login_data.get("refresh_token"),
        "password": user_data["password"],
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(registered_user):
    """Shortcut: solo los headers de autenticación."""
    return registered_user["headers"]


@pytest.fixture(name="sample_users")
def sample_users_fixture(client):
    """Crea varios usuarios para tests de filtros."""
    users_data = [
        {
            "provider": "google",
            "provider_user_id": "filter_test_1",
            "email": "alice@gmail.com",
            "name": "Alice Gmail",
        },
        {
            "provider": "google",
            "provider_user_id": "filter_test_2",
            "email": "bob@yahoo.com",
            "name": "Bob Yahoo",
        },
        {
            "provider": "github",
            "provider_user_id": "filter_test_3",
            "email": "charlie@gmail.com",
            "name": "Charlie Gmail",
        },
        {
            "provider": "google",
            "provider_user_id": "filter_test_4",
            "email": "david@hotmail.com",
            "name": "David Hotmail",
        },
    ]
    created = []
    for data in users_data:
        response = client.post("/users/", json=data)
        assert response.status_code == 201
        created.append(response.json())
    return created


# ---- Fixtures de multi-tenancy ----

@pytest.fixture(name="registered_user_with_org")
def registered_user_with_org_fixture(client):
    """Registra un usuario (register crea user + org + membership owner)."""
    user_data = {
        "email": "orgowner@example.com",
        "password": "password123",
        "name": "Org Owner",
        "organization_name": "Mi Correduría",
    }
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()

    return {
        "user": response.json(),
        "token": login_data["access_token"],
        "refresh_token": login_data.get("refresh_token"),
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
        "org_slug": "mi-correduria",
    }


@pytest.fixture(name="second_user_with_org")
def second_user_with_org_fixture(client):
    """Segundo usuario con su propia org (para tests de aislamiento)."""
    user_data = {
        "email": "second@example.com",
        "password": "password123",
        "name": "Second User",
        "organization_name": "Otra Correduría",
    }
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()

    return {
        "user": response.json(),
        "token": login_data["access_token"],
        "refresh_token": login_data.get("refresh_token"),
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
        "org_slug": "otra-correduria",
    }


@pytest.fixture(name="system_org")
def system_org_fixture(session):
    """Crea la organización sistema para tests."""
    from app.models.organization import Organization

    org = Organization(
        name="Sistema",
        slug="system",
        plan="system",
        is_system=True,
        is_active=True,
    )
    session.add(org)
    session.commit()
    session.refresh(org)
    return org
