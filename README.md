# FastAPI Base Template

Plantilla base de FastAPI con estructura estándar, SQLModel, autenticación OAuth, **WebSocket en tiempo real** y **almacenamiento multimedia S3/MinIO**.

## Estructura del Proyecto

```
fastapi_base/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuración y variables de entorno
│   ├── models/                # Modelos de base de datos
│   │   ├── __init__.py
│   │   └── user.py           # Modelo de usuario con OAuth
│   ├── database/              # Configuración de base de datos
│   │   ├── __init__.py
│   │   └── connection.py     # Engine y sesiones
│   ├── services/              # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── base_service.py   # Servicio genérico base
│   │   ├── filters.py        # Sistema de filtros avanzados
│   │   ├── user_service.py   # Servicios de usuario
│   │   ├── media_service.py  # Servicios de multimedia
│   │   ├── storage_service.py # Almacenamiento S3/Local
│   │   └── websocket/         # Sistema WebSocket
│   │       ├── __init__.py
│   │       ├── manager.py    # Gestor de conexiones
│   │       └── channels.py   # Canales por modelo
│   ├── routes/                # Endpoints de la API
│   │   ├── __init__.py
│   │   ├── users.py          # Rutas de usuarios
│   │   ├── media.py          # Rutas de multimedia
│   │   └── websocket.py      # Rutas WebSocket
│   └── static/                # Archivos estáticos
│       └── websocket-test.html # Cliente de prueba WebSocket
├── main.py                    # Punto de entrada de la aplicación
├── .env                       # Variables de entorno (no subir a git)
├── .env.example              # Ejemplo de variables de entorno
├── .gitignore
├── pyproject.toml
├── README.md                  # Este archivo
├── WEBSOCKET_GUIDE.md        # Guía completa de WebSocket
└── OAUTH_SETUP.md            # Guía de OAuth
```

## Características

- **FastAPI**: Framework moderno y rápido para construir APIs
- **SQLModel**: ORM basado en Pydantic y SQLAlchemy
- **WebSocket Real-time**: Sistema completo de actualizaciones en tiempo real con canales por modelo
- **Webhooks**: Sistema completo de webhooks con HMAC signatures, retries y logging
- **Sistema de Colas (ARQ)**: Procesamiento asíncrono de tareas (media, emails, webhooks)
- **Rate Limiting**: Protección contra abuso con límites configurables por endpoint
- **Structured Logging**: Logs estructurados JSON con request IDs y contextos
- **BaseService Genérico**: CRUD con WebSocket automático mediante herencia - agrega nuevos modelos en minutos
- **Sistema de Filtros Avanzado**: Filtrado, ordenamiento y paginación heredados automáticamente en todos los servicios
- **Almacenamiento Multimedia**: Soporte para S3/MinIO y filesystem local con cambio automático según configuración
- **Estructura modular**: Separación clara de modelos, servicios y rutas
- **OAuth Ready**: Modelo de usuario preparado para proveedores OAuth (Google, etc.)
- **Variables de entorno**: Configuración mediante archivo .env
- **Startup inteligente**: Verifica y crea la base de datos automáticamente
- **Documentación automática**: Swagger UI en /docs y ReDoc en /redoc
- **Cliente HTML de prueba**: Interfaz interactiva para probar WebSocket

## Instalación

1. Clonar el repositorio:
```bash
git clone <tu-repo>
cd fastapi_base
```

2. Instalar dependencias con uv:
```bash
uv sync
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

## Uso

### Iniciar el servidor de desarrollo:

```bash
# Con uv
uv run python main.py

# O directamente
python main.py

