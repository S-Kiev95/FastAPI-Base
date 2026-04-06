# Guía de Operaciones — Producción

Esta guía cubre el despliegue, mantenimiento y monitoreo del backend SaaS en producción.

---

## 📦 Despliegue en Producción

### Requisitos Previos

- Docker & Docker Compose instalados
- PostgreSQL 15+ con extensión pgvector
- Redis 7+
- Dominio configurado con SSL/TLS (Let's Encrypt recomendado)
- S3-compatible storage (AWS S3, MinIO, Backblaze B2)
- Servicio SMTP (SendGrid, AWS SES, Mailgun)

### 1. Configuración de Variables de Entorno

Copiar `.env.production.example` a `.env` y configurar:

```bash
# Environment
ENVIRONMENT=production

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/seguros_db

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-redis-password

# Security
SECRET_KEY=your-256-bit-secret-key-here-use-openssl-rand
ENFORCE_STRONG_PASSWORDS=true

# CORS (dominios permitidos separados por coma)
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# S3 Storage
USE_S3=true
S3_BUCKET_NAME=your-bucket
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key

# SMTP
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@yourdomain.com

# Observability
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1

# Admin
SYSTEM_ADMIN_EMAIL=admin@yourdomain.com
SYSTEM_ADMIN_PASSWORD=use-strong-password-here

# Billing
ACTIVE_PAYMENT_GATEWAY=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 2. Iniciar Servicios con Docker

```bash
# Production stack (PostgreSQL + Redis + Backend + ARQ workers)
docker-compose up -d

# Ver logs
docker-compose logs -f backend

# Ver estado de servicios
docker-compose ps
```

### 3. Aplicar Migraciones

```bash
# Ejecutar dentro del contenedor
docker-compose exec backend alembic upgrade head

# O desde el host con uv
uv run alembic upgrade head
```

### 4. Crear Usuario Administrador

El sistema creará automáticamente el usuario admin en el primer inicio si `SYSTEM_ADMIN_EMAIL` y `SYSTEM_ADMIN_PASSWORD` están configurados.

Verificar en logs:
```
INFO: Admin user created: admin@yourdomain.com
```

---

## 🔒 Seguridad en Producción

### Checklist Pre-Launch

- [ ] `ENVIRONMENT=production` configurado
- [ ] `SECRET_KEY` generado aleatoriamente (mínimo 256 bits)
- [ ] `ENFORCE_STRONG_PASSWORDS=true`
- [ ] CORS configurado con dominios específicos (NO usar `*`)
- [ ] SSL/TLS habilitado (HSTS se activa automáticamente)
- [ ] Credenciales de DB/Redis/S3/SMTP en secrets manager (AWS Secrets, Vault)
- [ ] Firewall configurado (solo puertos 80, 443 expuestos)
- [ ] Rate limiting habilitado (Redis required)
- [ ] Sentry DSN configurado para error tracking
- [ ] Logs enviados a agregador centralizado (CloudWatch, Datadog)

### Generar SECRET_KEY Seguro

```bash
openssl rand -hex 32
```

---

## 💾 Backups

### Base de Datos (PostgreSQL)

**Backup automático diario:**

```bash
# Configurar cron job (ejecutar como root)
crontab -e

# Agregar línea (backup diario a las 2 AM)
0 2 * * * /path/to/scripts/backup.sh
```

**Backup manual:**

```bash
# Ejecutar script de backup
./scripts/backup.sh

# O manualmente
pg_dump -h localhost -U user -d seguros_db -F c -f backup_$(date +%Y%m%d_%H%M%S).dump
```

**Restaurar backup:**

```bash
# Ejecutar script de restore
./scripts/restore.sh backup_20260406_020000.dump

# O manualmente
pg_restore -h localhost -U user -d seguros_db -c backup_20260406_020000.dump
```

### Archivos S3

Los archivos en S3 deben tener versionado habilitado y lifecycle policies configuradas:

```json
{
  "Rules": [
    {
      "Id": "DeleteOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
```

### Retention Policy Recomendado

- **Diarios**: mantener 7 días
- **Semanales**: mantener 4 semanas
- **Mensuales**: mantener 12 meses

---

## 📊 Monitoreo

### Health Checks

**Endpoint principal:**
```bash
curl https://api.yourdomain.com/health
```

Respuesta esperada (200 OK):
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

**Health checks extendidos (autenticado):**
```bash
curl -H "Authorization: Bearer $TOKEN" https://api.yourdomain.com/health/extended
```

### Prometheus Metrics

Endpoint: `/metrics`

**Métricas clave disponibles:**

- `fastapi_requests_total` — Total de requests por endpoint
- `fastapi_request_duration_seconds` — Latencia de requests
- `fastapi_requests_in_progress` — Requests activos
- `websocket_connections_active` — Conexiones WebSocket activas
- `cache_hits_total` / `cache_misses_total` — Cache hit rate
- `db_connections_active` — Conexiones DB activas

### Grafana Dashboard

Importar dashboard pre-configurado:

```bash
# Dashboard JSON en monitoring/grafana-dashboard.json
# Importar en Grafana UI: Dashboards → Import → Upload JSON
```

**Paneles incluidos:**
- Request rate y latencia (p50, p95, p99)
- Error rate (4xx, 5xx)
- Cache hit rate
- DB query performance
- WebSocket connections
- ARQ task queue stats

### Alertas Recomendadas

**Configurar en Grafana / PagerDuty:**

1. **Error rate > 5%** (últimos 5 min) → Critical
2. **Latencia p95 > 1s** → Warning
3. **DB connections > 80%** del pool → Warning
4. **Disk usage > 85%** → Warning
5. **Memory usage > 90%** → Critical
6. **Health check failing** → Critical

---

## 🛠️ Mantenimiento

### Database Maintenance

**Ejecutar semanalmente:**

```bash
# Script automatizado
./scripts/db-maintenance.sh

# O comandos manuales
psql -h localhost -U user -d seguros_db -c "VACUUM ANALYZE;"
psql -h localhost -U user -d seguros_db -c "REINDEX DATABASE seguros_db;"
```

### Limpiar Registros Antiguos

**Audit logs (retener 1 año):**

```sql
-- Ejecutar mensualmente
DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '1 year';
```

**Usuarios soft-deleted (purgar después de 30 días):**

```bash
# Endpoint admin autenticado
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.yourdomain.com/admin/purge-deleted-users
```

**Media files huérfanos (sin DB reference):**

```bash
# Pendiente: implementar script de limpieza S3
./scripts/cleanup-orphaned-media.sh
```

### Rotación de Logs

**Docker logs:**

Configurar en `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**Application logs:**

Si usas `LOG_FILE`, configurar logrotate:

```bash
# /etc/logrotate.d/fastapi-backend
/var/log/fastapi/app.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 www-data www-data
}
```

---

## 🚀 Escalabilidad

### Horizontal Scaling

**Backend instances:**

```bash
# Escalar a 3 réplicas
docker-compose up -d --scale backend=3

# Load balancer (nginx) en docker-compose.yml ya configurado
```

**ARQ workers:**

```bash
# Escalar workers para tasks asíncronos
docker-compose up -d --scale arq-worker=5
```

### Vertical Scaling

**Ajustar recursos en docker-compose.yml:**

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

### Database Connection Pool

Ajustar en código si necesario (`app/database/connection.py`):

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Conexiones persistentes
    max_overflow=40,     # Conexiones adicionales bajo carga
    pool_pre_ping=True,  # Health check antes de usar
)
```

---

## 🔧 Troubleshooting

### Logs

```bash
# Backend logs
docker-compose logs -f backend --tail=100

# Worker logs
docker-compose logs -f arq-worker --tail=100

# Database logs
docker-compose logs -f postgres --tail=100

# Redis logs
docker-compose logs -f redis --tail=100
```

### Problemas Comunes

**1. "Rate limit exceeded" masivo**

- Verificar Redis funcionando: `redis-cli ping`
- Revisar config `REDIS_ENABLED=true`
- Ajustar límites en `app/middleware/rate_limit.py` si necesario

**2. Tareas ARQ no se procesan**

- Verificar workers corriendo: `docker-compose ps arq-worker`
- Revisar logs: `docker-compose logs arq-worker`
- Verificar conexión Redis

**3. Errores 500 sin traza**

- Verificar Sentry DSN configurado
- Revisar logs: `docker-compose logs backend | grep ERROR`
- Habilitar debug temporal: `LOG_LEVEL=DEBUG`

**4. DB connection pool exhausted**

- Aumentar `pool_size` y `max_overflow` en engine
- Escalar backend horizontalmente
- Investigar slow queries: `pg_stat_statements`

**5. OOM (Out of Memory)**

- Revisar memory leak: `docker stats`
- Aumentar límites: `memory: 4G` en docker-compose
- Reducir `pool_size` / `max_overflow`

---

## 📖 Recursos Adicionales

- **Alembic Migrations:** `alembic --help`
- **ARQ Task Queue:** https://arq-docs.helpmanual.io/
- **Prometheus Metrics:** `/metrics` (formato OpenMetrics)
- **API Docs:** `/docs` (Swagger UI)
- **Sentry Error Tracking:** Dashboard en sentry.io

---

## 🆘 Soporte

Para problemas críticos en producción:

1. Revisar health checks: `/health`
2. Revisar Sentry dashboard (errores recientes)
3. Revisar logs: `docker-compose logs -f backend --tail=500`
4. Escalar temporalmente: `docker-compose up -d --scale backend=5`
5. Rollback si necesario: `docker-compose down && git checkout <previous-commit> && docker-compose up -d`

**Emergency Contacts:**
- On-call Engineer: [configurar PagerDuty]
- Database Admin: [contacto]
- DevOps Lead: [contacto]
