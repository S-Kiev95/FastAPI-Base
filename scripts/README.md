# Scripts de Operaciones

Scripts para mantenimiento y operaciones del backend en producción.

## 📋 Scripts Disponibles

### backup.sh
Crea backups de PostgreSQL y opcionalmente los sube a S3.

**Uso:**
```bash
# Backup local
./scripts/backup.sh

# Backup local + upload a S3
./scripts/backup.sh --s3
```

**Variables de entorno:**
- `DB_HOST` - Host de PostgreSQL (default: localhost)
- `DB_PORT` - Puerto (default: 5432)
- `DB_NAME` - Nombre de la base de datos (default: seguros_db)
- `DB_USER` - Usuario de PostgreSQL (default: postgres)
- `DB_PASSWORD` - Password de PostgreSQL
- `BACKUP_DIR` - Directorio para backups (default: ./backups)
- `RETENTION_DAYS` - Días para retener backups (default: 7)
- `S3_BUCKET` - Bucket S3 para upload (opcional, ej: s3://my-backups/db/)

**Cron setup (backup diario a las 2 AM):**
```bash
crontab -e
# Agregar:
0 2 * * * /path/to/scripts/backup.sh --s3
```

---

### restore.sh
Restaura backups de PostgreSQL desde archivo local o S3.

**Uso:**
```bash
# Restore desde archivo local (con confirmación interactiva)
./scripts/restore.sh ./backups/backup_20260406_020000.dump

# Restore desde S3 con confirmación automática
./scripts/restore.sh s3://my-bucket/backup_20260406_020000.dump --confirm
```

**⚠️ ADVERTENCIA:** Esta operación es DESTRUCTIVA y eliminará todos los datos actuales.

**Variables de entorno:**
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (igual que backup.sh)

---

### db-maintenance.sh
Ejecuta tareas de mantenimiento rutinarias en PostgreSQL.

**Uso:**
```bash
# Ejecutar mantenimiento completo
./scripts/db-maintenance.sh
```

**Tareas ejecutadas:**
1. VACUUM ANALYZE (liberar espacio + actualizar estadísticas)
2. REINDEX DATABASE (reconstruir índices)
3. Limpieza de audit logs antiguos (> 1 año)
4. Purga de usuarios soft-deleted (> 30 días)
5. Análisis de tamaños de tablas
6. Verificación de table bloat

**Variables de entorno:**
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `AUDIT_LOG_RETENTION_DAYS` - Días para retener audit logs (default: 365)

**Cron setup (mantenimiento semanal los domingos a las 3 AM):**
```bash
0 3 * * 0 /path/to/scripts/db-maintenance.sh
```

---

## 🔐 Configuración de Passwords

Para evitar ingresar passwords interactivamente, crear archivo `~/.pgpass`:

```
# Format: hostname:port:database:username:password
localhost:5432:seguros_db:postgres:your-secure-password
```

```bash
chmod 600 ~/.pgpass
```

Alternativamente, usar variable de entorno:
```bash
export DB_PASSWORD="your-secure-password"
./scripts/backup.sh
```

---

## 📊 Logs y Monitoreo

Todos los scripts loggean a stdout con timestamps. Para logguear a archivo:

```bash
./scripts/backup.sh 2>&1 | tee -a /var/log/backups.log
```

---

## 🆘 Troubleshooting

**Error: "pg_dump: command not found"**
- Instalar PostgreSQL client: `sudo apt-get install postgresql-client`

**Error: "aws: command not found"**
- Instalar AWS CLI: `pip install awscli`
- Configurar credenciales: `aws configure`

**Error: "FATAL: password authentication failed"**
- Verificar `DB_PASSWORD` correcto
- Verificar `pg_hba.conf` permite conexiones
- Usar archivo `~/.pgpass`

**Backup muy lento**
- Usar formato custom (`-F c`) ya está habilitado
- Considerar aumentar `checkpoint_segments` en postgresql.conf
- Verificar I/O no está saturado

**REINDEX falla con "database is being accessed"**
- Script usa `REINDEX CONCURRENTLY` en PostgreSQL 12+
- Si no disponible, detener backend temporalmente