# O usando el script configurado
uv run start
```

El servidor estará disponible en http://localhost:8000

### Endpoints disponibles:

- **GET /** - Página de bienvenida
- **GET /health** - Health check
- **GET /docs** - Documentación Swagger UI
- **GET /redoc** - Documentación ReDoc
- **GET /static/websocket-test.html** - Cliente de prueba WebSocket interactivo

#### Endpoints de usuarios:

- **GET /users/** - Obtener todos los usuarios (con paginación)
- **GET /users/{user_id}** - Obtener usuario por ID
- **GET /users/email/{email}** - Obtener usuario por email
- **POST /users/** - Crear nuevo usuario (con broadcast WebSocket)
- **PATCH /users/{user_id}** - Actualizar usuario (con broadcast WebSocket)
- **DELETE /users/{user_id}** - Eliminar usuario (con broadcast WebSocket)
- **POST /users/filter** - Filtrar usuarios con consultas avanzadas
- **POST /users/filter/paginated** - Filtrar usuarios con metadata de paginación

#### Endpoints WebSocket:

- **WS /ws/{channel}** - Conectar a un canal WebSocket
- **GET /ws/stats** - Obtener estadísticas de conexiones

### Ejemplo de uso con curl:

```bash
# Crear un usuario
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "provider_user_id": "123456789",
    "email": "user@example.com",
    "name": "John Doe",
    "picture": "https://example.com/photo.jpg"
  }'

# Obtener todos los usuarios
curl http://localhost:8000/users/

# Obtener usuario por ID
curl http://localhost:8000/users/1

# Filtrar usuarios con Gmail
curl -X POST "http://localhost:8000/users/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {"field": "email", "operator": "icontains", "value": "gmail"},
      {"field": "is_active", "operator": "eq", "value": true}
    ],
    "operator": "and",
    "order_by": "created_at",
    "order_direction": "desc",
    "limit": 10
  }'
```

## Sistema de Filtros Avanzado

Todos los servicios que heredan de `BaseService` incluyen automáticamente capacidades de filtrado avanzado sin necesidad de código adicional.

### Ejemplo Rápido

```python
from app.services.filters import QueryFilter, Condition, FilterOperator

# Filtrar usuarios activos con Gmail
filters = QueryFilter(
    conditions=[
        Condition(field="email", operator=FilterOperator.ICONTAINS, value="gmail"),
        Condition(field="is_active", operator=FilterOperator.EQ, value=True)
    ],
    operator="and",
    order_by="created_at",
    order_direction="desc",
    limit=10
)

# Filtrar
users = user_service.filter(session, filters)

# O con metadata de paginación
result = user_service.filter_paginated(session, filters)
# Retorna: {data: [...], total: 150, limit: 10, offset: 0, has_more: True}
```

### Operadores Disponibles

- **Comparación**: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`
- **Texto**: `contains`, `icontains`, `startswith`, `endswith`
- **Listas**: `in`, `not_in`
- **Nulos**: `is_null`, `is_not_null`

### Características

- ✅ Filtrado con múltiples condiciones (AND/OR)
- ✅ Grupos de condiciones anidadas
- ✅ Ordenamiento por cualquier campo
- ✅ Paginación con metadata (total, has_more)
- ✅ Validación automática con Pydantic
- ✅ Heredado automáticamente en todos los servicios

Ver [FILTERING_GUIDE.md](FILTERING_GUIDE.md) para documentación completa con ejemplos en JavaScript, React y más.

## WebSocket en Tiempo Real

### Conectar al WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/users');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);

    switch(data.type) {
        case 'created':
            console.log('New user:', data.data);
            break;
        case 'updated':
            console.log('Updated user:', data.data);
            break;
        case 'deleted':
            console.log('Deleted user ID:', data.data.id);
            break;
    }
};
```

### Cliente HTML Interactivo

Visita http://localhost:8000/static/websocket-test.html para ver una interfaz completa que te permite:

- Conectar/desconectar de canales WebSocket
- Ver eventos en tiempo real con timestamps
- Crear usuarios y ver actualizaciones instantáneas
- Ver estadísticas de conexiones activas
- Probar ping/pong y otros comandos

### Guía Completa

Para documentación completa de WebSocket, ver [WEBSOCKET_GUIDE.md](WEBSOCKET_GUIDE.md)

## Modelo de Usuario

El modelo de usuario está diseñado para trabajar con proveedores OAuth:

```python
User:
  - id: int (primary key)
  - provider: str (e.g., "google", "github")
  - provider_user_id: str (unique)
  - email: str (unique)
  - name: str (optional)
  - picture: str (optional, URL del avatar)
  - is_active: bool
  - is_verified: bool
  - created_at: datetime
  - updated_at: datetime
  - last_login: datetime (optional)
