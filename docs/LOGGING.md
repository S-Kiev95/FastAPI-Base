# Sistema de Logging Estructurado

Sistema completo de logging estructurado con soporte JSON/texto, request IDs, contextos y rotación de logs.

## 📋 Tabla de Contenidos

1. [Qué es y para qué sirve](#qué-es-y-para-qué-sirve)
2. [Características](#características)
3. [Configuración](#configuración)
4. [Uso Básico](#uso-básico)
5. [LogContext (Contexto de Logs)](#logcontext-contexto-de-logs)
6. [Request IDs](#request-ids)
7. [Niveles de Log](#niveles-de-log)
8. [Ejemplos](#ejemplos)
9. [Integración con Log Aggregators](#integración-con-log-aggregators)
10. [Best Practices](#best-practices)

---

## Qué es y para qué sirve

El **logging estructurado** organiza los logs en formato **JSON** o texto enriquecido, facilitando su análisis automático por herramientas de agregación (ELK, Loki, Datadog, etc.).

### Problemas que resuelve:

❌ **Sin logging estructurado:**
```python
print(f"User {user_id} uploaded file {filename}")
# Output: User 123 uploaded file image.jpg
# 🤔 Difícil de parsear automáticamente
# 🤔 No se puede filtrar por user_id fácilmente
# 🤔 No hay contexto de request
```

✅ **Con logging estructurado:**
```python
logger.info("User uploaded file", user_id=123, filename="image.jpg")
# Output JSON:
# {
#   "timestamp": "2025-12-18T10:30:45.123Z",
#   "level": "INFO",
#   "message": "User uploaded file",
#   "user_id": 123,
#   "filename": "image.jpg",
#   "request_id": "abc-123",
#   "client_ip": "192.168.1.1"
# }
# ✅ Parseable automáticamente
# ✅ Filtrable por cualquier campo
# ✅ Contexto completo del request
```

---

## Características

✅ **Formato JSON o texto** - Configurable según entorno
✅ **Request IDs** - Traza única para cada request
✅ **LogContext** - Propagación de contexto automática
✅ **Rotación de logs** - 10MB por archivo, 5 backups
✅ **Niveles de log** - DEBUG, INFO, WARNING, ERROR, CRITICAL
✅ **Campos extra** - Agrega campos personalizados fácilmente
✅ **Integration-ready** - Compatible con ELK, Loki, Datadog, etc.

---

## Configuración

### Variables de entorno (.env)

```bash
# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log format: json (structured) or text (human-readable)
# Use 'json' for production (parseable by log aggregators)
# Use 'text' for development (easier to read)
LOG_FORMAT=json

# Log file path (optional - leave empty to log only to stdout)
# Example: logs/app.log
LOG_FILE=
```

### Niveles por entorno:

**Desarrollo:**
```bash
LOG_LEVEL=DEBUG
LOG_FORMAT=text
LOG_FILE=
```

**Producción:**
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log
```

---

## Uso Básico

### 1. Importar el logger

```python
from app.utils.logger import get_structured_logger

logger = get_structured_logger(__name__)
```

### 2. Logs simples

```python
# INFO
logger.info("Application started")

# WARNING
logger.warning("Cache connection failed")

# ERROR
logger.error("Database query failed")

# DEBUG (solo si LOG_LEVEL=DEBUG)
logger.debug("Processing user data")
```

### 3. Logs con campos extra

```python
# Agregar campos personalizados
logger.info("User created",
           user_id=123,
           email="user@example.com",
           role="admin")

# Output JSON:
{
  "timestamp": "2025-12-18T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.routes.users",
  "message": "User created",
  "user_id": 123,
  "email": "user@example.com",
  "role": "admin"
}
```

### 4. Logs con excepciones

```python
try:
    result = process_data()
except Exception as e:
    logger.error("Data processing failed",
                error=str(e),
                data_id=data_id)
    raise
```

---

## LogContext (Contexto de Logs)

El **LogContext** propaga campos automáticamente a todos los logs dentro de un scope:

### ¿Para qué sirve?

Evita repetir campos en cada log. Todos los logs dentro del contexto heredan los campos automáticamente.

### Ejemplo básico:

```python
from app.utils.logger import LogContext

# Todos los logs dentro del contexto tendrán user_id y request_id
with LogContext(user_id=123, request_id="abc-123"):
    logger.info("Processing started")  # Incluye user_id + request_id
    logger.info("Step 1 completed")    # Incluye user_id + request_id
    logger.info("All done")            # Incluye user_id + request_id
```

### Output:

```json
{"timestamp": "...", "message": "Processing started", "user_id": 123, "request_id": "abc-123"}
{"timestamp": "...", "message": "Step 1 completed", "user_id": 123, "request_id": "abc-123"}
{"timestamp": "...", "message": "All done", "user_id": 123, "request_id": "abc-123"}
```

### Ejemplo en workers:

```python
async def process_media(ctx, media_id, file_path):
    job_id = ctx.get("job_id")

    # Todos los logs tendrán job_id y media_id
    with LogContext(job_id=job_id, media_id=media_id, task="process_media"):
        logger.info("Starting media processing")

        # Procesar...
        logger.info("Thumbnail generated")
        logger.info("Image optimized")
        logger.info("Processing completed")
```

### Contextos anidados:

```python
with LogContext(request_id="abc-123"):
    logger.info("Request started")

    with LogContext(user_id=123):  # Hereda request_id
        logger.info("User authenticated")  # Tiene request_id + user_id

    logger.info("Request completed")  # Solo tiene request_id
```

---

## Request IDs

Cada request HTTP recibe un **request_id único** (UUID) que se propaga automáticamente:

### Middleware automático:

El `LoggingMiddleware` genera un request_id para cada request y lo agrega al contexto:

```python
# Automático en main.py
app.add_middleware(LoggingMiddleware)
```

### ¿Qué incluye?

Cada request automáticamente loggea:
- `request_id` - UUID único
- `method` - GET, POST, etc.
- `path` - /api/users
- `client_ip` - IP del cliente
- `user_id` - Si está autenticado
- `duration_ms` - Tiempo de respuesta
- `status_code` - 200, 404, 500, etc.

### Ejemplo de logs de un request:

```json
// Request start
{
  "timestamp": "2025-12-18T10:30:45.123Z",
  "level": "INFO",
  "message": "Request started",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/users",
  "client_ip": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}

// Request completed
{
  "timestamp": "2025-12-18T10:30:45.456Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 201,
  "duration_ms": 333.45
}
```

### Acceder al request_id en tu código:

```python
from fastapi import Request

@app.post("/users")
async def create_user(request: Request):
    request_id = request.state.request_id
    logger.info("Creating user", request_id=request_id)
```

### Header en la respuesta:

```http
HTTP/1.1 200 OK
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

---

## Niveles de Log

| Nivel | Cuándo usar | Ejemplo |
|-------|-------------|---------|
| **DEBUG** | Información detallada para debugging | `logger.debug("Processing data", data=data)` |
| **INFO** | Eventos normales del sistema | `logger.info("User created", user_id=123)` |
| **WARNING** | Situaciones anormales pero manejables | `logger.warning("Cache miss", key="users:123")` |
| **ERROR** | Errores que requieren atención | `logger.error("Database query failed", error=str(e))` |
| **CRITICAL** | Fallos críticos del sistema | `logger.critical("Database unreachable")` |

### Configuración por entorno:

**Desarrollo:**
```bash
LOG_LEVEL=DEBUG  # Ver todo
```

**Staging:**
```bash
LOG_LEVEL=INFO  # Ver operaciones normales + errores
```

**Producción:**
```bash
LOG_LEVEL=WARNING  # Solo warnings + errores
```

---

## Ejemplos

### Ejemplo 1: Endpoint de creación de usuario

```python
from fastapi import APIRouter, Request
from app.utils.logger import get_structured_logger, LogContext

logger = get_structured_logger(__name__)
router = APIRouter()

@router.post("/users")
async def create_user(request: Request, user_data: UserCreate):
    # El request_id ya está en el contexto por el middleware

    logger.info("Creating user", email=user_data.email)

    try:
        # Crear usuario
        user = await user_service.create(user_data)

        logger.info("User created successfully",
                   user_id=user.id,
                   email=user.email,
                   role=user.role)

        return user

    except ValidationError as e:
        logger.warning("User creation failed - validation error",
                      error=str(e),
                      email=user_data.email)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("User creation failed - unexpected error",
                    error=str(e),
                    email=user_data.email)
        raise
```

### Ejemplo 2: Worker con LogContext

```python
from app.utils.logger import get_structured_logger, LogContext

logger = get_structured_logger(__name__)

async def process_media(ctx, media_id, file_path):
    job_id = ctx.get("job_id")

    # Crear contexto con job_id y media_id
    with LogContext(job_id=job_id, media_id=media_id, task="process_media"):
        logger.info("Starting media processing", file_path=file_path)

        try:
            # Generar thumbnail
            logger.info("Generating thumbnail")
            thumbnail = generate_thumbnail(file_path)
            logger.info("Thumbnail generated", thumbnail_path=thumbnail.path)

            # Optimizar imagen
            logger.info("Optimizing image")
            optimized = optimize_image(file_path)
            logger.info("Image optimized",
                       original_size=optimized.original_size,
                       compressed_size=optimized.compressed_size,
                       compression_ratio=optimized.ratio)

            logger.info("Media processing completed successfully")
            return {"thumbnail": thumbnail, "optimized": optimized}

        except Exception as e:
            logger.error("Media processing failed", error=str(e))
            raise
```

### Ejemplo 3: Service con logging detallado

```python
from app.utils.logger import get_structured_logger

logger = get_structured_logger(__name__)

class UserService:
    async def authenticate(self, email: str, password: str):
        logger.debug("Authenticating user", email=email)

        # Buscar usuario
        user = await self.get_by_email(email)
        if not user:
            logger.warning("Authentication failed - user not found", email=email)
            return None

        # Verificar contraseña
        if not verify_password(password, user.hashed_password):
            logger.warning("Authentication failed - invalid password",
                          user_id=user.id,
                          email=email)
            return None

        # Actualizar último login
        await self.update_last_login(user.id)

        logger.info("User authenticated successfully",
                   user_id=user.id,
                   email=email,
                   role=user.role)

        return user
```

---

## Integración con Log Aggregators

### ELK Stack (Elasticsearch, Logstash, Kibana)

**1. Configurar formato JSON:**
```bash
LOG_FORMAT=json
LOG_FILE=logs/app.log
```

**2. Logstash config:**
```ruby
input {
  file {
    path => "/app/logs/app.log"
    codec => "json"
  }
}

filter {
  # Opcional: parsear campos adicionales
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "fastapi-logs-%{+YYYY.MM.dd}"
  }
}
```

**3. Kibana queries:**
```
# Ver todos los errores
level: "ERROR"

# Ver requests de un usuario específico
user_id: 123

# Ver requests lentos (>1 segundo)
duration_ms: >1000

# Ver logs de un request específico
request_id: "550e8400-e29b-41d4-a716-446655440000"
```

---

### Grafana Loki

**1. Configurar formato JSON:**
```bash
LOG_FORMAT=json
```

**2. Promtail config:**
```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: fastapi
    static_configs:
      - targets:
          - localhost
        labels:
          job: fastapi
          __path__: /app/logs/app.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            message: message
            request_id: request_id
            user_id: user_id
```

**3. LogQL queries:**
```logql
# Ver logs de nivel ERROR
{job="fastapi"} | json | level="ERROR"

# Ver logs de un usuario
{job="fastapi"} | json | user_id="123"

# Ver requests lentos
{job="fastapi"} | json | duration_ms > 1000
```

---

### Datadog

**1. Configurar formato JSON:**
```bash
LOG_FORMAT=json
LOG_FILE=logs/app.log
```

**2. Datadog Agent config:**
```yaml
logs:
  - type: file
    path: /app/logs/app.log
    service: fastapi
    source: python
    sourcecategory: sourcecode
```

**3. Datadog queries:**
```
# Ver errores
@level:ERROR

# Ver logs de un request
@request_id:"550e8400-e29b-41d4-a716-446655440000"

# Ver requests lentos
@duration_ms:>1000
```

---

## Best Practices

### ✅ DO:

1. **Usa campos estructurados en vez de strings formateados:**
```python
# ✅ BIEN
logger.info("User created", user_id=123, email="user@example.com")

# ❌ MAL
logger.info(f"User {123} created with email user@example.com")
```

2. **Usa LogContext para evitar repetir campos:**
```python
# ✅ BIEN
with LogContext(user_id=123):
    logger.info("Processing started")
    logger.info("Step 1")
    logger.info("Completed")

# ❌ MAL (repetitivo)
logger.info("Processing started", user_id=123)
logger.info("Step 1", user_id=123)
logger.info("Completed", user_id=123)
```

3. **Loggea errores con contexto:**
```python
# ✅ BIEN
try:
    process_payment(payment_id)
except Exception as e:
    logger.error("Payment processing failed",
                payment_id=payment_id,
                amount=amount,
                error=str(e))
    raise

# ❌ MAL (sin contexto)
except Exception as e:
    logger.error(str(e))
```

4. **Usa niveles apropiados:**
```python
# ✅ BIEN
logger.debug("Cache miss", key="users:123")  # DEBUG para detalles
logger.info("User created", user_id=123)     # INFO para eventos normales
logger.warning("Rate limit exceeded")        # WARNING para anomalías
logger.error("Database query failed")        # ERROR para errores

# ❌ MAL (todo en INFO)
logger.info("Cache miss")
logger.info("User created")
logger.info("Rate limit exceeded")  # Debería ser WARNING
```

---

### ❌ DON'T:

1. **No uses print() en producción:**
```python
# ❌ MAL
print(f"User {user_id} created")

# ✅ BIEN
logger.info("User created", user_id=user_id)
```

2. **No loggees información sensible:**
```python
# ❌ MAL
logger.info("User login", password=password)  # ¡NUNCA!

# ✅ BIEN
logger.info("User login", user_id=user.id)
```

3. **No loggees en loops sin throttling:**
```python
# ❌ MAL
for item in items:  # 10,000 items
    logger.info("Processing item", item_id=item.id)  # 10,000 logs!

# ✅ BIEN
logger.info("Processing items", count=len(items))
for idx, item in enumerate(items):
    if (idx + 1) % 100 == 0:  # Log cada 100 items
        logger.info("Progress update", processed=idx+1, total=len(items))
```

4. **No uses f-strings para mensajes con datos variables:**
```python
# ❌ MAL
logger.info(f"User {user_id} uploaded {filename}")  # No parseable

# ✅ BIEN
logger.info("User uploaded file", user_id=user_id, filename=filename)
```

---

## Troubleshooting

### Los logs no aparecen

**1. Verificar nivel de log:**
```bash
# Si LOG_LEVEL=WARNING, solo verás WARNING, ERROR, CRITICAL
# Cambiar a INFO o DEBUG
LOG_LEVEL=INFO
```

**2. Verificar formato:**
```bash
# Si LOG_FORMAT=json, los logs están en JSON (difícil de leer en consola)
# Cambiar a text para desarrollo
LOG_FORMAT=text
```

---

### Logs duplicados

**Causa:** Múltiples handlers en el logger.

**Solución:** El sistema ya maneja esto automáticamente. Si ves duplicados, reinicia la aplicación.

---

### Request ID no aparece en logs

**Causa:** El `LoggingMiddleware` no está registrado.

**Solución:** Verificar que esté en `main.py`:
```python
app.add_middleware(LoggingMiddleware)
```

---

### Rotación de logs no funciona

**Causa:** `LOG_FILE` no está configurado.

**Solución:**
```bash
# Crear directorio de logs
mkdir -p logs

# Configurar en .env
LOG_FILE=logs/app.log
```

---

## Ejemplo Completo de Logs

**Request completo:**

```json
// 1. Request started (middleware)
{
  "timestamp": "2025-12-18T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.middleware.logging",
  "message": "Request started",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/users",
  "client_ip": "192.168.1.1"
}

// 2. User created (endpoint)
{
  "timestamp": "2025-12-18T10:30:45.234Z",
  "level": "INFO",
  "logger": "app.routes.users",
  "message": "User created successfully",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123,
  "email": "user@example.com",
  "role": "admin"
}

// 3. Request completed (middleware)
{
  "timestamp": "2025-12-18T10:30:45.456Z",
  "level": "INFO",
  "logger": "app.middleware.logging",
  "message": "Request completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_code": 201,
  "duration_ms": 333.45
}
```

**Todos estos logs están conectados por el mismo `request_id`**, permitiendo rastrear todo el flujo del request.

---

¡Listo! Ya tienes un sistema completo de logging estructurado con rastreo de requests, contextos y rotación de logs 🎉
