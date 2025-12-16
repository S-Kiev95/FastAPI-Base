# Sistema de Colas con ARQ

Sistema de procesamiento asíncrono de tareas usando **ARQ** (Async Redis Queue) con notificaciones en tiempo real vía WebSocket.

## 📋 Tabla de Contenidos

1. [Qué es y para qué sirve](#qué-es-y-para-qué-sirve)
2. [Arquitectura](#arquitectura)
3. [Casos de Uso](#casos-de-uso)
4. [Cómo Funciona](#cómo-funciona)
5. [Uso desde el Frontend](#uso-desde-el-frontend)
6. [Uso desde el Backend](#uso-desde-el-backend)
7. [Iniciar Workers](#iniciar-workers)
8. [Monitoreo](#monitoreo)

---

## Qué es y para qué sirve

El sistema de colas permite **ejecutar tareas pesadas en segundo plano** sin bloquear el API.

### Problemas que resuelve:

❌ **Sin cola:**
```
POST /media/upload + procesar imagen
→ Usuario espera 30 segundos ⏳
→ Request timeout si tarda mucho 💥
→ Server bloqueado 🚫
```

✅ **Con cola:**
```
POST /media/upload
→ Retorna 202 Accepted en 500ms ⚡
→ Tarea procesada en background 🔄
→ Usuario recibe notificación cuando termina 🔔
```

---

## Arquitectura

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Frontend   │────┬─>│   FastAPI   │──────>│    Redis    │──────>│   Workers   │
│  (Browser)  │    │  │  (Producer) │       │   (Queue)   │       │ (Consumers) │
└─────────────┘    │  └─────────────┘       └─────────────┘       └─────────────┘
      ▲            │         │                      │                      │
      │            │         │                      │                      │
      │            │         ▼                      ▼                      ▼
      │            │  ┌─────────────┐       [task1, task2]        Procesa tareas
      │            │  │  PostgreSQL │         task3, task4         Publica eventos
      │            │  │   (Estado)  │
      │            │  └─────────────┘
      │            │
      │            │  WebSocket (tiempo real)
      └────────────┘
```

### Componentes:

1. **FastAPI (Producer)**: Recibe requests y encola tareas
2. **Redis (Queue)**: Almacena tareas pendientes
3. **Workers (Consumers)**: Procesan tareas en background
4. **PostgreSQL**: Guarda estado de tareas (opcional)
5. **WebSocket**: Notifica al frontend en tiempo real

---

## Casos de Uso

### 1. Procesamiento de Media 🖼️

**Tareas disponibles:**
- `generate_thumbnail`: Generar thumbnails de imágenes
- `optimize_image`: Comprimir y optimizar imágenes
- `process_media`: Pipeline completo (thumbnail + optimización)

**Ejemplo:**
```python
# Usuario sube imagen de 10MB
POST /media/upload
→ Guardar archivo (500ms)
→ Encolar: "process_media" (10ms)
→ Retornar 202 Accepted

# Worker procesa:
- Generar thumbnail 300x300
- Optimizar imagen (reducir 70% tamaño)
- Notificar vía WebSocket: "¡Listo!"
```

### 2. Envío de Emails 📧

**Tareas disponibles:**
- `send_single_email`: Enviar un email
- `send_bulk_emails`: Enviar múltiples emails con rate limiting

**Ejemplo:**
```python
# Admin envía newsletter a 10,000 usuarios
POST /tasks/email/bulk
{
  "emails": [...10,000 emails...],
  "rate_limit": 10  # 10 emails/minuto
}

# Worker procesa:
- Envía 10 emails/minuto (evita ban de SMTP)
- Notifica progreso: "450 / 10,000 enviados"
- Total: ~16 horas de forma controlada
```

---

## Cómo Funciona

### Flujo completo:

```
1. Frontend envía request
   POST /tasks/media/process
   {
     "media_id": 123,
     "file_path": "/media/image.jpg"
   }

2. Backend encola tarea
   → Retorna 202 Accepted
   {
     "task_id": "abc123",
     "message": "Task enqueued"
   }

3. Frontend conecta WebSocket
   ws://localhost:8001/ws/media?client_id=user1

4. Worker procesa tarea
   → Progress: 10%, 30%, 60%, 100%
   → Publica eventos a Redis Pub/Sub

5. Backend escucha Redis Pub/Sub
   → Reenvía eventos por WebSocket

6. Frontend recibe notificaciones
   {
     "type": "task_notification",
     "event": "thumbnail_generated",
     "data": {...}
   }
```

---

## Uso desde el Frontend

### 1. Encolar tarea

```javascript
// Procesar imagen
const response = await fetch('/tasks/media/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    media_id: 123,
    file_path: '/media/image.jpg',
    operations: ['thumbnail', 'optimize']
  })
});

const { task_id } = await response.json();
console.log('Task enqueued:', task_id);
```

### 2. Conectar WebSocket para notificaciones

```javascript
// Conectar a canal de media
const ws = new WebSocket('ws://localhost:8001/ws/media?client_id=user1');

// Escuchar notificaciones
ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);

  if (notification.type === 'task_notification') {
    console.log('Event:', notification.event);
    console.log('Data:', notification.data);

    // Ejemplo: thumbnail generado
    if (notification.event === 'thumbnail_generated') {
      const { thumbnail_path } = notification.data;
      updateUI(thumbnail_path);
    }
  }
};
```

### 3. Consultar estado de tarea (opcional)

```javascript
// Si WebSocket falla, usar polling
async function checkTaskStatus(task_id) {
  const response = await fetch(`/tasks/${task_id}/status`);
  const status = await response.json();

  console.log('Status:', status.status);  // pending, processing, completed
  console.log('Progress:', status.progress);  // 0-100

  return status;
}

// Polling cada 2 segundos
const interval = setInterval(async () => {
  const status = await checkTaskStatus('abc123');

  if (status.status === 'completed') {
    clearInterval(interval);
    console.log('Task completed!');
  }
}, 2000);
```

---

## Uso desde el Backend

### 1. Encolar tarea manualmente

```python
from app.services.queue_service import queue_service

# En cualquier endpoint
@app.post("/media/upload")
async def upload_media(file: UploadFile):
    # Guardar archivo
    file_path = save_file(file)

    # Encolar procesamiento
    task_id = await queue_service.enqueue_media_processing(
        media_id=123,
        file_path=file_path,
        operations=['thumbnail', 'optimize']
    )

    return {"task_id": task_id, "message": "Processing started"}
```

### 2. Crear nuevas tareas

```python
# app/workers/custom_tasks.py

async def my_custom_task(
    ctx: Dict[str, Any],
    param1: str,
    param2: int
) -> Dict[str, Any]:
    """
    Mi tarea personalizada

    Args:
        ctx: ARQ context (incluye redis, job_id)
        param1: Parámetro personalizado
        param2: Otro parámetro
    """
    print(f"Processing: {param1}, {param2}")

    # Tu lógica aquí
    result = {"status": "success", "data": "..."}

    # Publicar notificación (opcional)
    await ctx['redis'].publish(
        f"task_notifications:{param2}",
        str({"event": "task_completed", "data": result})
    )

    return result
```

### 3. Registrar tarea en worker

```python
# app/workers/worker_config.py

from app.workers.custom_tasks import my_custom_task

class WorkerSettings:
    functions = [
        # Tareas existentes
        generate_thumbnail,
        optimize_image,

        # Tu nueva tarea
        my_custom_task,
    ]
```

---

## Iniciar Workers

### Opción 1: Con Docker (Recomendado)

```bash
# Iniciar todos los servicios (incluye workers)
docker-compose -f docker-compose.dev.yml up -d

# Ver logs de workers
docker-compose -f docker-compose.dev.yml logs -f worker-media
docker-compose -f docker-compose.dev.yml logs -f worker-email
```

### Opción 2: Local (Desarrollo)

```bash
# Terminal 1: Iniciar worker
uv run arq app.workers.worker_config.WorkerSettings

# Terminal 2: Iniciar FastAPI
uv run uvicorn main:app --reload

# Terminal 3: Ver logs de Redis (opcional)
docker logs -f fastapi_redis_dev
```

### Escalar workers

```bash
# Opción 1: Docker Compose (múltiples workers)
docker-compose -f docker-compose.dev.yml up -d --scale worker-media=3

# Opción 2: Múltiples terminales
# Terminal 1
uv run arq app.workers.worker_config.WorkerSettings

# Terminal 2
uv run arq app.workers.worker_config.WorkerSettings

# Terminal 3
uv run arq app.workers.worker_config.WorkerSettings
```

---

## Monitoreo

### 1. Revisar tareas en Redis

```bash
# Conectar a Redis
docker exec -it fastapi_redis_dev redis-cli

# Ver todas las keys
KEYS *

# Ver cola de ARQ
LRANGE arq:queue 0 -1

# Ver estado de tarea
GET task_status:abc123
```

### 2. Logs de workers

```bash
# Docker
docker-compose -f docker-compose.dev.yml logs -f worker-media

# Local
# Los logs aparecen en la terminal donde ejecutaste el worker
```

### 3. Redis Commander (UI)

Acceder a: http://localhost:8081

- Ver todas las keys
- Explorar colas
- Ver mensajes Pub/Sub

---

## Endpoints Disponibles

### Procesamiento de Media

```bash
# Procesar media (thumbnail + optimize)
POST /tasks/media/process
{
  "media_id": 123,
  "file_path": "/media/image.jpg",
  "operations": ["thumbnail", "optimize"]
}

# Solo generar thumbnail
POST /tasks/media/thumbnail
{
  "media_id": 123,
  "file_path": "/media/image.jpg"
}
```

### Envío de Emails

```bash
# Enviar email individual
POST /tasks/email/send
{
  "to_email": "user@example.com",
  "subject": "Welcome",
  "body": "Thanks for signing up"
}

# Envío masivo
POST /tasks/email/bulk
{
  "emails": [
    {"to_email": "user1@...", "subject": "...", "body": "..."},
    {"to_email": "user2@...", "subject": "...", "body": "..."}
  ],
  "rate_limit": 10
}
```

### Estado de Tareas

```bash
# Consultar estado
GET /tasks/{task_id}/status

# Cancelar tarea (solo si está en cola)
DELETE /tasks/{task_id}
```

---

## Troubleshooting

### Worker no procesa tareas

```bash
# 1. Verificar que Redis esté corriendo
docker ps | grep redis

# 2. Verificar que worker esté corriendo
docker ps | grep worker

# 3. Ver logs del worker
docker logs fastapi_worker_media_dev

# 4. Verificar conexión a Redis
docker exec -it fastapi_redis_dev redis-cli PING
```

### WebSocket no recibe notificaciones

```bash
# 1. Verificar que estés conectado al canal correcto
ws://localhost:8001/ws/media

# 2. Verificar que Redis Pub/Sub esté funcionando
docker exec -it fastapi_redis_dev redis-cli
> SUBSCRIBE task_notifications:123

# 3. Ver logs del backend
# Buscar: "[TaskNotification] Forwarded to WebSocket"
```

### Tareas quedan en pending

```bash
# 1. Verificar que workers estén corriendo
docker-compose -f docker-compose.dev.yml ps

# 2. Reiniciar workers
docker-compose -f docker-compose.dev.yml restart worker-media worker-email

# 3. Ver cola de Redis
docker exec -it fastapi_redis_dev redis-cli
> LRANGE arq:queue 0 -1
```

---

## Próximos Pasos

### Tareas que puedes agregar:

1. **Generación de embeddings** (cuando implementes búsqueda semántica)
2. **Procesamiento de video** (extraer frames, comprimir)
3. **Generación de reportes PDF**
4. **Scraping de datos**
5. **Sincronización con APIs externas**

### Ejemplo: Agregar tarea de embeddings

```python
# app/workers/ml_tasks.py

async def generate_embedding(
    ctx: Dict[str, Any],
    media_id: int,
    file_path: str,
    model: str = "openai"
) -> Dict[str, Any]:
    """Generar embedding para búsqueda semántica"""

    # Leer archivo
    text = read_file(file_path)

    # Llamar a API (OpenAI, Cohere, etc.)
    if model == "openai":
        embedding = await call_openai_embeddings(text)

    # Guardar en pgvector
    await save_embedding_to_db(media_id, embedding)

    return {"media_id": media_id, "embedding_size": len(embedding)}
```

---

¡Listo! Ya tienes un sistema completo de colas con notificaciones en tiempo real 🎉
