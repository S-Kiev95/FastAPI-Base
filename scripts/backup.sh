#!/bin/bash
set -euo pipefail

# ============================================================================
# Database Backup Script
# ============================================================================
# Crea backups de PostgreSQL y los almacena localmente + S3 (opcional)
# Uso: ./scripts/backup.sh [--s3]
# ============================================================================

# Configuración (sobrescribir via environment variables)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-seguros_db}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
S3_BUCKET="${S3_BUCKET:-}"  # Opcional: s3://my-backups/db/

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump no encontrado. Instalar postgresql-client."
        exit 1
    fi

    if [[ "$1" == "--s3" ]] && ! command -v aws &> /dev/null; then
        log_error "AWS CLI no encontrado. Instalar aws-cli para backup a S3."
        exit 1
    fi
}

create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "Creando directorio de backups: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/backup_${DB_NAME}_${timestamp}.dump"

    log_info "Iniciando backup de $DB_NAME..."

    # Crear backup (custom format, comprimido)
    if PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -F c \
        -f "$backup_file"; then

        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Backup completado: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Backup falló"
        exit 1
    fi
}

upload_to_s3() {
    local backup_file="$1"

    if [[ -z "$S3_BUCKET" ]]; then
        log_warn "S3_BUCKET no configurado, saltando upload a S3"
        return 0
    fi

    log_info "Subiendo backup a S3: $S3_BUCKET"

    if aws s3 cp "$backup_file" "$S3_BUCKET/$(basename $backup_file)" --storage-class GLACIER_IR; then
        log_info "Upload a S3 exitoso"
    else
        log_error "Upload a S3 falló (backup local aún disponible)"
        return 1
    fi
}

cleanup_old_backups() {
    log_info "Limpiando backups antiguos (> $RETENTION_DAYS días)..."

    local deleted_count=0
    while IFS= read -r file; do
        if [[ -f "$file" ]]; then
            rm "$file"
            deleted_count=$((deleted_count + 1))
            log_info "Eliminado: $(basename $file)"
        fi
    done < <(find "$BACKUP_DIR" -name "backup_*.dump" -type f -mtime +$RETENTION_DAYS)

    log_info "Backups eliminados: $deleted_count"
}

# ============================================================================
# Main
# ============================================================================

main() {
    local upload_s3=false

    # Parse args
    for arg in "$@"; do
        case $arg in
            --s3)
                upload_s3=true
                shift
                ;;
        esac
    done

    log_info "=== Backup Script Iniciado ==="
    log_info "Database: $DB_NAME@$DB_HOST:$DB_PORT"
    log_info "Backup dir: $BACKUP_DIR"
    log_info "Retention: $RETENTION_DAYS días"

    check_dependencies "$@"
    create_backup_dir

    # Crear backup
    backup_file=$(create_backup)

    # Upload a S3 si habilitado
    if [[ "$upload_s3" == true ]]; then
        upload_to_s3 "$backup_file"
    fi

    # Limpiar backups antiguos
    cleanup_old_backups

    log_info "=== Backup Completado ==="
}

main "$@"
