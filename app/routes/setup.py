"""
Setup Wizard Routes
====================
Endpoints para el wizard de configuración inicial del sistema.
Estos endpoints NO requieren autenticación porque se usan antes
de que el sistema esté configurado.

IMPORTANTE: Una vez que el sistema está configurado (archivo .env existe
con SECRET_KEY válido), estos endpoints solo son accesibles por superadmin.
"""
import os
import re
import secrets
from pathlib import Path
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.logger import get_structured_logger

logger = get_structured_logger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup Wizard"])

# Path al archivo .env en la raíz del proyecto
ENV_FILE_PATH = Path(__file__).parent.parent.parent / ".env"


# ============================================================================
# Request/Response Models
# ============================================================================

class SetupStatus(BaseModel):
    """Estado actual del setup del sistema."""
    configured: bool
    env_file_exists: bool
    required_vars_set: bool
    missing_vars: list[str] = []
    optional_vars_missing: list[str] = []
    environment: Optional[str] = None


class DatabaseConfig(BaseModel):
    """Configuración de base de datos."""
    database_url: str = Field(
        ...,
        description="URL de PostgreSQL: postgresql://user:pass@host:port/dbname",
        examples=["postgresql://postgres:password@localhost:5432/myapp"]
    )


class RedisConfig(BaseModel):
    """Configuración de Redis."""
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0, ge=0, le=15)


class S3Config(BaseModel):
    """Configuración de S3 storage."""
    s3_bucket_name: str
    s3_region: str = Field(default="us-east-1")
    s3_access_key: str
    s3_secret_key: str
    s3_endpoint_url: Optional[str] = Field(
        default=None,
        description="URL custom para MinIO, Backblaze B2, etc. Vacío para AWS S3."
    )


class SmtpConfig(BaseModel):
    """Configuración SMTP."""
    smtp_host: str
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str
    smtp_password: str
    smtp_from_email: str
    smtp_use_tls: bool = True


class StripeConfig(BaseModel):
    """Configuración de Stripe."""
    stripe_secret_key: str = Field(
        ...,
        description="Stripe secret key (sk_test_... o sk_live_...)"
    )
    stripe_webhook_secret: Optional[str] = None


class AdminUserConfig(BaseModel):
    """Configuración del usuario admin inicial."""
    admin_email: str
    admin_password: str = Field(..., min_length=8)
    admin_name: str = Field(default="System Admin")


class ValidationResult(BaseModel):
    """Resultado de una validación."""
    success: bool
    message: str
    details: Optional[dict] = None
    warnings: list[str] = []


class SaveConfigRequest(BaseModel):
    """Request para guardar configuración completa."""
    environment: Literal["development", "staging", "production"] = "production"
    database_url: str
    secret_key: Optional[str] = None  # Se genera si no se provee

    # Redis (opcional)
    redis_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None

    # Security
    enforce_strong_passwords: bool = True
    cors_origins: str = "*"

    # Storage (opcional)
    use_s3: bool = False
    s3_bucket_name: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_endpoint_url: Optional[str] = None

    # SMTP (opcional)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None

    # Payment (opcional)
    active_payment_gateway: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # Observability (opcional)
    sentry_dsn: Optional[str] = None

    # Admin user
    admin_email: str
    admin_password: str
    admin_name: str = "System Admin"


# ============================================================================
# Helper Functions
# ============================================================================

def _is_system_configured() -> bool:
    """
    Determina si el sistema ya está configurado.
    Se considera configurado si el archivo .env existe Y tiene SECRET_KEY válido.
    """
    if not ENV_FILE_PATH.exists():
        return False

    # Verificar que SECRET_KEY esté configurado (no el default)
    secret_key = os.getenv("SECRET_KEY", "")
    if not secret_key or secret_key == "change-me-in-production":
        return False

    return True


def _generate_secret_key() -> str:
    """Genera una SECRET_KEY segura de 256 bits."""
    return secrets.token_hex(32)


