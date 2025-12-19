import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlmodel import inspect
from prometheus_fastapi_instrumentator import Instrumentator
import os

from app.config import settings
from app.database import engine, init_db, get_session
from app.routes import users_router
from app.routes.auth import router as auth_router
from app.routes.media import router as media_router
from app.routes.websocket import router as websocket_router
from app.routes.roles import router as roles_router
from app.routes.email import router as email_router
from app.routes.cors import router as cors_router
from app.routes.metrics import router as metrics_router
from app.routes.tasks import router as tasks_router
from app.services.cors_service import cors_service
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.services.task_notification_service import start_task_notification_listener
from app.utils.logger import get_structured_logger

# Setup logger
logger = get_structured_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for the application.
    Checks if database exists and creates tables if needed.
    """
    logger.info("Starting FastAPI application")

    # Check if tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        logger.info("Database already initialized", table_count=len(existing_tables))
    else:
        logger.info("Initializing database")
        init_db()

    # Start task notification listener (if Redis is enabled)
    if settings.REDIS_ENABLED:
        asyncio.create_task(start_task_notification_listener())
        logger.info("Task notification listener started")

    yield

    logger.info("Shutting down FastAPI application")


# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# Configure CORS with dynamic origins from database
# Note: CORS middleware is configured on startup with DB origins
# Origins are cached for performance, fallback to "*" if DB is empty
def get_cors_origins():
    """Get CORS origins from database with fallback to '*' if empty"""
    try:
        session = next(get_session())
        origins = cors_service.get_active_origins(session)
        session.close()
        logger.info("CORS configured with origins from database", origin_count=len(origins))
        return origins
    except Exception as e:
        logger.warning("Could not load CORS origins from DB, falling back to environment", error=str(e))
        return settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS.split(",") if settings.CORS_METHODS != "*" else ["*"],
    allow_headers=settings.CORS_HEADERS.split(",") if settings.CORS_HEADERS != "*" else ["*"],
)

# Add logging middleware (should be first to capture all requests)
app.add_middleware(LoggingMiddleware)

# Add metrics middleware to collect API metrics
app.add_middleware(MetricsMiddleware)

# Add rate limiting middleware (if Redis is enabled)
if settings.REDIS_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=100,  # 100 requests per minute (default)
        default_window=60,
        exclude_paths=["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]
    )
    logger.info("Rate limiting enabled", default_limit=100, window=60)
else:
    logger.warning("Rate limiting disabled (Redis not enabled)")

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(media_router)
app.include_router(websocket_router)
app.include_router(roles_router)
app.include_router(email_router)
app.include_router(cors_router)
app.include_router(metrics_router)
app.include_router(tasks_router)

# Configure Prometheus metrics
# Instrument the app with Prometheus metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=False,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="fastapi_inprogress",
    inprogress_labels=True,
)

instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
def root():
    """Root endpoint - Home page with project documentation"""
    html_path = os.path.join(os.path.dirname(__file__), "app", "templates", "home.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


def main():
    """Run the application with uvicorn"""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", port=port, host="0.0.0.0")