```

## Configuración de Base de Datos

Por defecto usa SQLite (`sqlite:///./app.db`), pero puedes cambiar a PostgreSQL o MySQL modificando la variable `DATABASE_URL` en el archivo `.env`:

```env
# SQLite (por defecto)
DATABASE_URL=sqlite:///./app.db

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/dbname

# MySQL
DATABASE_URL=mysql://user:password@localhost/dbname
```

## Agregar Nuevos Modelos con WebSocket (Súper Fácil!)

Gracias al `BaseService` genérico, agregar nuevos modelos con CRUD completo y WebSocket toma **menos de 10 minutos**:

### 1. Crear el Modelo

```python
# app/models/post.py
from sqlmodel import Field, SQLModel

class Post(SQLModel, table=True):
    __tablename__ = "posts"
    id: int = Field(primary_key=True)
    title: str
    content: str

class PostCreate(SQLModel):
    title: str
    content: str

class PostRead(SQLModel):
    id: int
    title: str
    content: str

class PostUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
```

### 2. Crear el Canal WebSocket

```python
# app/services/websocket/channels.py (al final)
posts_channel = ChannelManager(connection_manager, "posts")
```

### 3. Crear el Servicio (¡Solo 10 líneas!)

```python
# app/services/post_service.py
from app.services.base_service import BaseService
from app.services.websocket import posts_channel
from app.models.post import Post, PostCreate, PostUpdate, PostRead

class PostService(BaseService[Post, PostCreate, PostUpdate, PostRead]):
    def __init__(self):
        super().__init__(
            model=Post,
            channel=posts_channel,
            read_schema=PostRead
        )

# Singleton
post_service = PostService()
```

**¡Eso es todo!** Ya tienes:
- ✅ `create()` con broadcast
- ✅ `update()` con broadcast
- ✅ `delete()` con broadcast
- ✅ `get_by_id()`
- ✅ `get_all()` con paginación
- ✅ Type-safe con generics

### 4. Crear las Rutas

```python
# app/routes/posts.py
from app.services.post_service import post_service

@router.post("/")
async def create_post(data: PostCreate, session: Session = Depends(get_session)):
    return await post_service.create(session, data)  # ¡Broadcast automático!
```

### 5. Registrar

- Importar modelo en `app/database/connection.py`
- Agregar canal en `app/routes/websocket.py`
- Registrar router en `main.py`

Ver [EXAMPLE_POST_MODEL.md](EXAMPLE_POST_MODEL.md) para tutorial completo paso a paso.

## Variables de Entorno

Archivo `.env`:

```env
# Database
DATABASE_URL=sqlite:///./app.db

# API
API_TITLE=FastAPI Base Template
API_VERSION=1.0.0
API_DESCRIPTION=FastAPI template with SQLModel and authentication

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=True

# Security
SECRET_KEY=your-secret-key-here-change-in-production

# OAuth (opcional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Storage Configuration (S3/MinIO)
USE_S3=False
S3_ENDPOINT_URL=http://localhost:9000  # MinIO endpoint
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET_NAME=media
S3_REGION=us-east-1

# Local storage (usado cuando USE_S3=False)
MEDIA_FOLDER=./media
MAX_FILE_SIZE=10485760  # 10MB
```

## Desarrollo

