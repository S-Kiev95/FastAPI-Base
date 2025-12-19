# Quick Start Guide

Guía rápida para empezar a usar esta plantilla FastAPI con WebSocket en 5 minutos.

## Instalación Rápida

```bash
# 1. Clonar/copiar el proyecto
cd fastapi_base

# 2. Instalar dependencias
uv sync

# 3. Configurar variables de entorno (opcional, ya hay valores por defecto)
# cp .env.example .env

# 4. Iniciar el servidor
uv run python main.py
```

## Primeros Pasos

### 1. Verificar que funciona

Abre tu navegador en: http://localhost:8000

Deberías ver:
```json
{
  "message": "Welcome to FastAPI Base Template",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc",
  "websocket": "/ws/{channel}",
  "websocket_test": "/static/websocket-test.html"
}
```

### 2. Explorar la documentación interactiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Probar WebSocket en tiempo real

Abre: http://localhost:8000/static/websocket-test.html

1. Haz clic en **"Connect"** para conectarte al canal de usuarios
2. Crea usuarios desde la interfaz
3. Observa las actualizaciones en tiempo real
4. Abre múltiples pestañas para ver el broadcast

### 4. Crear tu primer usuario via API

```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "provider_user_id": "quickstart_123",
    "email": "quickstart@example.com",
    "name": "Quick Start User",
    "picture": "https://ui-avatars.com/api/?name=Quick+Start"
  }'
```

Si tienes WebSocket conectado, verás la actualización en tiempo real.

### 5. Ver estadísticas de WebSocket

```bash
curl http://localhost:8000/ws/stats
```

## Agregar Tu Primer Modelo

### Paso 1: Crear el Modelo

Crea `app/models/post.py`:

```python
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    user_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PostCreate(SQLModel):
    title: str
    content: str
    user_id: int


class PostRead(SQLModel):
    id: int
    title: str
    content: str
    user_id: int
    created_at: datetime


class PostUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
```

Actualiza `app/models/__init__.py`:
```python
from .user import User
from .post import Post

__all__ = ["User", "Post"]
```

Actualiza `app/database/connection.py` (línea 24):
```python
from app.models import User, Post  # Importar Post
```

### Paso 2: Crear el Canal WebSocket

Agrega en `app/services/websocket/channels.py`:
```python
posts_channel = ChannelManager(connection_manager, "posts")
```

Actualiza el `__all__` en el mismo archivo.

### Paso 3: Crear el Servicio

Crea `app/services/post_service.py`:

```python
from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select
from app.models.post import Post, PostCreate, PostUpdate, PostRead


class PostService:
    @staticmethod
    def get_all_posts(session: Session, skip: int = 0, limit: int = 100) -> List[Post]:
        statement = select(Post).offset(skip).limit(limit)
        return list(session.exec(statement).all())

    @staticmethod
    async def create_post(session: Session, post_data: PostCreate, broadcast: bool = True) -> Post:
        post = Post(**post_data.model_dump())
        session.add(post)
        session.commit()
        session.refresh(post)

        if broadcast:
            from app.services.websocket import posts_channel
            post_dict = PostRead.model_validate(post).model_dump()
            await posts_channel.broadcast_created(post_dict)

        return post

    @staticmethod
    async def update_post(
        session: Session, post_id: int, post_data: PostUpdate, broadcast: bool = True
    ) -> Optional[Post]:
        post = session.get(Post, post_id)
        if not post:
            return None

        update_data = post_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(post, key, value)

        post.updated_at = datetime.utcnow()
        session.add(post)
        session.commit()
        session.refresh(post)

        if broadcast:
            from app.services.websocket import posts_channel
            post_dict = PostRead.model_validate(post).model_dump()
            await posts_channel.broadcast_updated(post_dict)

        return post

    @staticmethod
    async def delete_post(session: Session, post_id: int, broadcast: bool = True) -> bool:
        post = session.get(Post, post_id)
        if not post:
            return False

        session.delete(post)
        session.commit()

        if broadcast:
            from app.services.websocket import posts_channel
            await posts_channel.broadcast_deleted(post_id)

        return True
```

