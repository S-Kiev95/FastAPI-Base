"""
Security utilities for JWT authentication and password hashing.
Supports JWT access/refresh tokens, purpose tokens (verify email, password reset),
and OAuth providers.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera hash bcrypt de la contraseña."""
    return pwd_context.hash(password)


# --- Access tokens ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea JWT access token (vida corta, default desde settings)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """Decodifica JWT y retorna email (sub). None si inválido."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        return email if email else None
    except JWTError:
        return None


# --- Refresh tokens ---

def hash_token(raw_token: str) -> str:
    """SHA-256 del token raw para almacenar en BD."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_refresh_token() -> Tuple[str, str, datetime]:
    """
    Genera un refresh token seguro.
    Returns:
        (raw_token, token_hash, expires_at)
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, token_hash, expires_at


# --- Purpose tokens (verificación email, password reset) ---

def create_verification_token(email: str) -> str:
    """JWT firmado con purpose='verify', expira en 24h."""
    data = {"sub": email, "purpose": "verify"}
    expire = datetime.utcnow() + timedelta(hours=24)
    data["exp"] = expire
    return jwt.encode(data, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_token(email: str) -> str:
    """JWT firmado con purpose='reset', expira en 1h."""
    data = {"sub": email, "purpose": "reset"}
    expire = datetime.utcnow() + timedelta(hours=1)
    data["exp"] = expire
    return jwt.encode(data, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_purpose_token(token: str, expected_purpose: str) -> Optional[str]:
    """
    Decodifica JWT y valida que el purpose coincida.
    Returns: email si válido, None si inválido o purpose incorrecto.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        purpose: str = payload.get("purpose")
        if not email or purpose != expected_purpose:
            return None
        return email
    except JWTError:
        return None
