# Ejemplo: Cómo Agregar un Nuevo Modelo (Posts)

Este documento muestra lo **fácil** que es agregar un nuevo modelo con WebSocket usando el `BaseService` genérico.

## Paso 1: Crear el Modelo (app/models/post.py)

```python
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Post(SQLModel, table=True):
    """Post model"""
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    user_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PostCreate(SQLModel):
    """Schema for creating a post"""
    title: str
    content: str
    user_id: int


class PostRead(SQLModel):
    """Schema for reading a post"""
    id: int
    title: str
    content: str
    user_id: int
    created_at: datetime


class PostUpdate(SQLModel):
    """Schema for updating a post"""
    title: Optional[str] = None
    content: Optional[str] = None
```

## Paso 2: Crear el Canal WebSocket

En `app/services/websocket/channels.py`, agregar:

```python
# Al final del archivo
posts_channel = ChannelManager(connection_manager, "posts")
```

Y exportarlo en `app/services/websocket/__init__.py`:

```python
from .manager import ConnectionManager
from .channels import ChannelManager, users_channel, posts_channel, connection_manager

__all__ = ["ConnectionManager", "ChannelManager", "users_channel", "posts_channel", "connection_manager"]
```

## Paso 3: Crear el Servicio (app/services/post_service.py)

**¡Mira qué simple es con BaseService!**

```python
from sqlmodel import Session, select
from typing import List, Optional
from app.models.post import Post, PostCreate, PostUpdate, PostRead
from app.services.base_service import BaseService
from app.services.websocket import posts_channel


class PostService(BaseService[Post, PostCreate, PostUpdate, PostRead]):
    """
    Service layer for post operations.

    Inherits from BaseService to get automatic CRUD with WebSocket:
    - create() - Create post with broadcast
    - update() - Update post with broadcast
    - delete() - Delete post with broadcast
    - get_by_id() - Get post by ID
    - get_all() - Get all posts with pagination

    Add custom methods below if needed.
    """

    def __init__(self):
        """Initialize PostService with Post model and posts WebSocket channel."""
        super().__init__(
            model=Post,
            channel=posts_channel,
            read_schema=PostRead
        )

    def get_posts_by_user(self, session: Session, user_id: int) -> List[Post]:
        """Get all posts by a specific user"""
        statement = select(Post).where(Post.user_id == user_id)
        return list(session.exec(statement).all())


# Singleton instance
post_service = PostService()
```

**¡Eso es todo!** Solo 30 líneas y ya tienes:
- ✅ CRUD completo
- ✅ WebSocket en tiempo real
- ✅ Broadcast automático
- ✅ Type-safe con generics

