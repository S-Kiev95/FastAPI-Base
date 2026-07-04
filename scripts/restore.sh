#!/bin/bash
set -euo pipefail

# ============================================================================
# Database Restore Script
# ============================================================================
# Restaura backups de PostgreSQL desde archivo local o S3
# Uso: ./scripts/restore.sh <backup_file> [--confirm]
# ============================================================================

# Configuración
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-seguros_db}"
DB_USER="${DB_USER:-postgres}"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# Funciones
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    if ! command -v pg_restore &> /dev/null; then
        log_error "pg_restore no encontrado. Instalar postgresql-client."
        exit 1
    fi
}

confirm_restore() {
    local backup_file="$1"

    log_warn "============================================"
    log_warn "ADVERTENCIA: Esta operación es DESTRUCTIVA"
    log_warn "============================================"
    log_warn "Base de datos: $DB_NAME"
    log_warn "Backup file: $backup_file"
    log_warn ""
    log_warn "Se eliminarán TODOS los datos actuales y se reemplazarán con el backup."
    log_warn ""

    if [[ "$2" == "--confirm" ]]; then
        log_info "Confirmación automática activada (--confirm flag)"
        return 0
    fi

    read -p "¿Continuar con el restore? (escribir 'YES' para confirmar): " confirmation

    if [[ "$confirmation" != "YES" ]]; then
        log_error "Restore cancelado por el usuario"
        exit 1
    fi
}

download_from_s3() {
    local s3_path="$1"
    local local_file="./backups/$(basename $s3_path)"

    log_info "Descargando backup desde S3: $s3_path"

    if aws s3 cp "$s3_path" "$local_file"; then
        log_info "Download completado: $local_file"
        echo "$local_file"
    else
        log_error "Download desde S3 falló"
        exit 1
    fi
}

restore_backup() {
    local backup_file="$1"

    log_info "Iniciando restore de $backup_file..."

    # Verificar que el archivo existe
    if [[ ! -f "$backup_file" ]]; then
        log_error "Archivo no encontrado: $backup_file"
        exit 1
    fi

    # Verificar conexión a DB
    if ! PGPASSWORD="${DB_PASSWORD:-}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c '\q' 2>/dev/null; then
        log_error "No se puede conectar a PostgreSQL"
        exit 1
    fi

    # Terminar conexiones activas (necesario para restore limpio)
    log_info "Terminando conexiones activas..."
    PGPASSWORD="${DB_PASSWORD:-}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres <<EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
EOF

    # Restore con --clean (drop existing objects first)
    log_info "Restaurando backup..."
    if PGPASSWORD="${DB_PASSWORD:-}" pg_restore \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges \
        "$backup_file"; then

        log_info "Restore completado exitosamente"
    else
        log_error "Restore falló (algunos warnings son normales)"
        log_warn "Verificar estado de la base de datos manualmente"
        exit 1
    fi
}

verify_restore() {
    log_info "Verificando restore..."

    # Contar tablas
    local table_count=$(PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t \
        -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

    log_info "Tablas en DB: $(echo $table_count | xargs)"

    # Contar usuarios
    local user_count=$(PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t \
        -c "SELECT COUNT(*) FROM users WHERE deleted_at IS NULL;" 2>/dev/null || echo "0")

    log_info "Usuarios activos: $(echo $user_count | xargs)"

    log_info "Verificación completada"
}

# ============================================================================
# Main
# ============================================================================

main() {
    if [[ $# -lt 1 ]]; then
        log_error "Uso: $0 <backup_file> [--confirm]"
        log_info "Ejemplos:"
        log_info "  $0 ./backups/backup_20260406_020000.dump"
        log_info "  $0 s3://my-bucket/backup_20260406_020000.dump --confirm"
        exit 1
    fi

    local backup_file="$1"
    local confirm_flag="${2:-}"

    log_info "=== Restore Script Iniciado ==="

    check_dependencies

    # Si es S3 path, descargar primero
    if [[ "$backup_file" =~ ^s3:// ]]; then
        backup_file=$(download_from_s3 "$backup_file")
    fi

    # Confirmar operación destructiva
    confirm_restore "$backup_file" "$confirm_flag"

    # Ejecutar restore
    restore_backup "$backup_file"

    # Verificar resultado
    verify_restore

    log_info "=== Restore Completado ==="
    log_warn "IMPORTANTE: Verificar la aplicación funciona correctamente"
    log_warn "Ejecutar migraciones si es necesario: alembic upgrade head"
}

main "$@"
