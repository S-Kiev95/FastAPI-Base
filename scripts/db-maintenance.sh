#!/bin/bash
set -euo pipefail

# ============================================================================
# Database Maintenance Script
# ============================================================================
# Ejecuta tareas de mantenimiento en PostgreSQL:
# - VACUUM ANALYZE (liberar espacio, actualizar estadísticas)
# - REINDEX (reconstruir índices)
# - Limpieza de audit logs antiguos
# - Purga de usuarios soft-deleted
# ============================================================================

# Configuración
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-seguros_db}"
DB_USER="${DB_USER:-postgres}"
AUDIT_LOG_RETENTION_DAYS="${AUDIT_LOG_RETENTION_DAYS:-365}"  # 1 año

# Colores
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

run_query() {
    local query="$1"
    local description="$2"

    log_info "$description..."

    PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "$query"
}

vacuum_analyze() {
    log_info "Ejecutando VACUUM ANALYZE..."

    PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "VACUUM ANALYZE;"

    log_info "VACUUM ANALYZE completado"
}

reindex_database() {
    log_info "Reconstruyendo índices (REINDEX)..."

    # REINDEX DATABASE requiere que no haya conexiones activas
    # En producción, mejor usar REINDEX CONCURRENTLY (PostgreSQL 12+)

    PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "REINDEX DATABASE CONCURRENTLY $DB_NAME;" 2>/dev/null || {
            log_warn "REINDEX CONCURRENTLY no soportado, usando REINDEX normal"
            PGPASSWORD="${DB_PASSWORD:-}" psql \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d postgres \
                -c "REINDEX DATABASE $DB_NAME;"
        }

    log_info "REINDEX completado"
}

cleanup_audit_logs() {
    log_info "Limpiando audit logs antiguos (> $AUDIT_LOG_RETENTION_DAYS días)..."

    local deleted=$(PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t \
        -c "DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '$AUDIT_LOG_RETENTION_DAYS days' RETURNING id;" | wc -l)

    log_info "Audit logs eliminados: $deleted"
}

purge_soft_deleted_users() {
    log_info "Purgando usuarios soft-deleted (> 30 días)..."

    # Usuarios marcados para eliminación hace más de 30 días
    local deleted=$(PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t \
        -c "DELETE FROM users WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days' RETURNING id;" | wc -l)

    log_info "Usuarios purgados: $deleted"
}

analyze_table_sizes() {
    log_info "Analizando tamaños de tablas..."

    PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"
}

check_bloat() {
    log_info "Verificando table bloat..."

    PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_table_size(schemaname||'.'||tablename)) as size,
    CASE
        WHEN pg_table_size(schemaname||'.'||tablename) = 0 THEN 0
        ELSE ROUND((pg_total_relation_size(schemaname||'.'||tablename)::numeric - pg_table_size(schemaname||'.'||tablename)::numeric) / pg_table_size(schemaname||'.'||tablename)::numeric * 100, 2)
    END AS bloat_pct
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_table_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"

    log_warn "Si bloat_pct > 20%, considerar VACUUM FULL (requiere downtime)"
}

# ============================================================================
# Main
# ============================================================================

main() {
    log_info "=== Database Maintenance Script ==="
    log_info "Database: $DB_NAME@$DB_HOST:$DB_PORT"
    log_info ""

    # Verificar conexión
    if ! PGPASSWORD="${DB_PASSWORD:-}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
        log_error "No se puede conectar a PostgreSQL"
        exit 1
    fi

    # Maintenance tasks
    vacuum_analyze
    reindex_database
    cleanup_audit_logs
    purge_soft_deleted_users

    # Reporting
    log_info ""
    log_info "=== Database Stats ==="
    analyze_table_sizes
    check_bloat

    log_info ""
    log_info "=== Maintenance Completado ==="
}

main "$@"
