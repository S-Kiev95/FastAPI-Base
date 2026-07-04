# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI modular monolith backend (Python 3.13+) with SQLModel ORM, JWT/OAuth auth, WebSockets, ARQ task queues, and S3/local file storage. Documentation and comments are in Spanish.

## Commands

```bash
# Install dependencies
uv sync

# Run dev server (hot reload on port 8000)
uv run python main.py

# Run via script
uv run start

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Docker (production: PostgreSQL + Redis + backend)
docker-compose up -d

# Docker (dev: adds pgAdmin:5050, Redis Commander:8081, ARQ workers)
docker-compose -f docker-compose.dev.yml up -d

# ARQ background workers
arq app.workers.worker_config.WorkerSettings

# Run tests (standalone scripts, no test runner)
python test_auth.py
python test_filters.py
python test_rate_limit.py
python test_websocket.py
```

## Architecture

### Layer Pattern: Routes → Services → Models

- **Routes** (`app/routes/`) — FastAPI endpoint definitions with dependency injection
- **Services** (`app/services/`) — Business logic, all inherit from `BaseService`
- **Models** (`app/models/`) — SQLModel table definitions (dual Pydantic + SQLAlchemy)

### BaseService Generic Pattern

Central abstraction at `app/services/base_service.py`. All domain services inherit from `BaseService[Model, Create, Update, Read]` which provides:
- Type-safe CRUD operations
- Automatic WebSocket broadcasting on writes
- Transparent Redis caching on reads (when `REDIS_ENABLED=True`)
- Advanced filtering/sorting/pagination via `FilterMixin`

To add a new model: create model in `app/models/`, create a service inheriting `BaseService`, create routes using the service, register the router in `main.py`.

### Key Subsystems

- **Auth** (`app/core/security.py`, `app/core/dependencies.py`) — JWT (HS256) + bcrypt passwords + OAuth. Guards: `get_current_user`, `get_current_active_user`, `get_current_verified_user`
- **RBAC** (`app/core/permissions.py`, `app/models/role.py`) — Role-based access via many-to-many User↔Role↔Permission
- **WebSocket** (`app/services/websocket/manager.py`, `channels.py`) — Global connection manager with per-model channel broadcasting
- **Task Queue** (`app/workers/`) — ARQ workers for media processing, email sending, webhook delivery
- **Storage** (`app/services/storage_service.py`) — Abstraction over S3/MinIO and local filesystem, toggled by `USE_S3`
- **Middleware** pipeline in `main.py`: LoggingMiddleware → MetricsMiddleware → RateLimitMiddleware → CORSMiddleware

### Database

- **Default**: SQLite (`sqlite:///./app.db`) for development
- **Production**: PostgreSQL with pgvector extension for vector embeddings
- **Migrations**: Alembic in `alembic/versions/`
- **Connection**: `app/database/connection.py` — auto-creates tables on first startup if none exist

### Configuration

All config via environment variables loaded in `app/config.py` (Settings class). Copy `.env.example` to `.env`. Key feature toggles:
- `REDIS_ENABLED` — enables caching, rate limiting, task notifications
- `USE_S3` — switches between S3/MinIO and local file storage
- `RELOAD` — enables uvicorn hot reload

### API Docs

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- Health check: `/health`
- Prometheus metrics: `/metrics`
- WebSocket test client: `/static/websocket-test.html`