### Estructura recomendada para nuevas features:

1. **Modelo**: Define en `app/models/` con schemas (Create, Read, Update)
2. **Canal WebSocket**: Crea en `app/services/websocket/channels.py`
3. **Servicio**: Hereda de `BaseService` - ¡broadcast automático!
4. **Rutas**: Endpoints async que usan el servicio
5. **Registrar**: Importar modelo, agregar canal válido, registrar router

### Ejemplo de nueva ruta con WebSocket:

```python
# app/routes/items.py
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.database import get_session
from app.services.item_service import ItemService

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/")
async def create_item(
    item_data: ItemCreate,
    session: Session = Depends(get_session)
):
    # Automáticamente hace broadcast al canal de items
    item = await ItemService.create_item(session, item_data)
    return item
```

```python
# main.py
from app.routes import items_router
app.include_router(items_router)
```

## Documentación Adicional

Toda la documentación técnica ha sido movida a la carpeta `docs/` para mejor organización:

### Guías del Sistema

- **[docs/WEBHOOKS.md](docs/WEBHOOKS.md)** - Sistema completo de webhooks para integraciones externas
- **[docs/RATE_LIMITING.md](docs/RATE_LIMITING.md)** - Protección contra abuso con rate limiting
- **[docs/LOGGING.md](docs/LOGGING.md)** - Logging estructurado con request IDs y contextos

### Guías de Desarrollo

- [EXAMPLE_POST_MODEL.md](EXAMPLE_POST_MODEL.md) - **Tutorial completo**: Cómo agregar un modelo Post con BaseService (paso a paso)
- [BASE_SERVICE_ARCHITECTURE.md](BASE_SERVICE_ARCHITECTURE.md) - Arquitectura del BaseService genérico
- [FILTERING_GUIDE.md](FILTERING_GUIDE.md) - **Guía completa de filtros**: Consultas avanzadas con operadores, paginación y ordenamiento
- [MEDIA_STORAGE_GUIDE.md](MEDIA_STORAGE_GUIDE.md) - **Guía de almacenamiento**: S3/MinIO y almacenamiento local para multimedia
- [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md) - **Guía de migraciones**: Alembic para PostgreSQL y control de esquema de BD
- [WEBSOCKET_GUIDE.md](WEBSOCKET_GUIDE.md) - Guía completa de WebSocket con ejemplos en React, Vue y JavaScript
- [OAUTH_SETUP.md](OAUTH_SETUP.md) - Configuración de OAuth con Google, GitHub y otros proveedores
- [QUICKSTART.md](QUICKSTART.md) - Guía de inicio rápido en 5 minutos
- [examples.http](examples.http) - Ejemplos de peticiones HTTP

## Arquitectura WebSocket

```
┌─────────────┐
│   Cliente   │
└──────┬──────┘
       │ ws://localhost:8000/ws/users
       ↓
┌──────────────────────────────┐
│  ConnectionManager (Global)   │
│  - Maneja múltiples canales   │
│  - users, posts, etc.         │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────┐
│  ChannelManager (por modelo)  │
│  - broadcast_created()        │
│  - broadcast_updated()        │
│  - broadcast_deleted()        │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────┐
│   UserService                 │
│   - create_user() →           │
│     ↳ broadcast_created       │
│   - update_user() →           │
│     ↳ broadcast_updated       │
│   - delete_user() →           │
│     ↳ broadcast_deleted       │
└──────────────────────────────┘
```

## Testing

Para probar la funcionalidad completa:

1. Inicia el servidor: `uv run python main.py`
2. Abre el cliente HTML: http://localhost:8000/static/websocket-test.html
3. Haz clic en "Connect" para conectarte al canal de usuarios
4. Crea usuarios desde la interfaz y observa las actualizaciones en tiempo real
5. Abre múltiples pestañas del navegador para ver el broadcast en acción

## Licencia

MIT
