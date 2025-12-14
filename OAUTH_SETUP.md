# Configuración de OAuth

Esta plantilla incluye un modelo de usuario preparado para trabajar con proveedores OAuth como Google, GitHub, etc.

## Cómo Integrar OAuth

### 1. Google OAuth

#### Obtener credenciales:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API de Google+ (Google+ API)
4. Ve a "Credenciales" → "Crear credenciales" → "ID de cliente de OAuth 2.0"
5. Configura la pantalla de consentimiento
6. Añade URLs autorizadas:
   - JavaScript origins: `http://localhost:8000`
   - Redirect URIs: `http://localhost:8000/auth/google/callback`
7. Copia el Client ID y Client Secret

#### Configurar en tu aplicación:

Añade a tu archivo `.env`:

```env
GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret-aqui
```

#### Implementar el endpoint de OAuth:

```python
# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from app.database import get_session
from app.services.user_service import UserService
from app.models.user import UserCreate
import httpx

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/google/login")
async def google_login():
    """Redirige al usuario a la página de login de Google"""
    google_oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri=http://localhost:8000/auth/google/callback&"
        f"response_type=code&"
        f"scope=openid email profile"
    )
    return RedirectResponse(google_oauth_url)

@router.get("/google/callback")
async def google_callback(code: str, session: Session = Depends(get_session)):
    """Callback de Google OAuth"""
    # Intercambiar código por token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": "http://localhost:8000/auth/google/callback",
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        token_json = token_response.json()

        # Obtener información del usuario
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {token_json['access_token']}"}
        user_response = await client.get(user_info_url, headers=headers)
        user_info = user_response.json()

    # Crear o actualizar usuario
    user_data = UserCreate(
        provider="google",
        provider_user_id=user_info["id"],
        email=user_info["email"],
        name=user_info.get("name"),
        picture=user_info.get("picture"),
    )

    user, created = UserService.get_or_create_user(
        session,
        provider="google",
        provider_user_id=user_info["id"],
        user_data=user_data
    )

    # Aquí normalmente crearías un JWT token y lo devolverías
    return {
        "message": "Login successful",
        "user": user,
        "is_new_user": created
    }
```

### 2. GitHub OAuth

Similar a Google, pero con diferentes URLs:

```python
# Configuración
GITHUB_CLIENT_ID=tu-github-client-id
GITHUB_CLIENT_SECRET=tu-github-client-secret

# Login URL
github_oauth_url = (
    f"https://github.com/login/oauth/authorize?"
    f"client_id={settings.GITHUB_CLIENT_ID}&"
    f"redirect_uri=http://localhost:8000/auth/github/callback&"
    f"scope=user:email"
)

# Token URL
https://github.com/login/oauth/access_token

# User Info URL
https://api.github.com/user
```

## Dependencias Adicionales Necesarias

Para implementar OAuth completo, necesitarás:

```bash
uv add httpx  # Para hacer peticiones HTTP
uv add python-jose[cryptography]  # Para JWT tokens
uv add passlib[bcrypt]  # Para hashing de contraseñas (si es necesario)
```

## Estructura Recomendada con OAuth

```
app/
├── routes/
│   ├── auth.py          # Rutas de autenticación
│   └── users.py         # Rutas de usuarios (protegidas)
├── services/
│   ├── auth_service.py  # Lógica de autenticación
│   └── user_service.py  # Lógica de usuarios
└── middleware/
    └── auth.py          # Middleware de autenticación (JWT)
```

## Ejemplo de Middleware de Autenticación

```python
# app/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlmodel import Session
from app.database import get_session
from app.services.user_service import UserService
from app.config import settings

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
):
    """Dependency para obtener el usuario actual desde el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = UserService.get_user_by_id(session, user_id)
    if user is None:
        raise credentials_exception

    return user
```

## Uso en Rutas Protegidas

```python
from app.middleware.auth import get_current_user
from app.models.user import User

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.name}"}
```

## Referencias

- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Jose JWT](https://python-jose.readthedocs.io/)
