#!/bin/bash
# Sync data from Mac Mini back to MacBook Pro
# Usage: ./scripts/sync_to_macbook.sh [macbook_hostname_or_ip]

set -e

PROJECT_DIR="${PROJECT_DIR:-$HOME/Projects/RedCortex}"
MACBOOK_HOST="${1:-macbook-pro.local}"
MACBOOK_USER="${2:-$USER}"

echo "========================================"
echo "RedCortex Data Sync"
echo "From: Mac Mini ($(hostname))"
echo "To: MacBook Pro ($MACBOOK_USER@$MACBOOK_HOST)"
echo "========================================"
echo ""

# Check if target is reachable
echo "Checking connection to $MACBOOK_HOST..."
if ! ping -c 1 "$MACBOOK_HOST" &> /dev/null; then
    echo "❌ Cannot reach $MACBOOK_HOST"
    echo "Make sure both machines are on the same network"
    exit 1
fi
echo "✅ Connection OK"
echo ""

# Confirm sync
echo "This will sync:"
echo "  - data/library.db (SQLite database)"
echo "  - logs/ (all log files)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Create remote directory if needed
echo ""
echo "Setting up remote directories..."
ssh "$MACBOOK_USER@$MACBOOK_HOST" "mkdir -p ~/Projects/RedCortex/data ~/Projects/RedCortex/logs" || {
    echo "❌ Failed to connect via SSH"
    echo "Make sure SSH keys are set up:"
    echo "  ssh-copy-id $MACBOOK_USER@$MACBOOK_HOST"
    exit 1
}

# Sync database
echo ""
echo "Syncing database..."
rsync -avz --progress \
    "$PROJECT_DIR/data/library.db" \
    "$MACBOOK_USER@$MACBOOK_HOST:~/Projects/RedCortex/data/"

# Sync logs
echo ""
echo "Syncing logs..."
rsync -avz --progress \
    "$PROJECT_DIR/logs/" \
    "$MACBOOK_USER@$MACBOOK_HOST:~/Projects/RedCortex/logs/"

# Generate sync report
echo ""
echo "Generating sync report..."
REPORT_FILE="/tmp/sync_report_$(date +%Y%m%d_%H%M%S).txt"
cat > "$REPORT_FILE" <<EOF
RedCortex Sync Report
====================
Date: $(date)
Source: $(hostname) (Mac Mini)
Target: $MACBOOK_HOST (MacBook Pro)

Database Stats:
$(sqlite3 "$PROJECT_DIR/data/library.db" "SELECT 'Books: ' || COUNT(*) FROM books;")
$(sqlite3 "$PROJECT_DIR/data/library.db" "SELECT 'Chunks: ' || COUNT(*) FROM chunks;")
$(sqlite3 "$PROJECT_DIR/data/library.db" "SELECT 'Pages: ' || SUM(total_pages) FROM books;")

Indexed Books:
$(sqlite3 "$PROJECT_DIR/data/library.db" "SELECT title FROM books WHERE status='indexed';")

Files Synced:
$(ls -lh "$PROJECT_DIR/data/library.db" | awk '{print $9, $5}')
$(find "$PROJECT_DIR/logs" -name "*.log" | wc -l) log files
EOF

# Copy report
scp "$REPORT_FILE" "$MACBOOK_USER@$MACBOOK_HOST:~/Projects/RedCortex/logs/"

echo ""
echo "========================================"
echo "✅ Sync Complete!"
echo "========================================"
echo ""
cat "$REPORT_FILE"
echo ""
echo "Report saved to: logs/$(basename $REPORT_FILE)"

rm "$REPORT_FILE"
