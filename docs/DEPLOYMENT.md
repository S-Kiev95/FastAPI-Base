# 🚀 Guía de Deployment

Guía completa paso a paso para desplegar el backend SaaS en producción.

---

## 📑 Índice

1. [Prerequisitos](#prerequisitos)
2. [Opción 1: Setup Wizard Visual (Recomendado)](#opción-1-setup-wizard-visual-recomendado)
3. [Opción 2: Setup Manual](#opción-2-setup-manual)
4. [Opción 3: Docker Compose](#opción-3-docker-compose)
5. [Opción 4: Cloud Platforms](#opción-4-cloud-platforms)
6. [Verificación Post-Deploy](#verificación-post-deploy)
7. [Troubleshooting](#troubleshooting)

---

## ✅ Prerequisitos

Antes de comenzar, asegúrate de tener:

### Software Requerido
- [ ] **Python 3.13+** (`python --version`)
- [ ] **uv** package manager (`pip install uv` o `brew install uv`)
- [ ] **PostgreSQL 15+** con extensión pgvector
- [ ] **Redis 7+**
- [ ] **Git**
- [ ] **Node.js 18+** (para admin UI)
- [ ] **Docker & Docker Compose** (opcional)

### Servicios Externos (Opcional)
- [ ] **S3 bucket** (AWS S3, MinIO, Backblaze B2)
- [ ] **SMTP server** (SendGrid, AWS SES, Mailgun)
- [ ] **Payment gateway** (Stripe, MercadoPago, Polar)
- [ ] **Sentry** account para error tracking
- [ ] **Dominio + SSL certificate** para producción

### Verificación de Prerequisitos

```bash
# Verificar Python
python --version  # Debe ser 3.13+

# Verificar PostgreSQL con pgvector
psql -c "SELECT * FROM pg_available_extensions WHERE name='vector';"
# Debe mostrar "vector" en los resultados

# Verificar Redis
redis-cli ping  # Debe responder "PONG"

# Verificar uv
uv --version
```

---

## 🎨 Opción 1: Setup Wizard Visual (Recomendado)

El proyecto incluye un **Setup Wizard visual** que te guía por todas las configuraciones necesarias, validando cada una en tiempo real.

### Paso 1: Clonar el Repositorio

```bash
git clone <url-del-repo> mi-proyecto-saas
cd mi-proyecto-saas
```

### Paso 2: Instalar Dependencias

```bash
# Backend
uv sync

# Admin UI (opcional, para rebuild)
cd admin-ui && npm install && cd ..
```

### Paso 3: Iniciar el Backend en Modo Setup

```bash
uv run python main.py
```

Al iniciar sin archivo `.env` configurado, el backend detectará automáticamente que necesita setup y te redirigirá al wizard.

### Paso 4: Abrir el Setup Wizard

Navega a: **http://localhost:8000/admin/setup**

### Paso 5: Completar el Wizard

El wizard te guiará por estos pasos:

```mermaid
flowchart LR
    S1[1. Database] --> S2[2. Redis]
    S2 --> S3[3. Security]
    S3 --> S4[4. Storage]
    S4 --> S5[5. Email]
    S5 --> S6[6. Payment]
    S6 --> S7[7. Admin User]
    S7 --> S8[8. Review & Deploy]

    style S1 fill:#3b82f6,color:#fff
    style S8 fill:#10b981,color:#fff
```

**Cada paso:**
- ✅ Muestra qué campos son **obligatorios** vs **opcionales**
- ✅ **Valida la conexión** antes de continuar (ej: testa conexión a PostgreSQL)
- ✅ Verifica **pgvector** esté instalado en PostgreSQL
- ✅ Permite **omitir pasos opcionales** (ej: saltar Stripe si no usas billing)
- ✅ Guarda la configuración en `.env` al finalizar

### Paso 6: Reiniciar el Backend

Al finalizar el wizard, reinicia el backend para aplicar la configuración:

```bash
# Detener (Ctrl+C) y volver a iniciar
uv run python main.py
```

### Paso 7: Verificar que Todo Funciona

```bash
curl http://localhost:8000/health
# Debe retornar: {"status": "healthy", ...}
```

---

## 🔧 Opción 2: Setup Manual

Si prefieres configurar todo manualmente:

### Paso 1: Clonar y Dependencias

```bash
git clone <url-del-repo> mi-proyecto
cd mi-proyecto
uv sync
```

### Paso 2: Crear archivo `.env`

```bash
cp .env.production.example .env
nano .env  # Editar variables
```

**Variables mínimas requeridas:**

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb

# Security
SECRET_KEY=<generar-con-openssl-rand-hex-32>

# Environment
ENVIRONMENT=production
```

### Paso 3: Generar SECRET_KEY

```bash
openssl rand -hex 32
# Copiar el output al .env como SECRET_KEY
```

### Paso 4: Crear Base de Datos

```bash
# Crear DB
createdb mi_proyecto

# Habilitar pgvector
psql -d mi_proyecto -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Paso 5: Ejecutar Migraciones

```bash
uv run alembic upgrade head
```

### Paso 6: Crear Admin User

Se crea automáticamente al iniciar si están configurados:

```bash
SYSTEM_ADMIN_EMAIL=admin@yourdomain.com
SYSTEM_ADMIN_PASSWORD=SuperSecurePass123!
```

### Paso 7: Iniciar el Servidor

```bash
uv run python main.py
```

---

## 🐳 Opción 3: Docker Compose

### Setup Rápido con Docker

```bash
# 1. Clonar
git clone <url-del-repo> mi-proyecto
cd mi-proyecto

# 2. Copiar env
cp .env.production.example .env
# Editar .env con tus valores

# 3. Iniciar stack completo
docker-compose up -d

# 4. Ejecutar migraciones
docker-compose exec backend alembic upgrade head

# 5. Ver logs
docker-compose logs -f backend
```

### Servicios Incluidos

```mermaid
graph TB
    subgraph "docker-compose.yml"
        BACKEND[Backend FastAPI<br/>:8000]
        DB[PostgreSQL<br/>:5432]
        REDIS[Redis<br/>:6379]
        WORKER[ARQ Worker]
    end

    subgraph "docker-compose.dev.yml (extras)"
        PGADMIN[pgAdmin<br/>:5050]
        RCOMMANDER[Redis Commander<br/>:8081]
    end

    BACKEND --> DB
    BACKEND --> REDIS
    WORKER --> REDIS
    WORKER --> DB

    PGADMIN -.-> DB
    RCOMMANDER -.-> REDIS
```

### Comandos Útiles

```bash
# Ver estado
docker-compose ps

# Ver logs de un servicio
docker-compose logs -f backend
docker-compose logs -f worker

# Entrar a un contenedor
docker-compose exec backend bash

# Reiniciar un servicio
docker-compose restart backend

# Escalar backend (3 instancias)
docker-compose up -d --scale backend=3

# Escalar workers
docker-compose up -d --scale worker=5

# Detener todo
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v
```

---

## ☁️ Opción 4: Cloud Platforms

### AWS (ECS + RDS + ElastiCache)

```mermaid
graph TB
    subgraph "AWS Infrastructure"
        ALB[Application<br/>Load Balancer]
        ECS[ECS Fargate]
        RDS[(RDS PostgreSQL)]
        EC[(ElastiCache Redis)]
        S3[S3 Bucket]
        SES[SES Email]
        CW[CloudWatch Logs]
    end

    USERS[Users] --> ALB
    ALB --> ECS
    ECS --> RDS
    ECS --> EC
    ECS --> S3
    ECS --> SES
    ECS --> CW
```

**Pasos:**
1. Crear RDS PostgreSQL con pgvector
2. Crear ElastiCache Redis cluster
3. Crear S3 bucket
4. Crear ECR repository, push imagen
5. Crear ECS task definition con variables de entorno
6. Crear ALB con target group
7. Ejecutar migraciones: `ecs run-task --task-definition migrations`

### Google Cloud (Cloud Run + Cloud SQL + Memorystore)

```bash
# Build & push imagen
gcloud builds submit --tag gcr.io/PROJECT/backend

# Deploy a Cloud Run
gcloud run deploy backend \
  --image gcr.io/PROJECT/backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env.yaml \
  --allow-unauthenticated
```

### Railway (Más simple)

1. Crear cuenta en [railway.app](https://railway.app)
2. "New Project" → "Deploy from GitHub repo"
3. Agregar servicios: PostgreSQL, Redis
4. Configurar variables de entorno
5. Deploy automático en cada push

### Render

1. Crear cuenta en [render.com](https://render.com)
2. "New" → "Web Service" → conectar repo
3. Agregar PostgreSQL y Redis add-ons
4. Configurar variables de entorno
5. Deploy

### Fly.io

```bash
# Instalar flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Inicializar
fly launch

# Deploy
fly deploy
```

---

## ✔️ Verificación Post-Deploy

Después de desplegar, verifica que todo funciona correctamente:

### 1. Health Check

```bash
curl https://api.yourdomain.com/health
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "database": "connected",
  "redis": "connected",
  "storage": "connected"
}
```

### 2. API Docs

Visita: `https://api.yourdomain.com/docs`

Deberías ver la documentación Swagger interactiva.

### 3. Test de Registro

```bash
curl -X POST https://api.yourdomain.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!",
    "name": "Test User"
  }'
```

### 4. Test de Login

```bash
curl -X POST https://api.yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!"
  }'
```

### 5. Métricas Prometheus

```bash
curl https://api.yourdomain.com/metrics
```

### 6. Admin Panel

Visita: `https://api.yourdomain.com/admin`

Login con las credenciales configuradas en `SYSTEM_ADMIN_EMAIL`.

### 7. Checklist Post-Deploy

- [ ] Health check responde 200 OK
- [ ] API docs accesibles
- [ ] Registro y login funcionan
- [ ] Admin panel accesible
- [ ] Métricas en `/metrics`
- [ ] Logs sin errores
- [ ] Sentry recibiendo eventos (si está configurado)
- [ ] SSL certificate válido
- [ ] Rate limiting funcionando (probar con muchos requests)
- [ ] Webhooks de payment gateway configurados
- [ ] Backups automatizados configurados (cron)

---

## 🐛 Troubleshooting

### Error: "relation does not exist"

**Causa:** Migraciones no ejecutadas.

**Solución:**
```bash
uv run alembic upgrade head
```

### Error: "FATAL: password authentication failed"

**Causa:** Credenciales de DB incorrectas.

**Solución:**
1. Verificar `DATABASE_URL` en `.env`
2. Probar conexión: `psql $DATABASE_URL`
3. Verificar permisos del usuario en PostgreSQL

### Error: "extension 'vector' does not exist"

**Causa:** pgvector no instalado.

**Solución:**
```bash
# Ubuntu/Debian
sudo apt install postgresql-15-pgvector

# macOS
brew install pgvector

# Habilitar en la DB
psql -d $DB_NAME -c "CREATE EXTENSION vector;"
```

### Error: "Connection refused" en Redis

**Causa:** Redis no está corriendo.

**Solución:**
```bash
# Verificar status
redis-cli ping

# Iniciar Redis
sudo systemctl start redis
# O con Docker:
docker run -d --name redis -p 6379:6379 redis:7
```

### Error: "Invalid SECRET_KEY"

**Causa:** `SECRET_KEY` muy corta o no configurada.

**Solución:**
```bash
# Generar nueva clave
openssl rand -hex 32

# Actualizar .env
SECRET_KEY=<nueva-clave>
```

### Error: "CORS policy blocked"

**Causa:** Dominio no en `CORS_ORIGINS`.

**Solución:**
```bash
# En .env
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Error: "S3 access denied"

**Causa:** Credenciales o permisos IAM incorrectos.

**Solución:**
1. Verificar `S3_ACCESS_KEY` y `S3_SECRET_KEY`
2. Verificar bucket policy permite `PutObject`, `GetObject`
3. Testar: `aws s3 ls s3://your-bucket/`

### Rate Limit Exceeded Masivo

**Causa:** Redis no funcionando o mal configurado.

**Solución:**
```bash
# Verificar Redis
redis-cli ping

# Verificar config
grep REDIS .env

# Deshabilitar temporal si necesario
REDIS_ENABLED=false
```

### Backend no inicia: "Port 8000 already in use"

**Solución:**
```bash
# Encontrar proceso usando el puerto
lsof -i :8000
# O en Windows:
netstat -ano | findstr :8000

# Matar el proceso
kill -9 <PID>
```

### Migraciones fallan: "target database is not up to date"

**Solución:**
```bash
# Ver estado actual
uv run alembic current

# Aplicar pendientes
uv run alembic upgrade head

# Si hay conflictos, forzar:
uv run alembic stamp head
uv run alembic upgrade head
```

### Tests fallan después de deploy

```bash
# Correr tests
uv run pytest tests/ -v

# Ver qué falla
uv run pytest tests/ -v --tb=short

# Solo tests específicos
uv run pytest tests/test_auth.py -v
```

---

## 📞 Soporte

Si encuentras problemas no cubiertos aquí:

1. Revisa los logs: `docker-compose logs backend --tail=100`
2. Verifica Sentry (si está configurado)
3. Consulta `docs/ARCHITECTURE.md` para entender el sistema
4. Consulta `docs/OPERATIONS.md` para operaciones avanzadas

---

## 📚 Siguientes Pasos

Después de desplegar exitosamente:

1. **Configurar dominio y SSL** (Let's Encrypt con nginx/Caddy)
2. **Configurar backups automatizados** (ver `scripts/backup.sh`)
3. **Configurar monitoring** (Grafana dashboard incluido)
4. **Configurar alertas** (Sentry + PagerDuty/Slack)
5. **Configurar CI/CD** (GitHub Actions incluido)
6. **Revisar security checklist** en `docs/ARCHITECTURE.md`
7. **Personalizar admin panel** en `admin-ui/`
8. **Agregar tus propios modelos** siguiendo el BaseService pattern

---

**¡Listo! Tu backend SaaS está en producción.** 🎉
