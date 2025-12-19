# WebSocket Real-time Guide

Esta plantilla incluye soporte completo para WebSocket con canales por modelo, permitiendo actualizaciones en tiempo real.

## Arquitectura

### Estructura de WebSocket

```
app/
├── services/
│   └── websocket/
│       ├── manager.py      # ConnectionManager genérico
│       └── channels.py     # Canales por modelo (users, posts, etc.)
└── routes/
    └── websocket.py        # Endpoints WebSocket
```

### Componentes

1. **ConnectionManager**: Gestor genérico de conexiones WebSocket
   - Maneja múltiples canales
   - Conecta/desconecta clientes
   - Broadcast a canales específicos o todos

2. **ChannelManager**: Gestor específico por modelo
   - Wrapper sobre ConnectionManager
   - Métodos específicos: `broadcast_created`, `broadcast_updated`, `broadcast_deleted`
   - Un canal por modelo

3. **Integration en Services**: Los servicios automáticamente hacen broadcast
   - `create_user` → broadcast_created
   - `update_user` → broadcast_updated
   - `delete_user` → broadcast_deleted

## Uso Básico

### Conectar al WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/users');

ws.onopen = () => {
    console.log('Connected to users channel');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);

    // Handle different event types
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

ws.onclose = () => {
    console.log('Disconnected');
};
```

### Con Client ID personalizado

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/users?client_id=my-unique-id');
```

### Formato de Mensajes

#### Mensaje de Conexión
```json
{
    "type": "connection",
    "message": "Connected to channel: users",
    "channel": "users",
    "client_id": "uuid-here",
    "timestamp": "2025-12-04T10:00:00.000000"
}
```

#### Evento Created
```json
{
    "type": "created",
    "model": "users",
    "channel": "users",
    "timestamp": "2025-12-04T10:00:00.000000",
    "data": {
        "id": 1,
        "email": "user@example.com",
        "name": "John Doe",
        "is_active": true,
        "created_at": "2025-12-04T10:00:00.000000"
    }
}
```

#### Evento Updated
```json
{
    "type": "updated",
    "model": "users",
    "channel": "users",
    "timestamp": "2025-12-04T10:00:00.000000",
    "data": {
        "id": 1,
        "email": "user@example.com",
        "name": "John Updated",
        "is_active": true,
        "created_at": "2025-12-04T10:00:00.000000"
    }
}
```

#### Evento Deleted
```json
{
    "type": "deleted",
    "model": "users",
    "channel": "users",
    "timestamp": "2025-12-04T10:00:00.000000",
    "data": {
        "id": 1
    }
}
```

### Enviar Mensajes al Servidor

#### Ping/Pong
```javascript
ws.send(JSON.stringify({ type: 'ping' }));
// Respuesta: { "type": "pong", "message": "pong" }
```

#### Obtener Estadísticas
```javascript
ws.send(JSON.stringify({ type: 'get_stats' }));
// Respuesta:
// {
//     "type": "stats",
//     "data": {
//         "total_channels": 1,
//         "channels": { "users": 3 },
//         "total_connections": 3
//     }
// }
```

## Agregar Nuevos Canales

### 1. Crear el Canal en channels.py

```python
# app/services/websocket/channels.py

# Importar al inicio
from .manager import ConnectionManager, connection_manager

# Agregar al final del archivo
posts_channel = ChannelManager(connection_manager, "posts")
```

### 2. Exportar el Canal

```python
# app/services/websocket/__init__.py

from .manager import ConnectionManager
from .channels import ChannelManager, users_channel, posts_channel

__all__ = ["ConnectionManager", "ChannelManager", "users_channel", "posts_channel"]
```

### 3. Agregar Canal a la Ruta WebSocket

```python
# app/routes/websocket.py

# En la función websocket_endpoint, actualizar valid_channels
valid_channels = ["users", "posts"]  # Agregar tu nuevo canal
```

### 4. Integrar en el Servicio

```python
# app/services/post_service.py

from app.services.websocket import posts_channel
from app.models.post import Post, PostCreate, PostRead

class PostService:
    @staticmethod
    async def create_post(session: Session, post_data: PostCreate, broadcast: bool = True) -> Post:
        post = Post(**post_data.model_dump())
        session.add(post)
        session.commit()
        session.refresh(post)

        if broadcast:
            post_dict = PostRead.model_validate(post).model_dump()
            await posts_channel.broadcast_created(post_dict)

        return post

    @staticmethod
    async def update_post(session: Session, post_id: int, post_data: PostUpdate, broadcast: bool = True) -> Optional[Post]:
        post = session.get(Post, post_id)
        if not post:
            return None

        update_data = post_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(post, key, value)

        session.add(post)
        session.commit()
        session.refresh(post)

        if broadcast:
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
            await posts_channel.broadcast_deleted(post_id)

        return True
```

### 5. Actualizar las Rutas

