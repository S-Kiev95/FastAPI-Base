# BaseService Architecture

## Resumen Ejecutivo

La plantilla ahora incluye un **`BaseService` genérico** que elimina completamente la duplicación de código CRUD, proporciona WebSocket broadcasting automático mediante herencia, y incluye un sistema de filtros avanzado heredado automáticamente.

## Problema Original

Antes, cada servicio requería duplicar ~100 líneas de código:

```python
class UserService:
    @staticmethod
    async def create_user(session, data, broadcast=True):
        # 20 líneas de código para crear
        # 10 líneas para broadcast

    @staticmethod
    async def update_user(session, id, data, broadcast=True):
        # 20 líneas de código para actualizar
        # 10 líneas para broadcast

    @staticmethod
    async def delete_user(session, id, broadcast=True):
        # 15 líneas de código para eliminar
        # 10 líneas para broadcast
```

**Problemas:**
- ❌ Código duplicado en cada servicio
- ❌ Fácil olvidar el broadcast
- ❌ Errores de copiar/pegar
- ❌ Difícil de mantener
- ❌ No escalable

## Solución: BaseService Genérico

### Arquitectura

```python
BaseService[ModelType, CreateSchema, UpdateSchema, ReadSchema]
    ↓
    Herencia
    ↓
UserService(BaseService[User, UserCreate, UserUpdate, UserRead])
PostService(BaseService[Post, PostCreate, PostUpdate, PostRead])
...cualquier otro servicio
```

### Implementación

#### 1. BaseService (app/services/base_service.py)

```python
from typing import Generic, TypeVar
from app.services.websocket.channels import ChannelManager

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)
ReadSchemaType = TypeVar("ReadSchemaType", bound=SQLModel)

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ReadSchemaType]):
    def __init__(self, model, channel, read_schema):
        self.model = model
        self.channel = channel
        self.read_schema = read_schema

    async def create(self, session, data, broadcast=True):
        obj = self.model(**data.model_dump())
        session.add(obj)
        session.commit()
        session.refresh(obj)

        if broadcast:
            obj_dict = self.read_schema.model_validate(obj).model_dump()
            await self.channel.broadcast_created(obj_dict)

        return obj

    # update(), delete(), get_by_id(), get_all()...
```

#### 2. Servicio Específico (app/services/user_service.py)

```python
class UserService(BaseService[User, UserCreate, UserUpdate, UserRead]):
    def __init__(self):
        super().__init__(
            model=User,
            channel=users_channel,
            read_schema=UserRead
        )

    # Solo métodos específicos de usuario
    def get_user_by_email(self, session, email):
        ...

# Singleton
user_service = UserService()
```

**¡Solo 10 líneas!** Y obtienes:
- ✅ `create()` con broadcast
- ✅ `update()` con broadcast
- ✅ `delete()` con broadcast
- ✅ `get_by_id()`
- ✅ `get_all()` con paginación
- ✅ `count()`
- ✅ `filter()` con filtros avanzados
- ✅ `filter_paginated()` con metadata
- ✅ `count_filtered()` para contar resultados

## Ventajas

### 1. DRY (Don't Repeat Yourself)
- Un solo lugar para la lógica CRUD
- Cambios se propagan automáticamente
- Sin código duplicado

### 2. Type-Safe
```python
user_service = UserService()
user = await user_service.create(...)  # Type: User
post = await post_service.create(...)   # Type: Post
```

Gracias a los generics de Python, el IDE conoce los tipos exactos.

### 3. Consistencia
Todos los servicios funcionan de la misma manera:
```python
await user_service.create(session, data)
await post_service.create(session, data)
await comment_service.create(session, data)
```

### 4. Extensible
Agrega métodos personalizados fácilmente:
```python
class PostService(BaseService[...]):
    def get_popular_posts(self, session, min_views=100):
        # Método específico de posts
        pass
```

### 5. Broadcast Automático
No necesitas recordar agregar código de WebSocket:
```python
# El broadcast ocurre automáticamente
user = await user_service.create(session, user_data)
```

### 6. Configurable
Puedes desactivar el broadcast cuando sea necesario:
```python
user = await user_service.create(session, data, broadcast=False)
```

### 7. Rápido de Implementar
Nuevo modelo en **5 minutos**:
1. Crear modelo y schemas
2. Crear canal WebSocket
3. Heredar de BaseService
4. ¡Listo!

## Comparación: Antes vs Después

| Aspecto | Antes | Después |
|---------|-------|---------|
| Líneas por servicio | ~100 | ~10 |
| Código duplicado | Sí | No |
| Type-safe | Parcial | Total |
| Broadcast automático | Manual | Automático |
| Tiempo implementación | 30 min | 5 min |
| Mantenimiento | Difícil | Fácil |
| Escalabilidad | Baja | Alta |

