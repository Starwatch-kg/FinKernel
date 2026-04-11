#!/bin/bash
# Database Backup and Disaster Recovery System

set -e

BACKUP_DIR="/backups"
RETENTION_DAYS=30
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-financedb}"
DB_USER="${DB_USER:-finuser}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARN:${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

backup_database() {
    log "Starting database backup..."

    BACKUP_FILE="$BACKUP_DIR/financedb_${TIMESTAMP}.sql.gz"

    # Perform backup
    if PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        | gzip > "$BACKUP_FILE"; then

        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"

        # Create metadata file
        cat > "$BACKUP_FILE.meta" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "database": "$DB_NAME",
  "size": "$BACKUP_SIZE",
  "host": "$DB_HOST",
  "backup_type": "full"
}
EOF

        echo "$BACKUP_FILE"
    else
        error "Backup failed"
        exit 1
    fi
}

rotate_backups() {
    log "Rotating old backups (retention: $RETENTION_DAYS days)..."

    find "$BACKUP_DIR" -name "financedb_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "financedb_*.sql.gz.meta" -type f -mtime +$RETENTION_DAYS -delete

    REMAINING=$(find "$BACKUP_DIR" -name "financedb_*.sql.gz" -type f | wc -l)
    log "Backup rotation complete. Remaining backups: $REMAINING"
}

restore_database() {
    BACKUP_FILE="$1"

    if [ -z "$BACKUP_FILE" ]; then
        error "No backup file specified"
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi

    if [ ! -f "$BACKUP_FILE" ]; then
        error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    warn "⚠️  WARNING: This will OVERWRITE the current database!"
    read -p "Are you sure you want to restore from $BACKUP_FILE? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log "Restore cancelled"
        exit 0
    fi

    log "Starting database restore from $BACKUP_FILE..."

    # Drop existing connections
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        2>/dev/null || true

    # Restore database
    if gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --quiet; then

        log "Database restored successfully from $BACKUP_FILE"
    else
        error "Restore failed"
        exit 1
    fi
}

list_backups() {
    log "Available backups:"
    echo ""

    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A $BACKUP_DIR/financedb_*.sql.gz 2>/dev/null)" ]; then
        warn "No backups found"
        exit 0
    fi

    for backup in "$BACKUP_DIR"/financedb_*.sql.gz; do
        if [ -f "$backup" ]; then
            SIZE=$(du -h "$backup" | cut -f1)
            DATE=$(stat -c %y "$backup" | cut -d' ' -f1,2 | cut -d'.' -f1)
            echo "  $(basename $backup) - $SIZE - $DATE"

            if [ -f "$backup.meta" ]; then
                echo "    Metadata: $(cat $backup.meta)"
            fi
        fi
    done
}

verify_backup() {
    BACKUP_FILE="$1"

    if [ -z "$BACKUP_FILE" ]; then
        error "No backup file specified"
        exit 1
    fi

    log "Verifying backup: $BACKUP_FILE"

    # Check if file exists and is readable
    if [ ! -f "$BACKUP_FILE" ]; then
        error "Backup file not found"
        exit 1
    fi

    # Check if gzip file is valid
    if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
        log "✅ Backup file is valid"
    else
        error "❌ Backup file is corrupted"
        exit 1
    fi

    # Check file size
    SIZE=$(stat -c%s "$BACKUP_FILE")
    if [ "$SIZE" -lt 1000 ]; then
        warn "⚠️  Backup file is suspiciously small ($SIZE bytes)"
    fi
}

# Main command dispatcher
case "${1:-backup}" in
    backup)
        BACKUP_FILE=$(backup_database)
        rotate_backups
        verify_backup "$BACKUP_FILE"
        ;;
    restore)
        restore_database "$2"
        ;;
    list)
        list_backups
        ;;
    verify)
        verify_backup "$2"
        ;;
    rotate)
        rotate_backups
        ;;
    *)
        echo "Usage: $0 {backup|restore|list|verify|rotate} [backup_file]"
        echo ""
        echo "Commands:"
        echo "  backup          - Create new database backup"
        echo "  restore <file>  - Restore database from backup"
        echo "  list            - List available backups"
        echo "  verify <file>   - Verify backup integrity"
        echo "  rotate          - Remove old backups"
        exit 1
        ;;
esac
