#!/bin/bash
# RedCortex Monitoring Script
# Usage: ./scripts/monitor.sh

set -e

PROJECT_DIR="${PROJECT_DIR:-$HOME/Projects/RedCortex}"
DB_PATH="$PROJECT_DIR/data/library.db"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}     RedCortex Status Monitor${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running on Mac Mini or MacBook
if [ "$(hostname)" = "macmini" ] || [ "$(hostname)" = "Mac-mini" ]; then
    echo -e "${GREEN}📍 Running on: Mac Mini (Ingestion Server)${NC}"
else
    echo -e "${YELLOW}📍 Running on: $(hostname) (Development Machine)${NC}"
fi
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}⚠️  Database not found at $DB_PATH${NC}"
    exit 1
fi

# System Info
echo -e "${BLUE}System:${NC}"
echo "  Hostname: $(hostname)"
echo "  Uptime: $(uptime | awk -F',' '{print $1}' | awk '{print $3,$4}')"
echo "  Load: $(uptime | awk -F'load averages:' '{print $2}')"
echo ""

# Disk Usage
echo -e "${BLUE}Storage:${NC}"
df -h / | awk 'NR==2 {printf "  Used: %s/%s (%s)\n", $3, $2, $5}'
echo ""

# Database Stats
echo -e "${BLUE}Database Statistics:${NC}"
sqlite3 "$DB_PATH" <<EOF 2>/dev/null || echo "  Unable to query database"
SELECT '  Books: ' || COUNT(*) || ' total' FROM books;
SELECT '  Indexed: ' || COUNT(*) || ' books' FROM books WHERE status='indexed';
SELECT '  In Progress: ' || COUNT(*) || ' books' FROM books WHERE status='indexing';
SELECT '  Chunks: ' || COUNT(*) FROM chunks;
SELECT '  Total pages: ' || COALESCE(SUM(total_pages), 0) FROM books;
EOF
echo ""

# Recent Books
echo -e "${BLUE}Recently Indexed Books:${NC}"
sqlite3 "$DB_PATH" <<EOF 2>/dev/null || echo "  No books yet"
SELECT '  • ' || title || ' (' || status || ')' 
FROM books 
ORDER BY created_at DESC 
LIMIT 5;
EOF
echo ""

# Check Ollama
echo -e "${BLUE}Ollama Status:${NC}"
if pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}  ✅ Running${NC}"
    echo "  Models:"
    ollama list 2>/dev/null | grep -v "NAME" | awk '{print "    - " $1}' || echo "    (none)"
else
    echo -e "${YELLOW}  ⚠️  Not running${NC}"
fi
echo ""

# Check for running ingestion
if pgrep -f "ingest.py" > /dev/null; then
    echo -e "${GREEN}🔄 Ingestion is currently running${NC}"
    echo "  PID: $(pgrep -f "ingest.py")"
    echo "  Running since: $(ps -o lstart= -p $(pgrep -f "ingest.py"))"
else
    echo -e "${YELLOW}⏸️  No ingestion currently running${NC}"
fi
echo ""

# Recent log files
if [ -d "$PROJECT_DIR/logs" ]; then
    echo -e "${BLUE}Recent Log Files:${NC}"
    ls -lt "$PROJECT_DIR/logs" 2>/dev/null | head -6 | awk '{print "  " $6, $7, $8, $9}'
    echo ""
fi

# Last lines of most recent log
LATEST_LOG=$(ls -t "$PROJECT_DIR/logs"/ingest_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ]; then
    echo -e "${BLUE}Last 5 lines of current log:${NC}"
    tail -n 5 "$LATEST_LOG" | sed 's/^/  /'
    echo ""
fi

# Qdrant stats (if API key available)
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
    if [ -n "$QDRANT_API_KEY" ]; then
        echo -e "${BLUE}Qdrant Cloud Status:${NC}"
        # This would need Python to check properly, skip for now
        echo "  Check manually at: https://cloud.qdrant.io/"
    fi
fi

echo -e "${BLUE}========================================${NC}"
echo ""
echo "Useful commands:"
echo "  ./scripts/batch_ingest.sh  - Start ingestion"
echo "  tail -f logs/ingest_*.log  - Watch progress"
echo "  pkill -f ingest.py         - Stop ingestion"
echo ""
