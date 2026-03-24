#!/bin/bash
# RedCortex 24/7 Batch Ingestion Script for Mac Mini
# Usage: ./scripts/batch_ingest.sh

set -e  # Exit on error

# Configuration
PROJECT_DIR="${PROJECT_DIR:-$HOME/Projects/RedCortex}"
BOOKS_DIR="$PROJECT_DIR/Redhat E-Books"
LOG_DIR="$PROJECT_DIR/logs"
VENV_DIR="$PROJECT_DIR/secondbrain"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Create log directory
mkdir -p "$LOG_DIR"

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/ingest_$TIMESTAMP.log"

# Redirect all output to log file and console
exec > >(tee -a "$LOG_FILE")
exec 2>&1

log_info "========================================"
log_info "RedCortex 24/7 Ingestion Started"
log_info "Project: $PROJECT_DIR"
log_info "Log file: $LOG_FILE"
log_info "========================================"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    log_error "Virtual environment not found at $VENV_DIR"
    log_info "Run: python3 -m venv secondbrain"
    exit 1
fi

# Activate environment
log_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Change to project directory
cd "$PROJECT_DIR"

# Check Python dependencies
log_info "Checking dependencies..."
python -c "import ollama, qdrant_client, requests" 2>/dev/null || {
    log_error "Missing dependencies. Run: pip install -r requirements.txt"
    exit 1
}

# Check Ollama
log_info "Checking Ollama..."
if ! pgrep -x "ollama" > /dev/null; then
    log_warn "Ollama not running. Starting..."
    export OLLAMA_KEEP_ALIVE=60m
    ollama serve &
    sleep 5
fi

# Verify Ollama has the model
if ! ollama list | grep -q "nomic-embed-text"; then
    log_info "Pulling nomic-embed-text model..."
    ollama pull nomic-embed-text
fi

log_success "Ollama is ready"

# Check for books
if [ ! -d "$BOOKS_DIR" ]; then
    log_error "Books directory not found: $BOOKS_DIR"
    exit 1
fi

# Count available PDFs
PDF_COUNT=$(find "$BOOKS_DIR" -name "*.pdf" -type f | wc -l)
log_info "Found $PDF_COUNT PDF files in $BOOKS_DIR"

if [ "$PDF_COUNT" -eq 0 ]; then
    log_error "No PDF files found to process"
    exit 1
fi

# Define books to process (filename:title:category)
# Add your books here
declare -a BOOKS=(
    "System Administration l-9.0-student-guide.pdf:Red Hat System Administration I:red_hat"
    "Enterprise Linux Automation with Ansible9.0.pdf:Enterprise Linux Automation:red_hat"
    "OpenShift Administration I Operating a Production Cluster-4.14.pdf:OpenShift Administration I:red_hat"
    "OpenShift Administration II Operating a Production Kubernetes Cluster4.12.pdf:OpenShift Administration II:red_hat"
    "OpenShift Administration III Scaling Kubernetes Deployments in the Enterprise4.10.pdf:OpenShift Administration III:red_hat"
    "Network Automation with Red Hat Ansible Automation Platform2.3.pdf:Network Automation:red_hat"
    "Enterprise Kubernetes Storage with Red Hat OpenShift Data Foundation4.7.pdf:Kubernetes Storage:red_hat"
    "Microsoft Windows Automation with Red Hat Ansible 2.8.pdf:Windows Automation:red_hat"
)

# Statistics
TOTAL_BOOKS=${#BOOKS[@]}
COMPLETED=0
FAILED=0
SKIPPED=0

log_info "Starting batch processing of $TOTAL_BOOKS books..."
log_info "Estimated time: $((TOTAL_BOOKS * 4)) hours (4 hours per book)"

# Process each book
for book_info in "${BOOKS[@]}"; do
    IFS=':' read -r filename title category <<< "$book_info"
    
    PDF_PATH="$BOOKS_DIR/$filename"
    
    # Check if file exists
    if [ ! -f "$PDF_PATH" ]; then
        log_warn "Book not found, skipping: $filename"
        ((SKIPPED++))
        continue
    fi
    
    # Check if already completed
    STATUS=$(sqlite3 "$PROJECT_DIR/data/library.db" \
        "SELECT status FROM books WHERE file_path = '$PDF_PATH' AND status = 'indexed';" 2>/dev/null || echo "")
    
    if [ "$STATUS" = "indexed" ]; then
        log_info "Already completed: $title"
        ((COMPLETED++))
        continue
    fi
    
    log_info ""
    log_info "========================================"
    log_info "Processing: $title"
    log_info "File: $filename"
    log_info "Category: $category"
    log_info "Started: $(date)"
    log_info "Progress: $COMPLETED/$TOTAL_BOOKS completed"
    log_info "========================================"
    
    # Run ingestion with 4-hour timeout
    # The ingest.py script is resume-capable, so timeouts are safe
    if timeout 14400 python "$PROJECT_DIR/src/ingestion/ingest.py" \
        "$PDF_PATH" \
        "$title" \
        "$category"; then
        
        log_success "Completed: $title"
        ((COMPLETED++))
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            log_warn "Timeout (4 hours): $title - will resume on next run"
        else
            log_error "Failed with exit code $EXIT_CODE: $title"
            ((FAILED++))
        fi
    fi
    
    # Show current stats
    log_info ""
    log_info "Current Stats:"
    log_info "  Completed: $COMPLETED"
    log_info "  Failed: $FAILED"
    log_info "  Skipped: $SKIPPED"
    
    # Sync database back (optional, if configured)
    if [ -n "$SYNC_TARGET" ]; then
        log_info "Syncing database..."
        rsync -az "$PROJECT_DIR/data/library.db" "$SYNC_TARGET" 2>/dev/null || true
    fi
    
    # Cool down between books
    if [ $COMPLETED -lt $TOTAL_BOOKS ]; then
        log_info "Cooling down for 60 seconds..."
        sleep 60
    fi
done

# Final summary
log_info ""
log_info "========================================"
log_info "Batch Processing Complete!"
log_info "========================================"
log_info "Total books: $TOTAL_BOOKS"
log_success "Completed: $COMPLETED"
log_error "Failed: $FAILED"
log_warn "Skipped: $SKIPPED"
log_info "Finished: $(date)"
log_info "Log file: $LOG_FILE"
log_info "========================================"

# Show final database stats
log_info ""
log_info "Database Statistics:"
sqlite3 "$PROJECT_DIR/data/library.db" <<EOF
SELECT 
    'Books: ' || COUNT(*) || ' (' || 
    SUM(CASE WHEN status='indexed' THEN 1 ELSE 0 END) || ' indexed)' 
FROM books;
SELECT 'Total chunks: ' || COUNT(*) FROM chunks;
SELECT 'Total pages indexed: ' || SUM(total_pages) FROM books WHERE status='indexed';
EOF

# Deactivate environment
deactivate

exit 0
