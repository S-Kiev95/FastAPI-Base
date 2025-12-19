# 🐳 Docker Setup Guide

Este documento explica cómo usar Docker para desarrollo y producción con PostgreSQL + pgvector y Redis.

## 📋 Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Desarrollo Local con Docker](#desarrollo-local-con-docker)
- [Producción con Docker](#producción-con-docker)
- [pgvector - Soporte de Vectores](#pgvector---soporte-de-vectores)
- [Comandos Útiles](#comandos-útiles)

---

## 📦 Requisitos Previos

- Docker Desktop instalado
- Docker Compose v2.0+

---

## 🔧 Desarrollo Local con Docker

### 1. Iniciar Servicios de Desarrollo

```bash
# Levantar PostgreSQL + Redis + pgAdmin + Redis Commander
docker-compose -f docker-compose.dev.yml up -d

# Ver logs
docker-compose -f docker-compose.dev.yml logs -f

# Solo PostgreSQL
docker-compose -f docker-compose.dev.yml logs -f postgres
```

### 2. Configurar Variables de Entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

Edita `.env` y cambia la conexión a PostgreSQL:

```env
# Cambia de SQLite
# DATABASE_URL=sqlite:///./app.db

# A PostgreSQL
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/fastapi_db

# Habilita Redis
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
```

### 3. Instalar Dependencias (con pgvector)

```bash
# Sincronizar dependencias incluyendo pgvector
uv sync
```

### 4. Ejecutar Migraciones

```bash
# Aplicar migraciones (incluye extensión pgvector)
uv run alembic upgrade head
```

### 5. Iniciar Backend

```bash
# Modo desarrollo
uv run uvicorn main:app --reload --port 8001
```

### 6. Acceder a las Herramientas

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| **Backend API** | http://localhost:8001 | - |
| **API Docs (Swagger)** | http://localhost:8001/docs | - |
| **PostgreSQL** | localhost:5432 | postgres / postgres123 |
| **pgAdmin** | http://localhost:5050 | admin@admin.com / admin |
| **Redis** | localhost:6379 | - |
| **Redis Commander** | http://localhost:8081 | - |

### 7. Detener Servicios

```bash
# Detener sin eliminar volúmenes
docker-compose -f docker-compose.dev.yml down

# Detener y eliminar volúmenes (limpia la BD)
docker-compose -f docker-compose.dev.yml down -v
```

---

## 🚀 Producción con Docker

### 1. Construir y Levantar Todo

```bash
# Construir imagen del backend y levantar servicios
docker-compose up -d --build

# Ver logs
docker-compose logs -f backend
```

### 2. Variables de Entorno de Producción

Crea un archivo `.env` para producción:

```env
# PostgreSQL
POSTGRES_DB=fastapi_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=TU_PASSWORD_SEGURO_AQUI

# Backend
SECRET_KEY=TU_SECRET_KEY_GENERADO_CON_OPENSSL
DATABASE_URL=postgresql://postgres:TU_PASSWORD_SEGURO_AQUI@postgres:5432/fastapi_db

# Redis
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0

# Storage (cambiar a S3 en producción)
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_REGION=us-east-1
S3_BUCKET=tu-bucket

# CORS
CORS_ORIGINS=https://tudominio.com,https://www.tudominio.com
```

### 3. Generar Secret Key

```bash
openssl rand -hex 32
```

### 4. Ejecutar Migraciones en Producción

```bash
# Dentro del contenedor
docker-compose exec backend alembic upgrade head
```

### 5. Escalar Servicios (Opcional)

```bash
# Múltiples instancias del backend
docker-compose up -d --scale backend=3
```

---

## 🧬 pgvector - Soporte de Vectores

### ¿Qué es pgvector?

**pgvector** es una extensión de PostgreSQL que permite almacenar y buscar vectores de embeddings de forma eficiente.

### Casos de Uso

El modelo `Media` incluye un campo `embedding` opcional que puedes usar para:

#### 1. **Text Embeddings** (Búsqueda Semántica)
```python
# Ejemplo con OpenAI
from openai import OpenAI

client = OpenAI()
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Descripción de la imagen"
)
embedding = response.data[0].embedding

# Guardar en media
media.embedding = embedding  # Lista de 512 floats
```

#### 2. **Image Embeddings** (Búsqueda por Similitud Visual)
```python
# Ejemplo con CLIP
import clip
import torch

model, preprocess = clip.load("ViT-B/32")
image = preprocess(Image.open("photo.jpg"))
with torch.no_grad():
    embedding = model.encode_image(image).cpu().numpy()[0].tolist()

media.embedding = embedding
```

#### 3. **Face Embeddings** (Reconocimiento Facial)
```python
# Ejemplo con DeepFace
from deepface import DeepFace

embedding = DeepFace.represent(
    img_path="face.jpg",
    model_name="Facenet512"
)[0]["embedding"]

media.embedding = embedding
```

#### 4. **Audio Embeddings** (Similitud de Audio/Voz)
```python
# Ejemplo con Resemblyzer
from resemblyzer import VoiceEncoder, preprocess_wav

encoder = VoiceEncoder()
wav = preprocess_wav("audio.wav")
embedding = encoder.embed_utterance(wav).tolist()

media.embedding = embedding
```

### Búsqueda por Similitud

```python
# Buscar media similar por embedding
from sqlmodel import select

def find_similar_media(embedding: List[float], limit: int = 10):
    statement = (
        select(Media)
        .order_by(Media.embedding.l2_distance(embedding))  # Distancia L2
        .limit(limit)
    )
    results = session.exec(statement).all()
    return results
```

### Tipos de Índices

La migración crea un índice **HNSW** (Hierarchical Navigable Small World):

```sql
CREATE INDEX idx_media_embedding_hnsw
ON media USING hnsw (embedding vector_l2_ops)
WITH (m = 16, ef_construction = 64)
```

**Parámetros:**
- `m`: Número de conexiones por nodo (mayor = más preciso, más memoria)
- `ef_construction`: Precisión en construcción (mayor = más lento, más preciso)

### Cambiar Dimensión del Vector

Por defecto el embedding es de **512 dimensiones**. Para cambiar:

```python
# En app/models/media.py
embedding: Optional[List[float]] = Field(
    default=None,
    sa_column=Column(Vector(1536))  # Cambiar a 1536 para OpenAI
)
```

Y actualiza la migración:

```python
# En alembic/versions/...
op.add_column('media', sa.Column('embedding', Vector(1536), nullable=True))
```

---

## 🛠️ Comandos Útiles

### Docker

```bash
# Ver contenedores corriendo
docker-compose ps

# Ver logs de un servicio específico
docker-compose logs -f postgres

# Ejecutar comando en contenedor
docker-compose exec postgres psql -U postgres -d fastapi_db

# Reiniciar un servicio
docker-compose restart backend

# Reconstruir imagen
docker-compose build backend

# Limpiar todo (⚠️ elimina volúmenes)
docker-compose down -v
docker system prune -a
```

### PostgreSQL

```bash
# Conectarse a PostgreSQL
docker-compose exec postgres psql -U postgres -d fastapi_db

# Verificar extensión pgvector
SELECT * FROM pg_extension WHERE extname = 'vector';

# Ver tablas
\dt

# Describir tabla media
\d media

# Salir
\q
```

### Redis

```bash
# Conectarse a Redis
docker-compose exec redis redis-cli

# Ver todas las keys
KEYS *

# Limpiar cache
FLUSHDB

# Salir
exit
```

### Backup de PostgreSQL

```bash
# Crear backup
docker-compose exec postgres pg_dump -U postgres fastapi_db > backup.sql

# Restaurar backup
docker-compose exec -T postgres psql -U postgres -d fastapi_db < backup.sql
```

---

## 📊 Monitoreo

### Health Checks

Todos los servicios tienen health checks configurados:

```bash
# Ver estado de salud
docker-compose ps

# Debería mostrar "healthy" en todos los servicios
```

### Logs de Producción

```bash
# Ver últimas 100 líneas
docker-compose logs --tail=100 backend

# Seguir logs en tiempo real
docker-compose logs -f backend

# Logs con timestamp
docker-compose logs -f -t backend
```

---

## 🔒 Seguridad

### Checklist de Producción

- [ ] Cambiar `SECRET_KEY` a un valor generado con `openssl rand -hex 32`
- [ ] Cambiar `POSTGRES_PASSWORD` a un password seguro
- [ ] Usar HTTPS con certificados SSL (Nginx)
- [ ] Limitar `CORS_ORIGINS` a dominios específicos
- [ ] No exponer puertos de PostgreSQL/Redis públicamente
- [ ] Usar secrets de Docker para contraseñas (en lugar de .env)
- [ ] Habilitar firewall y limitar acceso a puertos
- [ ] Configurar backups automáticos de PostgreSQL

---

## 🆘 Troubleshooting

### Error: "Cannot connect to PostgreSQL"

```bash
# Verificar que PostgreSQL esté corriendo
docker-compose ps postgres

# Ver logs de PostgreSQL
docker-compose logs postgres

# Reiniciar PostgreSQL
docker-compose restart postgres
```

### Error: "pgvector extension not found"

```bash
# Conectarse a PostgreSQL y verificar
docker-compose exec postgres psql -U postgres -d fastapi_db

# Habilitar extensión manualmente
CREATE EXTENSION IF NOT EXISTS vector;
```

### Limpiar Todo y Empezar de Nuevo

```bash
# Detener y eliminar todo
docker-compose down -v

# Eliminar imágenes
docker rmi $(docker images -q)

# Volver a construir
docker-compose up -d --build
```

---

## 📚 Recursos Adicionales

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don%27t_Do_This)
- [Redis Best Practices](https://redis.io/docs/getting-started/)