## Paso 4: Crear las Rutas (app/routes/posts.py)

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models.post import PostCreate, PostRead, PostUpdate
from app.services.post_service import post_service

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/", response_model=List[PostRead])
def get_posts(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all posts with pagination"""
    posts = post_service.get_all(session, skip=skip, limit=limit)
    return posts


@router.get("/{post_id}", response_model=PostRead)
def get_post(
    post_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific post by ID"""
    post = post_service.get_by_id(session, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    return post


@router.get("/user/{user_id}", response_model=List[PostRead])
def get_posts_by_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Get all posts by a specific user"""
    posts = post_service.get_posts_by_user(session, user_id)
    return posts


@router.post("/", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new post and broadcast to WebSocket clients.

    Broadcast happens automatically via BaseService!
    """
    post = await post_service.create(session, post_data)
    return post


@router.patch("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    session: Session = Depends(get_session)
):
    """
    Update a post and broadcast to WebSocket clients.

    Broadcast happens automatically via BaseService!
    """
    post = await post_service.update(session, post_id, post_data)
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
    """
    Delete a post and broadcast to WebSocket clients.

    Broadcast happens automatically via BaseService!
    """
    deleted = await post_service.delete(session, post_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    return None
```

## Paso 5: Registrar Todo

### 5.1 Actualizar app/models/__init__.py

```python
from .user import User
from .post import Post

__all__ = ["User", "Post"]
```

### 5.2 Actualizar app/database/connection.py

```python
# Línea 24, importar el nuevo modelo
from app.models import User, Post  # noqa: F401
```

### 5.3 Agregar canal válido en app/routes/websocket.py

```python
# Línea ~30
valid_channels = ["users", "posts"]  # Agregar "posts"
```

### 5.4 Registrar router en main.py

```python
from app.routes.posts import router as posts_router

# ...

app.include_router(posts_router)
```

## Paso 6: Usar

### Reiniciar servidor

```bash
uv run python main.py
```

### Crear un post

```bash
curl -X POST "http://localhost:8000/posts/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mi primer post",
    "content": "Contenido del post",
    "user_id": 1
  }'
```

### Conectar WebSocket y ver actualizaciones en tiempo real

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/posts');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Post event:', data);

    switch(data.type) {
        case 'created':
            console.log('New post created:', data.data);
            break;
        case 'updated':
            console.log('Post updated:', data.data);
            break;
        case 'deleted':
            console.log('Post deleted:', data.data.id);
            break;
    }
};
```

## Comparación: Antes vs Después

### Antes (sin BaseService):

```python
class PostService:
    @staticmethod
    async def create_post(session, data, broadcast=True):
        post = Post(**data.model_dump())
        session.add(post)
        session.commit()
        session.refresh(post)

        if broadcast:
            from app.services.websocket import posts_channel
            post_dict = PostRead.model_validate(post).model_dump()
            await posts_channel.broadcast_created(post_dict)

        return post

    @staticmethod
    async def update_post(session, post_id, data, broadcast=True):
        post = session.get(Post, post_id)
        if not post:
            return None

        update_data = data.model_dump(exclude_unset=True)
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

    # ... más código repetitivo
```

**~100 líneas de código repetitivo**

### Después (con BaseService):

```python
class PostService(BaseService[Post, PostCreate, PostUpdate, PostRead]):
    def __init__(self):
        super().__init__(
            model=Post,
            channel=posts_channel,
            read_schema=PostRead
        )
```

**~10 líneas, sin código duplicado!**

## Ventajas del BaseService

1. **DRY (Don't Repeat Yourself)**: No duplicas código CRUD
2. **Type-Safe**: Generics de Python mantienen el tipado
3. **Consistencia**: Todos los servicios funcionan igual
4. **Mantenible**: Cambios en un lugar se reflejan en todos
5. **Extensible**: Agrega métodos personalizados fácilmente
6. **Broadcast Automático**: WebSocket incluido sin esfuerzo
7. **Rápido de Implementar**: Nuevos modelos en minutos

## Métodos Heredados de BaseService

Todos estos métodos están disponibles automáticamente:

| Método | Descripción | Broadcast |
|--------|-------------|-----------|
| `get_by_id(session, id)` | Obtener por ID | No |
| `get_all(session, skip, limit)` | Listar con paginación | No |
| `create(session, data, broadcast)` | Crear objeto | Sí* |
| `update(session, id, data, broadcast)` | Actualizar objeto | Sí* |
| `delete(session, id, broadcast)` | Eliminar objeto | Sí* |
| `count(session)` | Contar total | No |

*Configurable con parámetro `broadcast`

## Agregar Métodos Personalizados

Si necesitas métodos específicos, solo agrégalos en la clase hija:

```python
class PostService(BaseService[Post, PostCreate, PostUpdate, PostRead]):
    def __init__(self):
        super().__init__(...)

    # Método personalizado
    def get_popular_posts(self, session: Session, min_views: int = 100):
        statement = select(Post).where(Post.views >= min_views)
        return list(session.exec(statement).all())

    # Otro método personalizado
    def get_posts_by_tag(self, session: Session, tag: str):
        statement = select(Post).where(Post.tags.contains(tag))
        return list(session.exec(statement).all())
```

## ¡Eso es todo!

Con `BaseService` puedes agregar nuevos modelos con WebSocket en tiempo real en **menos de 10 minutos**.

No más código repetitivo, no más errores de copiar/pegar. Solo herencia limpia y elegante.