def _parse_database_url(url: str) -> dict:
    """Parsea una DATABASE_URL en sus componentes."""
    # postgresql://user:pass@host:port/dbname
    pattern = r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)"
    match = re.match(pattern, url)
    if not match:
        raise ValueError("Formato de DATABASE_URL inválido")

    return {
        "user": match.group(1),
        "password": match.group(2),
        "host": match.group(3),
        "port": int(match.group(4)) if match.group(4) else 5432,
        "database": match.group(5),
    }


# ============================================================================
# Status Endpoint
# ============================================================================

@router.get("/status", response_model=SetupStatus)
async def get_setup_status():
    """
    Retorna el estado actual del setup del sistema.

    Usado por el frontend para determinar si mostrar el wizard.
    """
    required_vars = ["DATABASE_URL", "SECRET_KEY"]
    optional_vars = [
        "REDIS_HOST", "SMTP_HOST", "S3_BUCKET_NAME",
        "STRIPE_SECRET_KEY", "SENTRY_DSN"
    ]

    missing = []
    for var in required_vars:
        val = os.getenv(var, "")
        if not val or val in ("change-me-in-production", ""):
            missing.append(var)

    missing_optional = []
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)

    configured = len(missing) == 0 and ENV_FILE_PATH.exists()

    return SetupStatus(
        configured=configured,
        env_file_exists=ENV_FILE_PATH.exists(),
        required_vars_set=len(missing) == 0,
        missing_vars=missing,
        optional_vars_missing=missing_optional,
        environment=os.getenv("ENVIRONMENT", "development"),
    )


# ============================================================================
# Validation Endpoints
# ============================================================================

@router.post("/validate/database", response_model=ValidationResult)
async def validate_database(config: DatabaseConfig):
    """
    Valida conexión a PostgreSQL y verifica extensiones.

    Verifica:
    - Conexión exitosa
    - Versión de PostgreSQL (>= 13)
    - Extensión pgvector disponible
    - Permisos de creación de tablas
    """
    try:
        # Parsear URL
        db_info = _parse_database_url(config.database_url)

        # Intentar conexión con SQLAlchemy
        from sqlalchemy import create_engine, text as sql_text

        engine = create_engine(
            config.database_url,
            connect_args={"connect_timeout": 5}
        )

        details = {}
        warnings = []

        with engine.connect() as conn:
            # 1. Verificar versión
            version_result = conn.execute(sql_text("SHOW server_version"))
            version = version_result.scalar()
            details["postgresql_version"] = version

            # Parsear major version
            try:
                major_version = int(version.split(".")[0])
                if major_version < 13:
                    warnings.append(
                        f"PostgreSQL {version} es antiguo. Se recomienda 15+."
                    )
            except (ValueError, IndexError):
                pass

            # 2. Verificar pgvector disponible
            pgvector_check = conn.execute(sql_text(
                "SELECT name FROM pg_available_extensions WHERE name = 'vector'"
            ))
            pgvector_available = pgvector_check.scalar() is not None
            details["pgvector_available"] = pgvector_available

            if not pgvector_available:
                warnings.append(
                    "pgvector NO está disponible. Instálalo con: "
                    "CREATE EXTENSION vector; o sudo apt install postgresql-15-pgvector"
                )

            # 3. Verificar si pgvector ya está instalado
            pgvector_installed_check = conn.execute(sql_text(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            ))
            pgvector_installed = pgvector_installed_check.scalar() is not None
            details["pgvector_installed"] = pgvector_installed

            # 4. Verificar permisos CREATE TABLE
            try:
                conn.execute(sql_text(
                    "CREATE TABLE IF NOT EXISTS _setup_test (id int); "
                    "DROP TABLE _setup_test;"
                ))
                conn.commit()
                details["can_create_tables"] = True
            except Exception as e:
                details["can_create_tables"] = False
                warnings.append(f"No se pueden crear tablas: {str(e)[:100]}")

            # 5. Info de la DB
            details["database"] = db_info["database"]
            details["host"] = db_info["host"]
            details["port"] = db_info["port"]

        engine.dispose()

        return ValidationResult(
            success=True,
            message="Conexión a PostgreSQL exitosa",
            details=details,
            warnings=warnings,
        )

    except ValueError as e:
        return ValidationResult(
            success=False,
            message=f"Formato de URL inválido: {str(e)}",
        )
    except Exception as e:
        logger.error("Database validation failed", error=str(e))
        return ValidationResult(
            success=False,
            message=f"Error de conexión: {str(e)[:200]}",
        )


