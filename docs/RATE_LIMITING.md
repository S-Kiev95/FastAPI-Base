# Rate Limiting Implementation

Sistema de rate limiting implementado con Redis para proteger la API de abuso y asegurar un uso justo.

## 📋 ¿Qué es Rate Limiting?

Rate limiting limita el número de requests que un cliente puede hacer en un período de tiempo. Por ejemplo:
- 100 requests por minuto
- 50 uploads por minuto
- 5 envíos masivos por hora

---

## 🎯 Objetivos

### Protege contra:
- ❌ Usuarios maliciosos (10,000 requests/segundo)
- ❌ Bots scrapeando sin control
- ❌ Bugs en frontend (loops infinitos)
- ❌ Ataques DDoS simples
- ❌ Saturación del servidor

### NO reemplaza:
- ✅ Sistema de colas (para tareas pesadas)
- ✅ Autenticación/Autorización
- ✅ Validación de datos

---

## 🏗️ Arquitectura

```
Request → Rate Limiter → [¿Dentro del límite?]
                              ↓              ↓
                             SÍ             NO
                              ↓              ↓
                       API Endpoint    429 Too Many Requests
```

### Componentes implementados:

1. **RateLimiter Service** - Lógica core con Redis
2. **RateLimitMiddleware** - Rate limit global por ruta
3. **@rate_limit decorator** - Rate limit por endpoint específico

---

## 📁 Archivos Creados

### 1. Rate Limiter Service
📁 `app/services/rate_limiter.py`

Implementa sliding window algorithm con Redis:
```python
from app.services.rate_limiter import rate_limiter

allowed, info = await rate_limiter.check_rate_limit(
    key="ip:192.168.1.1",
    limit=100,
    window=60
)

# allowed = True o False
# info = {
#     "limit": 100,
#     "remaining": 85,
#     "reset_at": 1640000000,
#     "retry_after": 0
# }
```

### 2. Middleware Global
📁 `app/middleware/rate_limit.py`

Aplica rate limiting a todas las rutas automáticamente:
- 100 requests/minuto (default)
- 50 requests/minuto para `/tasks/`
- 5 requests/hora para `/tasks/email/bulk`
- Excluye: `/health`, `/metrics`, `/docs`

### 3. Decorador para Endpoints
📁 `app/utils/rate_limit_decorator.py`

Permite aplicar límites específicos a endpoints individuales:
```python
@app.post("/api/action")
@rate_limit(limit=50, window=60)  # 50 requests/minuto
async def action(request: Request):
    ...
```

---

## 🚀 Configuración Actual

### Límites por Endpoint:

| Endpoint | Límite | Ventana | Razón |
|----------|--------|---------|-------|
| **General** | 100 | 60s | Default para todos los endpoints |
| `/tasks/media/process` | 50 | 60s | Procesamiento pesado |
| `/tasks/media/thumbnail` | 50 | 60s | Generación de thumbnails |
| `/tasks/email/send` | 30 | 60s | Prevenir spam |
| `/tasks/email/bulk` | 5 | 3600s | Envíos masivos (muy pesado) |

### Headers de Respuesta:

Cada response incluye headers informativos:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1640000000
```

Si excede el límite (429):
```
Retry-After: 45
```

---

## 💡 Uso

### Desde el Frontend

```javascript
// Hacer request normalmente
const response = await fetch('/tasks/media/process', {
  method: 'POST',
  body: JSON.stringify({...})
});

// Revisar headers
const limit = response.headers.get('X-RateLimit-Limit');
const remaining = response.headers.get('X-RateLimit-Remaining');
const resetAt = response.headers.get('X-RateLimit-Reset');

console.log(`${remaining}/${limit} requests restantes`);

// Si recibe 429
if (response.status === 429) {
  const retryAfter = response.headers.get('Retry-After');
  console.log(`Espera ${retryAfter} segundos`);

  // Implementar backoff exponencial
  await sleep(retryAfter * 1000);
  // Reintentar...
}
```

### Desde el Backend (agregar nuevo endpoint)

#### Opción 1: Usar decorador

```python
from app.utils.rate_limit_decorator import rate_limit