```python
# app/routes/posts.py

@router.post("/", response_model=PostRead)
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
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    session: Session = Depends(get_session)
):
    deleted = await PostService.delete_post(session, post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted"}
```

## Cliente HTML de Prueba

Accede a http://localhost:8000/static/websocket-test.html para ver una interfaz interactiva que te permite:

- Conectar/desconectar de canales
- Ver eventos en tiempo real
- Crear usuarios y ver las actualizaciones instantáneas
- Ver estadísticas de conexiones
- Enviar ping/pong

## Endpoints HTTP para WebSocket

### GET /ws/stats

Obtener estadísticas de conexiones WebSocket:

```bash
curl http://localhost:8000/ws/stats
```

Respuesta:
```json
{
    "total_channels": 1,
    "channels": {
        "users": 3
    },
    "total_connections": 3
}
```

## Características Avanzadas

### Desactivar Broadcast en Operaciones Específicas

Si necesitas crear/actualizar/eliminar sin hacer broadcast:

```python
# No hará broadcast
user = await UserService.create_user(session, user_data, broadcast=False)
```

### Broadcast Personalizado

Puedes enviar eventos personalizados desde cualquier lugar:

```python
from app.services.websocket import users_channel

await users_channel.broadcast_custom(
    "user_login",
    {"user_id": 123, "timestamp": "2025-12-04T10:00:00"}
)
```

### Excluir Cliente del Broadcast

Útil para no enviar el evento al cliente que lo originó:

```python
await users_channel.broadcast_created(user_dict, exclude_client="client-123")
```

### Broadcast a Todos los Canales

```python
from app.services.websocket import connection_manager

await connection_manager.broadcast_to_all_channels({
    "type": "maintenance",
    "message": "Server will restart in 5 minutes"
})
```

## Ejemplo React

```jsx
import { useEffect, useState } from 'react';

function UsersRealtime() {
    const [users, setUsers] = useState([]);
    const [ws, setWs] = useState(null);

    useEffect(() => {
        // Connect to WebSocket
        const websocket = new WebSocket('ws://localhost:8000/ws/users');

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch(data.type) {
                case 'created':
                    setUsers(prev => [...prev, data.data]);
                    break;
                case 'updated':
                    setUsers(prev => prev.map(u =>
                        u.id === data.data.id ? data.data : u
                    ));
                    break;
                case 'deleted':
                    setUsers(prev => prev.filter(u => u.id !== data.data.id));
                    break;
            }
        };

        setWs(websocket);

        // Load initial users
        fetch('http://localhost:8000/users/')
            .then(res => res.json())
            .then(data => setUsers(data));

        return () => websocket.close();
    }, []);

    return (
        <div>
            <h2>Users (Real-time)</h2>
            {users.map(user => (
                <div key={user.id}>
                    {user.name} - {user.email}
                </div>
            ))}
        </div>
    );
}
```

## Ejemplo Vue

```vue
<template>
    <div>
        <h2>Users (Real-time)</h2>
        <div v-for="user in users" :key="user.id">
            {{ user.name }} - {{ user.email }}
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const users = ref([]);
let ws = null;

onMounted(async () => {
    // Connect to WebSocket
    ws = new WebSocket('ws://localhost:8000/ws/users');

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch(data.type) {
            case 'created':
                users.value.push(data.data);
                break;
            case 'updated':
                const index = users.value.findIndex(u => u.id === data.data.id);
                if (index !== -1) {
                    users.value[index] = data.data;
                }
                break;
            case 'deleted':
                users.value = users.value.filter(u => u.id !== data.data.id);
                break;
        }
    };

    // Load initial users
    const response = await fetch('http://localhost:8000/users/');
    users.value = await response.json();
});

onUnmounted(() => {
    if (ws) ws.close();
});
</script>
```

## Seguridad

Para producción, considera:

1. **Autenticación en WebSocket**:
```python
@router.websocket("/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str,
    token: str = Query(...),  # Require auth token
):
    # Validate token
    user = await validate_token(token)
    if not user:
        await websocket.close(code=1008, reason="Invalid authentication")
        return
    # Continue with connection...
```

2. **Rate Limiting**: Limitar número de conexiones por usuario

3. **CORS**: Configurar orígenes permitidos en producción

4. **WSS**: Usar WebSocket Secure (wss://) en producción

## Troubleshooting

### WebSocket no conecta

1. Verifica que el servidor esté corriendo
2. Verifica la URL (ws:// no http://)
3. Verifica el canal en valid_channels
4. Revisa la consola del navegador para errores

### No se reciben eventos

1. Verifica que el servicio tenga `broadcast=True`
2. Verifica que estés conectado al canal correcto
3. Revisa los logs del servidor

### Conexión se cierra inesperadamente

1. Implementa reconexión automática en el cliente
2. Verifica logs del servidor para errores
3. Implementa heartbeat (ping/pong) para mantener conexión viva

## Referencias

- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket API MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