## Ejemplo Real: Agregar Modelo Post

### Antes (sin BaseService): ~100 líneas

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

    @staticmethod
    async def delete_post(session, post_id, broadcast=True):
        post = session.get(Post, post_id)
        if not post:
            return False

        session.delete(post)
        session.commit()

        if broadcast:
            from app.services.websocket import posts_channel
            await posts_channel.broadcast_deleted(post_id)

        return True

    @staticmethod
    def get_post_by_id(session, post_id):
        return session.get(Post, post_id)

    @staticmethod
    def get_all_posts(session, skip=0, limit=100):
        statement = select(Post).offset(skip).limit(limit)
        return list(session.exec(statement).all())
```

### Después (con BaseService): ~15 líneas

```python
from app.services.base_service import BaseService
from app.services.websocket import posts_channel

class PostService(BaseService[Post, PostCreate, PostUpdate, PostRead]):
    def __init__(self):
        super().__init__(
            model=Post,
            channel=posts_channel,
            read_schema=PostRead
        )

post_service = PostService()
```

**Reducción de código: ~85%**

## Métodos Heredados Automáticamente

| Método | Firma | Broadcast | Descripción |
|--------|-------|-----------|-------------|
| `get_by_id` | `(session, id)` | No | Obtener por ID |
| `get_all` | `(session, skip, limit)` | No | Listar con paginación |
| `create` | `(session, data, broadcast)` | Sí* | Crear objeto |
| `update` | `(session, id, data, broadcast)` | Sí* | Actualizar objeto |
| `delete` | `(session, id, broadcast)` | Sí* | Eliminar objeto |
| `count` | `(session)` | No | Contar total |
| `filter` | `(session, filters)` | No | Filtrar con condiciones |
| `filter_paginated` | `(session, filters)` | No | Filtrar con metadata |
| `count_filtered` | `(session, filters)` | No | Contar resultados filtrados |

*Configurable con parámetro `broadcast=True/False`

## Uso en Rutas

```python
from app.services.user_service import user_service

@router.post("/")
async def create_user(data: UserCreate, session: Session = Depends(get_session)):
    user = await user_service.create(session, data)
    return user

@router.patch("/{user_id}")
async def update_user(user_id: int, data: UserUpdate, session: Session = Depends(get_session)):
    user = await user_service.update(session, user_id, data)
    if not user:
        raise HTTPException(404)
    return user
```

## Características Técnicas

### Generics de Python
```python
class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ReadSchemaType]):
    ...
```

Los generics proporcionan:
- Type hints correctos
- Autocompletado en IDE
- Validación estática con mypy
- Documentación clara

### Patrón Singleton
```python
user_service = UserService()  # Instancia única
```

Ventajas:
- Estado compartido
- Fácil importación
- Mejor performance

### Inyección de Dependencias
```python
def __init__(self, model, channel, read_schema):
    self.model = model
    self.channel = channel
    self.read_schema = read_schema
```

Facilita:
- Testing con mocks
- Cambiar implementaciones
- Flexibilidad

## Testing

Con `BaseService` es más fácil testear:

```python
class MockChannel:
    async def broadcast_created(self, data):
        self.last_broadcast = data

def test_create_user():
    mock_channel = MockChannel()
    service = UserService()
    service.channel = mock_channel

    user = await service.create(session, user_data)

    assert user.id is not None
    assert mock_channel.last_broadcast == {...}
```

## Migración

Si tienes servicios existentes, la migración es simple:

1. Mantén métodos personalizados
2. Cambia la clase base
3. Elimina métodos CRUD duplicados
4. Actualiza las rutas para usar la instancia singleton

```python
# Antes
class UserService:
    @staticmethod
    async def create_user(...):
        ...

# Después
class UserService(BaseService[User, UserCreate, UserUpdate, UserRead]):
    def __init__(self):
        super().__init__(...)
```

## Conclusión

`BaseService` transforma la plantilla de:
- ❌ 100 líneas de código repetitivo por modelo
- ❌ Fácil olvidar broadcasts
- ❌ Difícil de mantener

A:
- ✅ 10 líneas de código limpio
- ✅ Broadcast automático
- ✅ Fácil de extender
- ✅ Type-safe
- ✅ Nuevos modelos en 5 minutos

**Es la diferencia entre código profesional y código enterprise-grade.**

## Referencias

- Ver código: [app/services/base_service.py](app/services/base_service.py)
- Ver filtros: [app/services/filters.py](app/services/filters.py)
- Ver ejemplo: [app/services/user_service.py](app/services/user_service.py)
- Tutorial completo: [EXAMPLE_POST_MODEL.md](EXAMPLE_POST_MODEL.md)
- Guía de filtros: [FILTERING_GUIDE.md](FILTERING_GUIDE.md)
- Python Generics: https://docs.python.org/3/library/typing.html#generics