@app.post("/api/my-endpoint")
@rate_limit(limit=30, window=60)  # 30 requests/minuto
async def my_endpoint(request: Request):
    return {"message": "success"}
```

#### Opción 2: Rate limit por usuario

```python
from app.utils.rate_limit_decorator import rate_limit_by_user

@app.post("/api/premium-action")
@rate_limit_by_user(limit=100, window=60)  # Por usuario, no por IP
async def premium_action(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    return {"message": "success"}
```

#### Opción 3: Custom key function

```python
from app.utils.rate_limit_decorator import rate_limit

# Rate limit por API key
@app.post("/api/bulk-operation")
@rate_limit(
    limit=1000,
    window=60,
    key_func=lambda req, **kwargs: f"api_key:{kwargs.get('api_key')}"
)
async def bulk_operation(
    request: Request,
    api_key: str = Header(...)
):
    return {"message": "success"}
```

---

## 🔧 Configuración Personalizada

### Cambiar límites globales

En `main.py`:
```python
app.add_middleware(
    RateLimitMiddleware,
    default_limit=200,  # Cambiar a 200 requests/minuto
    default_window=60,
    exclude_paths=["/health", "/docs"]
)
```

### Agregar límites por ruta

En `app/middleware/rate_limit.py`:
```python
self.path_limits = {
    "/tasks/": (50, 60),
    "/tasks/email/bulk": (5, 3600),
    "/api/heavy-operation": (10, 60),  # ← Agregar nuevo
}
```

### Desactivar rate limiting

En `.env`:
```env
REDIS_ENABLED=False  # Desactiva rate limiting
```

---

## 📊 Monitoreo

### Ver límites en Redis

```bash
# Conectar a Redis
docker exec -it fastapi_redis_dev redis-cli

# Ver todas las keys de rate limiting
KEYS rate_limit:*

# Ver contador específico
ZCARD rate_limit:ip:192.168.1.1:/tasks/media/process

# Ver requests en ventana actual
ZRANGE rate_limit:ip:192.168.1.1:/tasks/media/process 0 -1 WITHSCORES
```

### Script de test

He creado un script para probar el rate limiting:

```bash
# Asegúrate que el servidor esté corriendo
uv run uvicorn main:app --port 8001

# En otra terminal, ejecutar test
python test_rate_limit.py
```

El script probará:
1. Requests dentro del límite
2. Requests que exceden el límite
3. Headers de respuesta
4. Comportamiento por endpoint

---

## 🎛️ Límites Recomendados

### Por Tipo de Operación:

#### Lectura (GET)
```python
@rate_limit(limit=1000, window=60)  # 1000/minuto
async def list_items():
    ...
```

#### Escritura Ligera (POST/PUT)
```python
@rate_limit(limit=100, window=60)  # 100/minuto
async def create_item():
    ...
```

#### Escritura Pesada (Media, Files)
```python
@rate_limit(limit=50, window=60)  # 50/minuto
async def upload_file():
    ...
```

#### Operaciones Batch
```python
@rate_limit(limit=10, window=3600)  # 10/hora
async def batch_operation():
    ...
```

#### Operaciones Críticas
```python
@rate_limit(limit=5, window=3600)  # 5/hora
async def delete_all_data():
    ...
```

---

## 🚨 Mensajes de Error

### Cuando se excede el límite

**Status Code:** `429 Too Many Requests`

**Response Body:**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Limit: 100 requests per 60 seconds",
  "limit": 100,
  "current_usage": 105,
  "retry_after": 45,
  "reset_at": 1640000045
}
```

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640000045
Retry-After: 45
```

---

## 🔐 Rate Limiting por Tier de Usuario

Puedes implementar diferentes límites según el tipo de usuario:

```python
# app/utils/rate_limit_tiers.py

RATE_LIMITS = {
    "free": {
        "media_upload": (10, 60),      # 10/minuto
        "api_calls": (100, 60),         # 100/minuto
    },
    "premium": {
        "media_upload": (100, 60),     # 100/minuto
        "api_calls": (1000, 60),        # 1000/minuto
    },
    "enterprise": {
        "media_upload": (1000, 60),    # Sin límite práctico
        "api_calls": (10000, 60),
    }
}

@app.post("/api/action")
async def action(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    tier = current_user.subscription_tier  # "free", "premium", etc.
    limit, window = RATE_LIMITS[tier]["api_calls"]

    allowed, info = await rate_limiter.check_rate_limit(
        key=f"user:{current_user.id}:api_calls",
        limit=limit,
        window=window
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {tier} tier"
        )

    # Procesar...
```

---

## 🔄 Estrategias de Retry (Frontend)

### Exponential Backoff

```javascript
async function requestWithBackoff(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(url, options);

    if (response.status === 429) {
      const retryAfter = parseInt(response.headers.get('Retry-After') || '5');
      const delay = Math.min(retryAfter * 1000 * (2 ** i), 60000); // Max 60s

      console.log(`Rate limited. Retrying in ${delay/1000}s...`);
      await sleep(delay);
      continue;
    }

    return response;
  }

  throw new Error('Max retries exceeded');
}
```

### Con indicador visual

```javascript
const response = await fetch('/tasks/media/process', {...});

if (response.status === 429) {
  const retryAfter = parseInt(response.headers.get('Retry-After'));

  // Mostrar toast/notification
  showNotification(
    `Límite excedido. Reintentando en ${retryAfter}s...`,
    'warning'
  );

  // Mostrar countdown
  for (let i = retryAfter; i > 0; i--) {
    updateCountdown(i);
    await sleep(1000);
  }

  // Reintentar automáticamente
  return await fetch('/tasks/media/process', {...});
}
```

---

## 🛠️ Troubleshooting

### Rate limit no funciona

**Verificar que Redis esté habilitado:**
```bash
# En .env
REDIS_ENABLED=True

# Verificar conexión
docker ps | grep redis
```

**Ver logs:**
```bash
# Al iniciar FastAPI deberías ver:
[OK] Rate limiting enabled

# Si ves esto, Redis no está disponible:
[WARNING] Rate limiting disabled (Redis not enabled)
```

### Rate limit demasiado estricto

**Solución temporal - Desactivar:**
```python
# En main.py, comentar:
# app.add_middleware(RateLimitMiddleware, ...)
```

**Solución permanente - Ajustar límites:**
```python
# Aumentar límite default
app.add_middleware(
    RateLimitMiddleware,
    default_limit=500,  # Era 100
    default_window=60
)
```

### Múltiples usuarios detrás de NAT

Si muchos usuarios comparten la misma IP (empresa, universidad):

```python
# Opción 1: Rate limit por usuario autenticado
@rate_limit_by_user(limit=100, window=60)

# Opción 2: Aumentar límite para IPs corporativas
CORPORATE_IPS = ["192.168.1.0/24", "10.0.0.0/8"]

# En middleware, detectar y aplicar límite mayor
if client_ip in CORPORATE_IPS:
    limit = 1000  # Límite mayor
```

---

## 📚 Referencias

- **Algoritmo:** Sliding Window con Redis ZSET
- **Ventajas:** Preciso, eficiente, distribuido
- **Alternativas:** Token bucket, Leaky bucket, Fixed window

---

## ✅ Resumen

### Lo que tienes:
✅ Rate limiting global (middleware)
✅ Rate limiting por endpoint (decorador)
✅ Headers informativos
✅ Mensajes de error claros
✅ Configuración flexible
✅ Compatible con sistema de colas

### Lo que puedes agregar después:
⏸️ Rate limiting por usuario/API key
⏸️ Diferentes tiers (free, premium, enterprise)
⏸️ Dashboard de monitoreo
⏸️ Alertas cuando límites se exceden frecuentemente
⏸️ Whitelist de IPs

---

¡El rate limiting está implementado y listo para proteger tu API! 🎉
