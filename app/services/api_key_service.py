"""
Servicio de API Keys — generación, verificación y gestión.
"""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List
from sqlmodel import Session, select
from app.models.api_key import ApiKey
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ApiKeyService:
    """Gestión de API keys con hash SHA-256."""

    def _hash_key(self, raw_key: str) -> str:
        """SHA-256 hash de un API key."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def generate_key(self) -> Tuple[str, str, str]:
        """
        Genera un API key.
        Returns: (raw_key, key_prefix, key_hash)
        """
        prefix = settings.API_KEY_PREFIX
        random_part = secrets.token_urlsafe(48)
        raw_key = f"{prefix}{random_part}"
        key_prefix = raw_key[:12]
        key_hash = self._hash_key(raw_key)
        return raw_key, key_prefix, key_hash

    def create_key(
        self,
        session: Session,
        *,
        user_id: int,
        name: str,
        organization_id: Optional[str] = None,
        scopes: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[ApiKey, str]:
        """
        Crea una nueva API key.
        Returns: (ApiKey model, raw_key)
        """
        raw_key, key_prefix, key_hash = self.generate_key()

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = ApiKey(
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            user_id=user_id,
            organization_id=organization_id,
            scopes=scopes,
            expires_at=expires_at,
        )
        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        logger.info(f"API key creada: {key_prefix}... para user_id={user_id}")
        return api_key, raw_key

    def verify_key(self, session: Session, raw_key: str) -> Optional[ApiKey]:
        """
        Verifica un API key raw. Retorna el ApiKey si es válido, None si no.
        Actualiza last_used_at.
        """
        key_hash = self._hash_key(raw_key)
        statement = select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True,
        )
        api_key = session.exec(statement).first()

        if not api_key:
            return None

        # Verificar expiración
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None

        # Actualizar last_used_at
        api_key.last_used_at = datetime.now(timezone.utc)
        session.add(api_key)
        session.commit()

        return api_key

    def revoke_key(self, session: Session, key_id, user_id: int) -> bool:
        """Revoca un API key (solo si pertenece al usuario)."""
        import uuid as _uuid
        if isinstance(key_id, str):
            key_id = _uuid.UUID(key_id)
        statement = select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == user_id,
        )
        api_key = session.exec(statement).first()
        if not api_key:
            return False

        api_key.is_active = False
        session.add(api_key)
        session.commit()
        return True

    def list_keys(self, session: Session, user_id: int) -> List[ApiKey]:
        """Lista las API keys de un usuario (activas)."""
        statement = select(ApiKey).where(
            ApiKey.user_id == user_id,
            ApiKey.is_active == True,
        )
        return list(session.exec(statement).all())

    def has_scope(self, api_key: ApiKey, required_scope: str) -> bool:
        """Verifica si un API key tiene el scope requerido."""
        if not api_key.scopes:
            return True  # Sin scopes = acceso total
        scopes = [s.strip() for s in api_key.scopes.split(",")]
        return required_scope in scopes


api_key_service = ApiKeyService()
