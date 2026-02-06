#!/bin/bash
# Database Health Check Script
# Verifies that all required tables exist and are accessible

set -e

DB_PATH="${1:-ai-assistant.db}"

echo "🔍 Checking database: $DB_PATH"
echo ""

# Check if database file exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database file not found: $DB_PATH"
    exit 1
fi

# Check database file size
DB_SIZE=$(stat -f%z "$DB_PATH" 2>/dev/null || stat -c%s "$DB_PATH" 2>/dev/null)
if [ "$DB_SIZE" -eq 0 ]; then
    echo "❌ Database file is empty (0 bytes)"
    exit 1
fi

# Format size in human-readable format (cross-platform)
format_size() {
    local size=$1
    if [ "$size" -lt 1024 ]; then
        echo "${size} bytes"
    elif [ "$size" -lt 1048576 ]; then
        echo "$(( size / 1024 )) KB"
    else
        echo "$(( size / 1048576 )) MB"
    fi
}

echo "✅ Database file exists ($(format_size $DB_SIZE))"

# Expected tables
EXPECTED_TABLES=(
    "User"
    "Session"
    "Task"
    "TaskExecution"
    "ActivityLog"
    "Notification"
    "AiMemory"
    "DigestSettings"
    "_prisma_migrations"
)

echo ""
echo "📋 Checking tables..."

MISSING_TABLES=()

for table in "${EXPECTED_TABLES[@]}"; do
    if sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';" | grep -q "$table"; then
        COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM $table;")
        echo "  ✅ $table (${COUNT} rows)"
    else
        echo "  ❌ $table (MISSING)"
        MISSING_TABLES+=("$table")
    fi
done

# Check migration status
echo ""
echo "🔄 Migration status:"
MIGRATION_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM _prisma_migrations;")
echo "  Migrations applied: $MIGRATION_COUNT"

if [ $MIGRATION_COUNT -eq 0 ]; then
    echo "  ⚠️  No migrations recorded - database may not be initialized"
fi

# Summary
echo ""
if [ ${#MISSING_TABLES[@]} -eq 0 ]; then
    echo "✅ Database health check PASSED"
    echo "   All ${#EXPECTED_TABLES[@]} expected tables exist and are accessible"
    exit 0
else
    echo "❌ Database health check FAILED"
    echo "   Missing ${#MISSING_TABLES[@]} tables: ${MISSING_TABLES[*]}"
    echo ""
    echo "   To fix, run:"
    echo "   cd frontend && npx prisma migrate deploy"
    exit 1
fi
