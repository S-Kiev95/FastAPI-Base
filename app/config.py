import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # API Configuration
    API_TITLE: str = os.getenv("API_TITLE", "FastAPI Base Template")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION: str = os.getenv(
        "API_DESCRIPTION",
        "FastAPI template with SQLModel and authentication"
    )

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "True").lower() == "true"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")

    # OAuth (optional)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Storage Configuration
    USE_S3: bool = os.getenv("USE_S3", "False").lower() == "true"
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")  # For MinIO, leave empty for AWS S3
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "media")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

    # Local Storage (fallback)
    MEDIA_FOLDER: str = os.getenv("MEDIA_FOLDER", "./media")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default

    # SMTP Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "FastAPI Base")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "True").lower() == "true"

    # Email Templates
    EMAIL_TEMPLATES_DIR: str = os.getenv("EMAIL_TEMPLATES_DIR", "app/templates/emails")

    # Redis Cache Configuration (Optional - cache disabled if not configured)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "False").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default

    # CORS Configuration
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")  # Comma-separated origins or "*"
    CORS_CREDENTIALS: bool = os.getenv("CORS_CREDENTIALS", "True").lower() == "true"
    CORS_METHODS: str = os.getenv("CORS_METHODS", "*")  # Comma-separated methods or "*"
    CORS_HEADERS: str = os.getenv("CORS_HEADERS", "*")  # Comma-separated headers or "*"

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # json or text
    LOG_FILE: str = os.getenv("LOG_FILE", "")  # Optional: path to log file (e.g., "logs/app.log")

    # Auth tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    INVITATION_EXPIRE_HOURS: int = int(os.getenv("INVITATION_EXPIRE_HOURS", "48"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Multi-tenancy
    DEFAULT_PLAN: str = os.getenv("DEFAULT_PLAN", "free")
    SYSTEM_ORG_SLUG: str = os.getenv("SYSTEM_ORG_SLUG", "system")
    SYSTEM_ADMIN_EMAIL: str = os.getenv("SYSTEM_ADMIN_EMAIL", "")
    SYSTEM_ADMIN_PASSWORD: str = os.getenv("SYSTEM_ADMIN_PASSWORD", "")

    # SaaS Features
    SOFT_DELETE_ENABLED: bool = os.getenv("SOFT_DELETE_ENABLED", "True").lower() == "true"
    AUDIT_LOG_ENABLED: bool = os.getenv("AUDIT_LOG_ENABLED", "True").lower() == "true"
    API_KEYS_ENABLED: bool = os.getenv("API_KEYS_ENABLED", "True").lower() == "true"
    API_KEY_PREFIX: str = os.getenv("API_KEY_PREFIX", "sk_live_")
    GDPR_EXPORT_ENABLED: bool = os.getenv("GDPR_EXPORT_ENABLED", "True").lower() == "true"
    ACCOUNT_DELETION_GRACE_DAYS: int = int(os.getenv("ACCOUNT_DELETION_GRACE_DAYS", "30"))

    # Observability
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Security
    ENFORCE_STRONG_PASSWORDS: bool = os.getenv("ENFORCE_STRONG_PASSWORDS", "False").lower() == "true"

    # Billing / Payment Gateways
    ACTIVE_PAYMENT_GATEWAY: str = os.getenv("ACTIVE_PAYMENT_GATEWAY", "stripe")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    MERCADOPAGO_ACCESS_TOKEN: str = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
    MERCADOPAGO_WEBHOOK_SECRET: str = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")
    POLAR_ACCESS_TOKEN: str = os.getenv("POLAR_ACCESS_TOKEN", "")
    POLAR_WEBHOOK_SECRET: str = os.getenv("POLAR_WEBHOOK_SECRET", "")

    @property
    def cors_origins_list(self) -> list:
        """Convert CORS_ORIGINS string to list"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