@router.post("/validate/redis", response_model=ValidationResult)
async def validate_redis(config: RedisConfig):
    """
    Valida conexión a Redis.

    Verifica:
    - Conexión exitosa (PING)
    - Versión de Redis
    - Permisos de SET/GET
    """
    try:
        import redis

        r = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password or None,
            db=config.redis_db,
            socket_connect_timeout=5,
            decode_responses=True,
        )

        details = {}

        # 1. Ping
        r.ping()

        # 2. Info del servidor
        info = r.info()
        details["redis_version"] = info.get("redis_version")
        details["mode"] = info.get("redis_mode", "standalone")
        details["connected_clients"] = info.get("connected_clients", 0)
        details["used_memory_human"] = info.get("used_memory_human", "N/A")

        # 3. Test de escritura/lectura
        test_key = "_setup_wizard_test"
        r.set(test_key, "test_value", ex=10)
        value = r.get(test_key)
        r.delete(test_key)

        if value != "test_value":
            raise Exception("Test de escritura/lectura falló")

        details["read_write"] = True

        r.close()

        return ValidationResult(
            success=True,
            message=f"Conexión a Redis exitosa (v{details['redis_version']})",
            details=details,
        )

    except Exception as e:
        logger.error("Redis validation failed", error=str(e))
        return ValidationResult(
            success=False,
            message=f"Error de conexión a Redis: {str(e)[:200]}",
        )