### Paso 4: Crear las Rutas

Crea `app/routes/posts.py`:

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models.post import PostCreate, PostRead, PostUpdate
from app.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/", response_model=List[PostRead])
def get_posts(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    posts = PostService.get_all_posts(session, skip=skip, limit=limit)
    return posts


@router.post("/", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    session: Session = Depends(get_session)
):
    post = await PostService.create_post(session, post_data)
    return post


@router.patch("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    session: Session = Depends(get_session)
):
    post = await PostService.update_post(session, post_id, post_data)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    session: Session = Depends(get_session)
):
    deleted = await PostService.delete_post(session, post_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    return None
```

### Paso 5: Registrar Todo

1. **En `app/routes/websocket.py`** (línea ~30):
```python
valid_channels = ["users", "posts"]  # Agregar "posts"
```

2. **En `main.py`**:
```python
from app.routes.posts import router as posts_router

# ...

app.include_router(posts_router)
```

3. **Reiniciar el servidor**:
```bash
# Ctrl+C para detener
uv run python main.py
```

### Paso 6: Probar

```bash
# Crear un post
curl -X POST "http://localhost:8000/posts/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mi primer post",
    "content": "Contenido del post",
    "user_id": 1
  }'

# Ver todos los posts
curl http://localhost:8000/posts/
```

Para ver actualizaciones en tiempo real:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/posts');
ws.onmessage = (event) => {
    console.log('Post event:', JSON.parse(event.data));
};
```

## Siguiente Paso

- Lee [README.md](README.md) para entender la estructura completa
- Lee [WEBSOCKET_GUIDE.md](WEBSOCKET_GUIDE.md) para dominar WebSocket
- Lee [OAUTH_SETUP.md](OAUTH_SETUP.md) si necesitas OAuth

## Tips Rápidos

### Cambiar a PostgreSQL

```env
# En .env
DATABASE_URL=postgresql://usuario:password@localhost/mi_base_datos
```

```bash
# Instalar driver
uv add psycopg2-binary
```

### Agregar CORS

```python
# En main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Desactivar Broadcast

```python
# Si no quieres broadcast en una operación específica
user = await UserService.create_user(session, user_data, broadcast=False)
```

### Logging Personalizado

```python
# En main.py o donde necesites
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Mensaje de información")
```

## Solución de Problemas

### El servidor no inicia

```bash
# Verifica que las dependencias estén instaladas
uv sync

# Verifica la versión de Python
python --version  # Debe ser >= 3.13

# Verifica el puerto
# Si 8000 está ocupado, cambia en .env:
PORT=8001
```

### WebSocket no conecta

1. Verifica que el servidor esté corriendo
2. Usa `ws://` no `http://` para WebSocket
3. Verifica el canal en la URL: `/ws/users`, `/ws/posts`, etc.
4. Revisa la consola del navegador para errores

### Base de datos no se crea

1. Verifica permisos de escritura en el directorio
2. Para SQLite, el archivo `app.db` debería crearse automáticamente
3. Revisa los logs en la consola al iniciar el servidor

### Import errors

```bash
# Asegúrate de estar en el directorio correcto
cd fastapi_base

# Reinstala dependencias
uv sync --reinstall
```

## Recursos

- **Documentación**: http://localhost:8000/docs
- **WebSocket Test**: http://localhost:8000/static/websocket-test.html
- **Estadísticas WS**: http://localhost:8000/ws/stats
- **Health Check**: http://localhost:8000/health

## Contacto y Soporte

- FastAPI Docs: https://fastapi.tiangolo.com/
- SQLModel Docs: https://sqlmodel.tiangolo.com/
- WebSocket MDN: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
