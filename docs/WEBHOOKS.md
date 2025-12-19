# Sistema de Webhooks

Sistema completo de webhooks para integraciones con sistemas externos. Permite suscribirse a eventos y recibir notificaciones HTTP POST cuando ocurren.

## 📋 Tabla de Contenidos

1. [Qué son los Webhooks](#qué-son-los-webhooks)
2. [Características](#características)
3. [Arquitectura](#arquitectura)
4. [Eventos Disponibles](#eventos-disponibles)
5. [API Reference](#api-reference)
6. [Seguridad (HMAC Signatures)](#seguridad-hmac-signatures)
7. [Retries y Backoff](#retries-y-backoff)
8. [Ejemplos de Uso](#ejemplos-de-uso)
9. [Monitoreo y Logs](#monitoreo-y-logs)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Qué son los Webhooks

Los **webhooks** son notificaciones HTTP que tu aplicación envía a sistemas externos cuando ocurre un evento.

### Flujo básico:

```
1. Sistema Externo se suscribe a eventos:
   POST /webhooks/subscriptions
   {
     "url": "https://external.com/hook",
     "events": ["user.created", "task.completed"]
   }

2. Evento ocurre en tu app:
   - Usuario creado → user_id=123

3. Tu app envía webhook:
   POST https://external.com/hook
   {
     "event_type": "user.created",
     "event_id": "uuid",
     "timestamp": "2025-12-19T...",
     "data": {
       "user_id": 123,
       "email": "user@example.com"
     }
   }

4. Sistema externo responde:
   200 OK

5. Si falla → Retry automático con backoff exponencial
```

---

## Características

✅ **Eventos flexibles** - 15+ tipos de eventos predefinidos
✅ **HMAC Signatures** - Seguridad con firma SHA256
✅ **Retry automático** - Exponential backoff configurable
✅ **Filtros** - Filtra eventos por criterios específicos
✅ **Headers personalizados** - Agrega autenticación, tokens, etc.
✅ **Logs detallados** - Historial completo de entregas
✅ **Test endpoints** - Prueba webhooks antes de activarlos
✅ **Estadísticas** - Tasa de éxito, últimas entregas, etc.
✅ **Async delivery** - Procesamiento en cola (ARQ)
✅ **Timeout configurable** - Control de timeouts por webhook

---

## Arquitectura

### Componentes:

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Endpoint (e.g., POST /users)                               │
│       │                                                      │
│       ├─> Crea usuario en DB                                │
│       │                                                      │
│       └─> trigger_webhook(                                  │
│              event_type="user.created",                     │
│              data={"user_id": 123, ...}                     │
│           )                                                  │
│              │                                               │
│              ▼                                               │
│     WebhookService.trigger_event()                          │
│              │                                               │
│              ├─> Busca subscripciones activas              │
│              │   para "user.created"                        │
│              │                                               │
│              ├─> Aplica filtros (si existen)               │
│              │                                               │
│              └─> Enqueue en ARQ                             │
│                      │                                       │
└──────────────────────┼───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     ARQ Worker (Redis Queue)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  deliver_webhook(subscription_id, event, payload)           │
│       │                                                      │
│       ├─> Genera HMAC signature                             │
│       │                                                      │
│       ├─> HTTP POST a URL destino                           │
│       │       Headers:                                       │
│       │         - X-Webhook-Signature: sha256=...           │
│       │         - X-Webhook-Event: user.created             │
│       │         - Custom headers                            │
│       │                                                      │
│       ├─> Recibe respuesta                                  │
│       │                                                      │
│       ├─> Guarda en webhook_deliveries                      │
│       │   (status, response, duration, etc.)                │
│       │                                                      │
│       └─> Si falla:                                          │
│              ├─> Calcular próximo retry                     │
│              └─> Enqueue retry (si quedan intentos)         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
          Sistema Externo (tu servicio)
```

### Base de Datos:

**webhook_subscriptions**
- Configuración de suscripciones
- URL, eventos, secret, headers
- Configuración de retries
- Estadísticas (total, éxitos, fallos)

**webhook_deliveries**
- Log de cada entrega
- Request/response completo
- Timing, status code, errors
- Info de retries

---

## Eventos Disponibles

### User Events

| Evento | Cuándo se dispara | Datos incluidos |
|--------|------------------|----------------|
| `user.created` | Usuario creado | `user_id`, `email`, `role`, `created_at` |
| `user.updated` | Usuario actualizado | `user_id`, `email`, `changes` |
| `user.deleted` | Usuario eliminado | `user_id`, `email`, `deleted_at` |
| `user.login` | Usuario inicia sesión | `user_id`, `email`, `ip`, `timestamp` |

### Entity Events (Dinámicos)

| Evento | Cuándo se dispara | Datos incluidos |
|--------|------------------|----------------|
| `entity.created` | Entidad creada | `entity_type`, `entity_id`, `data` |
| `entity.updated` | Entidad actualizada | `entity_type`, `entity_id`, `changes` |
| `entity.deleted` | Entidad eliminada | `entity_type`, `entity_id` |

### Task Events

| Evento | Cuándo se dispara | Datos incluidos |
|--------|------------------|----------------|
| `task.started` | Task inicia | `task_id`, `task_type`, `started_at` |
| `task.completed` | Task completa exitosamente | `task_id`, `task_type`, `result`, `duration_ms` |
| `task.failed` | Task falla | `task_id`, `task_type`, `error`, `duration_ms` |

### Media Events

| Evento | Cuándo se dispara | Datos incluidos |
|--------|------------------|----------------|
| `media.processed` | Media procesada | `media_id`, `thumbnail_path`, `optimized_path`, `compression_ratio` |
| `media.failed` | Procesamiento falla | `media_id`, `error` |

### Email Events

| Evento | Cuándo se dispara | Datos incluidos |
|--------|------------------|----------------|
| `email.sent` | Email enviado | `to_email`, `subject`, `sent_at` |
| `email.failed` | Email falla | `to_email`, `subject`, `error` |
| `bulk_email.completed` | Bulk email completa | `total`, `sent`, `failed` |

### Permission Events

| Evento | Cuándo se dispara | Datos incluidos |
|--------|------------------|----------------|
| `permissions.updated` | Permisos actualizados | `user_id`, `role_id`, `permissions` |
| `role.created` | Rol creado | `role_id`, `role_name`, `permissions` |
| `role.updated` | Rol actualizado | `role_id`, `changes` |

---

## API Reference

### Crear Webhook Subscription

```http
POST /webhooks/subscriptions
Content-Type: application/json

{
  "name": "My Webhook",
  "description": "Notifies my service of user events",
  "url": "https://myservice.com/webhooks/users",
  "events": ["user.created", "user.updated", "user.deleted"],
  "secret": "your-secret-key",  // Optional: auto-generated if not provided
  "active": true,
  "headers": {
    "Authorization": "Bearer my-token",
    "X-Custom-Header": "value"
  },
  "max_retries": 3,
  "retry_backoff": 60,  // Seconds between retries
  "timeout": 10,  // Request timeout in seconds
  "filters": {
    // Optional: only trigger for specific conditions
    "user_id": 123  // Only trigger for user_id=123
  }
}
```

**Response:**
```json
{
  "id": 1,
  "name": "My Webhook",
  "url": "https://myservice.com/webhooks/users",
  "events": ["user.created", "user.updated", "user.deleted"],
  "active": true,
  "secret": "auto-generated-or-yours",  // Hidden in real responses
  "max_retries": 3,
  "retry_backoff": 60,
  "timeout": 10,
  "created_at": "2025-12-19T10:30:45Z",
  "total_deliveries": 0,
  "successful_deliveries": 0,
  "failed_deliveries": 0
}
```

---

### Listar Webhooks

```http
GET /webhooks/subscriptions?active_only=true&event_type=user.created
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "My Webhook",
    "url": "https://myservice.com/webhooks/users",
    "events": ["user.created", "user.updated"],
    "active": true,
    "total_deliveries": 150,
    "successful_deliveries": 148,
    "failed_deliveries": 2,
    "last_delivery_at": "2025-12-19T10:45:00Z",
    "last_success_at": "2025-12-19T10:45:00Z"
  }
]
```

---

### Ver Logs de Entregas

```http
GET /webhooks/deliveries?subscription_id=1&limit=50
```

**Response:**
```json
[
  {
    "id": 1001,
    "subscription_id": 1,
    "event_type": "user.created",
    "payload": {
      "event_type": "user.created",
      "event_id": "uuid-here",
      "timestamp": "2025-12-19T10:45:00Z",
      "data": {
        "user_id": 123,
        "email": "user@example.com"
      }
    },
    "url": "https://myservice.com/webhooks/users",
    "status_code": 200,
    "success": true,
    "delivered_at": "2025-12-19T10:45:01Z",
    "duration_ms": 234,
    "attempt_number": 1,
    "will_retry": false
  },
  {
    "id": 1002,
    "subscription_id": 1,
    "event_type": "user.updated",
    "status_code": 500,
    "success": false,
    "error_message": "HTTP 500: Internal Server Error",
    "attempt_number": 1,
    "will_retry": true,
    "next_retry_at": "2025-12-19T10:47:00Z"
  }
]
```

---

### Test Webhook

Prueba si una URL funciona antes de crear la subscription:

```http
POST /webhooks/test
Content-Type: application/json

{
  "url": "https://myservice.com/webhooks/test",
  "headers": {
    "Authorization": "Bearer test-token"
  },
  "timeout": 10
}
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response_body": "OK",
  "duration_ms": 145,
  "error_message": null
}
```

**Test Payload Enviado:**
```json
{
  "event_type": "test.ping",
  "event_id": "uuid",
  "timestamp": "2025-12-19T...",
  "data": {
    "message": "This is a test webhook from FastAPI Webhooks",
    "test": true
  }
}
```

---

### Ver Estadísticas

```http
GET /webhooks/subscriptions/{id}/stats
```

**Response:**
```json
{
  "subscription_id": 1,
  "total_deliveries": 150,
  "successful_deliveries": 148,
  "failed_deliveries": 2,
  "success_rate": 98.67,  // Percentage
  "last_delivery_at": "2025-12-19T10:45:00Z",
  "last_success_at": "2025-12-19T10:45:00Z",
  "last_failure_at": "2025-12-19T09:15:23Z",
  "recent_deliveries": [
    // 10 entregas más recientes
  ]
}
```

---

### Actualizar Webhook

```http
PATCH /webhooks/subscriptions/{id}
Content-Type: application/json

{
  "active": false,  // Pausar webhook
  "max_retries": 5  // Aumentar retries
}
```

---

### Eliminar Webhook

```http
DELETE /webhooks/subscriptions/{id}
```

---

## Seguridad (HMAC Signatures)

Todos los webhooks incluyen una **firma HMAC SHA256** para que puedas verificar que vienen de tu aplicación.

### Cómo funciona:

1. **Tu app genera signature:**
```python
import hmac
import hashlib
import json

payload = {...}  # Event payload
secret = "your-secret-key"

payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
signature = hmac.new(
    secret.encode('utf-8'),
    payload_bytes,
    hashlib.sha256
).hexdigest()

# Signature: "abc123def456..."
```

2. **Tu app envía header:**
```http
POST https://yourservice.com/webhooks
X-Webhook-Signature: sha256=abc123def456...
X-Webhook-Event: user.created
X-Webhook-Delivery: uuid
Content-Type: application/json

{payload}
```

3. **Tu servicio verifica signature:**

**Python (Flask/FastAPI):**
```python
import hmac
import hashlib
import json
from fastapi import Request, HTTPException

@app.post("/webhooks")
async def receive_webhook(request: Request):
    # 1. Obtener signature del header
    signature = request.headers.get("X-Webhook-Signature")
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing signature")

    received_signature = signature.replace("sha256=", "")

    # 2. Obtener payload
    payload = await request.json()

    # 3. Calcular signature esperada
    secret = "your-secret-key"  # Mismo secret de la subscription
    payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    # 4. Comparar (constant-time comparison)
    if not hmac.compare_digest(received_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 5. Procesar evento
    event_type = request.headers.get("X-Webhook-Event")
    print(f"Received event: {event_type}")
    print(f"Payload: {payload}")

    return {"status": "ok"}
```

**Node.js (Express):**
```javascript
const crypto = require('crypto');
const express = require('express');

app.post('/webhooks', express.json(), (req, res) => {
  // 1. Get signature
  const signature = req.headers['x-webhook-signature'];
  if (!signature || !signature.startsWith('sha256=')) {
    return res.status(401).json({ error: 'Missing signature' });
  }

  const receivedSignature = signature.replace('sha256=', '');

  // 2. Calculate expected signature
  const secret = 'your-secret-key';
  const payload = JSON.stringify(req.body);
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  // 3. Compare (constant-time)
  if (!crypto.timingSafeEqual(
    Buffer.from(receivedSignature),
    Buffer.from(expectedSignature)
  )) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  // 4. Process event
  const eventType = req.headers['x-webhook-event'];
  console.log(`Received event: ${eventType}`);
  console.log(`Payload:`, req.body);

  res.json({ status: 'ok' });
});
```

---

## Retries y Backoff

Si una entrega falla, el sistema reintenta automáticamente con **exponential backoff**.

### Configuración:

```json
{
  "max_retries": 3,
  "retry_backoff": 60  // Base backoff in seconds
}
```

### Cálculo de delays:

```
Attempt 1: Inmediato
Attempt 2: 60s  * (2^1) = 60s  después del fallo
Attempt 3: 60s  * (2^2) = 240s después del fallo (4 min)
Attempt 4: 60s  * (2^3) = 480s después del fallo (8 min)
```

### Estados de delivery:

```
Attempt 1 → 500 Error
  ↓
will_retry = true
next_retry_at = now + 60s
  ↓
Attempt 2 (60s después) → Timeout
  ↓
will_retry = true
next_retry_at = now + 240s
  ↓
Attempt 3 (240s después) → 200 OK
  ↓
success = true
will_retry = false
```

### Condiciones de retry:

✅ **Retry SI:**
- Status code: 5xx (500, 502, 503, etc.)
- Timeout
- Connection error
- `attempt_number < max_retries`

❌ **NO Retry:**
- Status code: 2xx (200, 201, etc.) → Éxito
- Status code: 4xx (400, 404, etc.) → Error del cliente, no tiene sentido reintentar
- `attempt_number >= max_retries` → Agotados los intentos

---

## Ejemplos de Uso

### Ejemplo 1: Sincronizar usuarios con CRM externo

**1. Crear webhook:**
```bash
curl -X POST http://localhost:8001/webhooks/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CRM User Sync",
    "url": "https://crm.example.com/api/webhooks/users",
    "events": ["user.created", "user.updated", "user.deleted"],
    "headers": {
      "Authorization": "Bearer crm-api-token"
    }
  }'
```

**2. En tu código (crear usuario):**
```python
from app.utils.webhooks import trigger_webhook

@router.post("/users")
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Crear usuario
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    db.refresh(user)

    # Trigger webhook
    await trigger_webhook(
        db=db,
        event_type="user.created",
        data={
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "created_at": user.created_at.isoformat()
        }
    )

    return user
```

**3. Tu CRM recibe:**
```http
POST https://crm.example.com/api/webhooks/users
Authorization: Bearer crm-api-token
X-Webhook-Signature: sha256=...
X-Webhook-Event: user.created
Content-Type: application/json

{
  "event_type": "user.created",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-19T10:30:45.123Z",
  "data": {
    "user_id": 123,
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2025-12-19T10:30:45Z"
  }
}
```

---

### Ejemplo 2: Notificar Slack cuando tasks fallan

**1. Crear webhook:**
```bash
curl -X POST http://localhost:8001/webhooks/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Slack Task Failures",
    "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    "events": ["task.failed", "media.failed", "email.failed"]
  }'
```

**2. En tu worker (media_tasks.py):**
```python
from app.utils.webhooks import trigger_webhook

async def process_media(ctx, media_id, file_path):
    try:
        # ... procesamiento ...
        result = {"media_id": media_id, "success": True}
    except Exception as e:
        # Trigger webhook de fallo
        db = SessionLocal()
        try:
            await trigger_webhook(
                db=db,
                event_type="media.failed",
                data={
                    "media_id": media_id,
                    "file_path": file_path,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        finally:
            db.close()

        raise
```

**3. Slack recibe notificación:**
```json
{
  "event_type": "media.failed",
  "data": {
    "media_id": 456,
    "file_path": "/media/image.jpg",
    "error": "Invalid image format",
    "timestamp": "2025-12-19T..."
  }
}
```

---

### Ejemplo 3: Webhook con filtros

Solo notificar para usuarios VIP:

```bash
curl -X POST http://localhost:8001/webhooks/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "VIP Users Only",
    "url": "https://vip-service.com/webhook",
    "events": ["user.created", "user.updated"],
    "filters": {
      "role": "vip"
    }
  }'
```

Trigger webhook:
```python
await trigger_webhook(
    db=db,
    event_type="user.created",
    data={
        "user_id": 123,
        "email": "vip@example.com",
        "role": "vip"  # ← Coincide con el filtro
    }
)
# ✅ Webhook se dispara

await trigger_webhook(
    db=db,
    event_type="user.created",
    data={
        "user_id": 124,
        "email": "normal@example.com",
        "role": "user"  # ← NO coincide
    }
)
# ❌ Webhook NO se dispara (filtrado)
```

---

## Monitoreo y Logs

### Ver entregas recientes:

```bash
curl http://localhost:8001/webhooks/deliveries?limit=10
```

### Ver solo fallos:

```bash
curl http://localhost:8001/webhooks/deliveries?success_only=false&limit=50
```

### Ver stats de un webhook:

```bash
curl http://localhost:8001/webhooks/subscriptions/1/stats
```

### Logs estructurados:

Todos los webhooks loguean en formato estructurado:

```json
{
  "timestamp": "2025-12-19T10:30:45Z",
  "level": "INFO",
  "logger": "app.services.webhook_service",
  "message": "Webhook delivered successfully",
  "subscription_id": 1,
  "event_type": "user.created",
  "job_id": "arq-job-123",
  "delivery_id": 1001,
  "status_code": 200,
  "duration_ms": 234
}
```

---

## Best Practices

### ✅ DO:

1. **Usa HTTPS en producción:**
```json
{
  "url": "https://yourservice.com/webhooks"  // ✅
}
```

2. **Verifica signatures siempre:**
```python
# ✅ BIEN
if not verify_signature(payload, signature, secret):
    raise HTTPException(status_code=401)
```

3. **Responde rápido (< 5 segundos):**
```python
# ✅ BIEN
@app.post("/webhooks")
async def receive_webhook(request: Request):
    payload = await request.json()

    # Procesar async en background
    background_tasks.add_task(process_webhook, payload)

    # Responder inmediatamente
    return {"status": "accepted"}
```

4. **Usa idempotency (event_id):**
```python
# ✅ BIEN - Evita procesar duplicados
event_id = payload["event_id"]

if redis.exists(f"processed:{event_id}"):
    return {"status": "already_processed"}

process_event(payload)
redis.setex(f"processed:{event_id}", 3600, "1")  # Cache 1h
```

5. **Loguea todo:**
```python
# ✅ BIEN
logger.info("Webhook received",
           event_type=event_type,
           event_id=event_id,
           subscription_id=subscription_id)
```

---

### ❌ DON'T:

1. **No uses HTTP en producción:**
```json
{
  "url": "http://yourservice.com/webhooks"  // ❌ Inseguro
}
```

2. **No ignores signatures:**
```python
# ❌ MAL - Cualquiera puede enviar webhooks falsos
@app.post("/webhooks")
def receive_webhook(payload: dict):
    process_event(payload)  # Sin verificar signature
```

3. **No proceses sincrónicamente:**
```python
# ❌ MAL - Bloquea el webhook
@app.post("/webhooks")
def receive_webhook(payload: dict):
    time.sleep(10)  # Procesamiento largo
    send_email(payload)  # Más procesamiento
    return {"status": "ok"}  # Timeout!
```

4. **No asumas orden de eventos:**
```python
# ❌ MAL - Los webhooks pueden llegar desordenados
@app.post("/webhooks")
def receive_webhook(payload: dict):
    if payload["event_type"] == "user.updated":
        # Asumir que user.created ya llegó
        # ❌ Puede no ser cierto!
```

5. **No retornes 5xx por errores de datos:**
```python
# ❌ MAL - Causará retries innecesarios
@app.post("/webhooks")
def receive_webhook(payload: dict):
    user_id = payload["data"]["user_id"]
    user = db.get_user(user_id)
    if not user:
        return {"error": "User not found"}, 500  # ❌ Retry innecesario

# ✅ BIEN
if not user:
    return {"error": "User not found"}, 400  # Sin retry
```

---

## Troubleshooting

### Webhook no se dispara

**1. Verificar subscription activa:**
```bash
curl http://localhost:8001/webhooks/subscriptions
```
→ Asegurar `"active": true`

**2. Verificar eventos:**
```bash
curl http://localhost:8001/webhooks/events
```
→ Confirmar que el evento existe

**3. Verificar logs:**
```bash
# Ver logs del servicio
tail -f logs/app.log | grep webhook
```

**4. Verificar filtros:**
Si tienes filtros, asegurar que el payload los cumple:
```json
{
  "filters": {"role": "vip"}
}
```
→ El payload debe incluir `"role": "vip"`

---

### Webhook falla siempre

**1. Test endpoint primero:**
```bash
curl -X POST http://localhost:8001/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourservice.com/webhook",
    "timeout": 10
  }'
```

**2. Verificar signature:**
Tu endpoint debe verificar correctamente la signature (ver sección Seguridad).

**3. Verificar timeout:**
Responder en < 10 segundos (o el timeout configurado).

**4. Ver logs de delivery:**
```bash
curl http://localhost:8001/webhooks/deliveries?subscription_id=1&success_only=false
```
→ Ver `error_message` para detalles

---

### Retries no funcionan

**1. Verificar max_retries:**
```bash
curl http://localhost:8001/webhooks/subscriptions/1
```
→ `max_retries` debe ser > 0

**2. Verificar que el error sea retriable:**
- 5xx → Retry ✅
- Timeout → Retry ✅
- 4xx → NO retry ❌

**3. Verificar worker ARQ está corriendo:**
```bash
arq app.workers.worker_config.WorkerSettings
```

---

### Demasiados webhooks duplicados

**Causa:** Múltiples workers procesando el mismo evento.

**Solución:** Implementar idempotency con event_id:

```python
@app.post("/webhooks")
def receive_webhook(payload: dict):
    event_id = payload["event_id"]

    # Check if already processed
    if redis.exists(f"processed:{event_id}"):
        return {"status": "already_processed"}

    # Process
    process_event(payload)

    # Mark as processed (TTL 1 hour)
    redis.setex(f"processed:{event_id}", 3600, "1")

    return {"status": "ok"}
```

---

## Webhook Payload Format

Todos los webhooks siguen este formato estándar:

```json
{
  "event_type": "user.created",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-19T10:30:45.123456Z",
  "source": "fastapi_base",
  "version": "1.0",
  "data": {
    // Event-specific data
    "user_id": 123,
    "email": "user@example.com"
  }
}
```

**Campos garantizados:**
- `event_type` (string) - Tipo de evento
- `event_id` (UUID string) - ID único del evento
- `timestamp` (ISO 8601 string) - Cuándo ocurrió
- `source` (string) - Nombre de la aplicación
- `version` (string) - Versión del schema
- `data` (object) - Datos específicos del evento

---

¡Listo! Ya tienes un sistema completo de webhooks con seguridad, retries, logging y monitoreo 🎉
