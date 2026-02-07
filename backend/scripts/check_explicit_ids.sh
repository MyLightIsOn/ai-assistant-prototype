#!/bin/bash

# Check for explicit UUID IDs in model creation
echo "🔍 Checking for explicit UUID IDs in code..."

# Get repository root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    REPO_ROOT="."
fi

# Change to repository root
cd "$REPO_ROOT"

# Search for problematic patterns
PATTERNS=(
    'id=str(uuid.uuid4())'
    'id=uuid.uuid4()'
    'id=f"log_'
    'createdAt=datetime'
    'startedAt=datetime'
)

FOUND=0

for pattern in "${PATTERNS[@]}"; do
    FILES=$(find backend -name "*.py" -type f -not -path "*/tests/*" -not -path "*/migrations/*" -exec grep -l "$pattern" {} \; 2>/dev/null)
    if [ ! -z "$FILES" ]; then
        echo "❌ Found explicit ID/timestamp pattern: $pattern"
        echo "   Files:"
        for file in $FILES; do
            echo "   - $file"
            grep -n "$pattern" "$file" | head -3
        done
        FOUND=1
    fi
done

if [ $FOUND -eq 1 ]; then
    echo ""
    echo "❌ BLOCKED: Explicit IDs or timestamps found in code"
    echo "   Let SQLAlchemy defaults handle ID and timestamp generation"
    echo "   Remove id= and timestamp= parameters from model constructors"
    exit 1
else
    echo "✅ No explicit IDs or timestamps found"
    exit 0
fi