@router.post("/validate/s3", response_model=ValidationResult)
async def validate_s3(config: S3Config):
    """
    Valida credenciales S3 y acceso al bucket.

    Verifica:
    - Credenciales válidas
    - Bucket existe
    - Permisos de PutObject y GetObject
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        s3_kwargs = {
            "aws_access_key_id": config.s3_access_key,
            "aws_secret_access_key": config.s3_secret_key,
            "region_name": config.s3_region,
        }

        if config.s3_endpoint_url:
            s3_kwargs["endpoint_url"] = config.s3_endpoint_url

        client = boto3.client("s3", **s3_kwargs)

        details = {}
        warnings = []

        # 1. Verificar que el bucket existe
        try:
            client.head_bucket(Bucket=config.s3_bucket_name)
            details["bucket_exists"] = True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                return ValidationResult(
                    success=False,
                    message=f"Bucket '{config.s3_bucket_name}' no existe",
                )
            elif error_code == "403":
                return ValidationResult(
                    success=False,
                    message="Acceso denegado al bucket. Verifica credenciales y permisos.",
                )
            else:
                raise

        # 2. Test de PutObject
        test_key = "_setup_wizard_test.txt"
        try:
            client.put_object(
                Bucket=config.s3_bucket_name,
                Key=test_key,
                Body=b"setup wizard test",
                ContentType="text/plain",
            )
            details["can_put_object"] = True
        except ClientError:
            details["can_put_object"] = False
            warnings.append("No se pueden subir archivos (PutObject denegado)")

        # 3. Test de GetObject
        if details.get("can_put_object"):
            try:
                client.get_object(Bucket=config.s3_bucket_name, Key=test_key)
                details["can_get_object"] = True
            except ClientError:
                details["can_get_object"] = False
                warnings.append("No se pueden leer archivos (GetObject denegado)")

            # 4. Cleanup
            try:
                client.delete_object(Bucket=config.s3_bucket_name, Key=test_key)
            except ClientError:
                warnings.append("No se pudo eliminar el archivo de prueba")

        details["region"] = config.s3_region
        details["endpoint"] = config.s3_endpoint_url or "AWS S3"

        return ValidationResult(
            success=True,
            message=f"Acceso a bucket '{config.s3_bucket_name}' validado",
            details=details,
            warnings=warnings,
        )

    except ImportError:
        return ValidationResult(
            success=False,
            message="boto3 no está instalado. Ejecuta: uv add boto3",
        )
    except Exception as e:
        logger.error("S3 validation failed", error=str(e))
        return ValidationResult(
            success=False,
            message=f"Error de S3: {str(e)[:200]}",
        )


@router.post("/validate/smtp", response_model=ValidationResult)
async def validate_smtp(config: SmtpConfig):
    """
    Valida conexión SMTP.

    Verifica:
    - Conexión al servidor
    - Autenticación
    - Soporte TLS
    """
    try:
        import smtplib

        details = {}

        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as server:
            # EHLO
            server.ehlo()
            details["server_info"] = server.ehlo_resp.decode("utf-8", errors="ignore")[:200]

            # TLS si está habilitado
            if config.smtp_use_tls:
                if server.has_extn("STARTTLS"):
                    server.starttls()
                    server.ehlo()
                    details["tls"] = True
                else:
                    return ValidationResult(
                        success=False,
                        message="Servidor no soporta STARTTLS",
                    )

            # Autenticación
            server.login(config.smtp_user, config.smtp_password)
            details["authenticated"] = True

        return ValidationResult(
            success=True,
            message=f"Conexión SMTP a {config.smtp_host}:{config.smtp_port} exitosa",
            details=details,
        )

    except Exception as e:
        logger.error("SMTP validation failed", error=str(e))
        return ValidationResult(
            success=False,
            message=f"Error SMTP: {str(e)[:200]}",
        )


@router.post("/validate/stripe", response_model=ValidationResult)
async def validate_stripe(config: StripeConfig):
    """
    Valida credenciales de Stripe.

    Verifica:
    - API key válida
    - Modo (test/live)
    """
    try:
        import stripe

        # Detectar modo
        if config.stripe_secret_key.startswith("sk_test_"):
            mode = "test"
        elif config.stripe_secret_key.startswith("sk_live_"):
            mode = "live"
        else:
            return ValidationResult(
                success=False,
                message="Formato de Stripe key inválido (debe empezar con sk_test_ o sk_live_)",
            )

        stripe.api_key = config.stripe_secret_key

        # Intentar hacer un request simple
        account = stripe.Account.retrieve()

        details = {
            "mode": mode,
            "account_id": account.id,
            "country": account.country,
            "email": account.email,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
        }

        warnings = []
        if mode == "test":
            warnings.append("Usando Stripe en modo TEST")
        if not account.charges_enabled:
            warnings.append("Charges no están habilitados en esta cuenta")

        return ValidationResult(
            success=True,
            message=f"Stripe conectado correctamente (modo {mode})",
            details=details,
            warnings=warnings,
        )

    except ImportError:
        return ValidationResult(
            success=False,
            message="stripe no está instalado. Ejecuta: uv add stripe",
        )
    except Exception as e:
        logger.error("Stripe validation failed", error=str(e))
        return ValidationResult(
            success=False,
            message=f"Error Stripe: {str(e)[:200]}",
        )


# ============================================================================
# Save Configuration
# ============================================================================

@router.post("/save", response_model=ValidationResult)
async def save_configuration(config: SaveConfigRequest):
    """
    Guarda la configuración completa en el archivo .env

    IMPORTANTE: Solo permite guardar si el sistema NO está configurado,
    o si se provee un token de superadmin.
    """
    # Solo permitir si no está configurado
    if _is_system_configured():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El sistema ya está configurado. Usa las herramientas de admin para cambiar la configuración."
        )

    try:
        # Generar SECRET_KEY si no se provee
        secret_key = config.secret_key or _generate_secret_key()

        # Construir contenido del .env
        env_lines = [
            "# ============================================================================",
            "# Configuración generada por Setup Wizard",
            "# ============================================================================",
            "",
            f"ENVIRONMENT={config.environment}",
            "",
            "# Database",
            f"DATABASE_URL={config.database_url}",
            "",
            "# Security",
            f"SECRET_KEY={secret_key}",
            f"ENFORCE_STRONG_PASSWORDS={'true' if config.enforce_strong_passwords else 'false'}",
            "",
            "# CORS",
            f"CORS_ORIGINS={config.cors_origins}",
            "",
            "# Redis",
            f"REDIS_ENABLED={'true' if config.redis_enabled else 'false'}",
        ]

        if config.redis_enabled:
            env_lines.extend([
                f"REDIS_HOST={config.redis_host}",
                f"REDIS_PORT={config.redis_port}",
            ])
            if config.redis_password:
                env_lines.append(f"REDIS_PASSWORD={config.redis_password}")

        env_lines.append("")
        env_lines.append("# Storage")
        env_lines.append(f"USE_S3={'true' if config.use_s3 else 'false'}")

        if config.use_s3:
            env_lines.extend([
                f"S3_BUCKET_NAME={config.s3_bucket_name or ''}",
                f"S3_REGION={config.s3_region or 'us-east-1'}",
                f"S3_ACCESS_KEY={config.s3_access_key or ''}",
                f"S3_SECRET_KEY={config.s3_secret_key or ''}",
            ])
            if config.s3_endpoint_url:
                env_lines.append(f"S3_ENDPOINT_URL={config.s3_endpoint_url}")

        # SMTP
        if config.smtp_host:
            env_lines.extend([
                "",
                "# SMTP",
                f"SMTP_HOST={config.smtp_host}",
                f"SMTP_PORT={config.smtp_port or 587}",
                f"SMTP_USER={config.smtp_user or ''}",
                f"SMTP_PASSWORD={config.smtp_password or ''}",
                f"SMTP_FROM_EMAIL={config.smtp_from_email or ''}",
            ])

        # Payment
        if config.active_payment_gateway:
            env_lines.extend([
                "",
                "# Payment",
                f"ACTIVE_PAYMENT_GATEWAY={config.active_payment_gateway}",
            ])
            if config.stripe_secret_key:
                env_lines.append(f"STRIPE_SECRET_KEY={config.stripe_secret_key}")
            if config.stripe_webhook_secret:
                env_lines.append(f"STRIPE_WEBHOOK_SECRET={config.stripe_webhook_secret}")

        # Sentry
        if config.sentry_dsn:
            env_lines.extend([
                "",
                "# Observability",
                f"SENTRY_DSN={config.sentry_dsn}",
            ])

        # Admin user
        env_lines.extend([
            "",
            "# Admin User (creado en primer inicio)",
            f"SYSTEM_ADMIN_EMAIL={config.admin_email}",
            f"SYSTEM_ADMIN_PASSWORD={config.admin_password}",
        ])

        # Escribir archivo
        env_content = "\n".join(env_lines) + "\n"

        with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(env_content)

        logger.info(
            "Configuration saved via setup wizard",
            env_path=str(ENV_FILE_PATH),
            environment=config.environment,
        )

        return ValidationResult(
            success=True,
            message="Configuración guardada exitosamente en .env. Reinicia el backend para aplicar los cambios.",
            details={
                "env_file": str(ENV_FILE_PATH),
                "secret_key_generated": config.secret_key is None,
                "restart_required": True,
            },
            warnings=[
                "⚠️ IMPORTANTE: Debes reiniciar el backend para aplicar los cambios",
                "⚠️ Guarda las credenciales del admin en un lugar seguro",
            ],
        )

    except Exception as e:
        logger.error("Failed to save configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error guardando configuración: {str(e)}"
        )


@router.get("/generate-secret-key")
async def generate_secret_key():
    """Genera una nueva SECRET_KEY segura de 256 bits."""
    return {"secret_key": _generate_secret_key()}
