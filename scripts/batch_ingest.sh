#!/bin/bash
# RedCortex 24/7 Batch Ingestion Script for Mac Mini
# Usage: ./scripts/batch_ingest.sh

set -e  # Exit on error

# Configuration
PROJECT_DIR="${PROJECT_DIR:-$HOME/Projects/RedCortex}"
BOOKS_DIR="$PROJECT_DIR/ML-Books"
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
# ML Books Collection
declare -a BOOKS=(
    "0812_Machine-Learning-for-Absolute-Beginners.pdf:Machine Learning for Absolute Beginners:ai_engineering"
    "AI Engineering.pdf:AI Engineering:ai_engineering"
    "Applied-Machine-Learning-and-AI-for-Engineers.pdf:Applied Machine Learning and AI for Engineers:ai_engineering"
    "Artificial Intelligence. A modern approach (Stuart Russell  Peter Norvig) (Z-Library).pdf:Artificial Intelligence A Modern Approach:ai_engineering"
    "Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf:Pattern Recognition and Machine Learning:ai_engineering"
    "Deep Learning by Ian Goodfellow, Yoshua Bengio, Aaron Courville.pdf:Deep Learning:ai_engineering"
    "Designing Machine Learning Systems An Iterative Process.pdf:Designing Machine Learning Systems:ai_engineering"
    "Gans-in-action-deep-learning-with-generative-adversarial-networks.pdf:GANs in Action:ai_engineering"
    "Generative-Deep-Learning.pdf:Generative Deep Learning:ai_engineering"
    "Hands-On Generative AI with Transformers and Diffusion Models (Omar Sanseviero, Pedro Cuenca etc.) (Z-Library).pdf:Hands-On Generative AI with Transformers:ai_engineering"
    "Hands-On Large Language Models Language Understanding and Generation (Jay Alammar, Maarten Grootendorst) (Z-Library).pdf:Hands-On Large Language Models:ai_engineering"
    "Hands-On Machine Learning with Pytorch.pdf:Hands-On Machine Learning with PyTorch:ai_engineering"
    "Hands-On Machine Learning with Scikit-Learn and PyTorch (Second Early Release) (Aurelien Geron) (Z-Library).pdf:Hands-On ML with Scikit-Learn and PyTorch:ai_engineering"
    "Hands-On_Machine_Learning_with_Scikit-Learn_Keras_and_Tensorflow_-_Aurelien_Geron.pdf:Hands-On ML with Scikit-Learn Keras and TensorFlow:ai_engineering"
    "LLM Engineers Handbook.pdf:LLM Engineers Handbook:ai_engineering"
    "ML Machine Learning-A Probabilistic Perspective.pdf:Machine Learning A Probabilistic Perspective:ai_engineering"
    "ML Math.pdf:Mathematics for Machine Learning:ai_engineering"
    "NLP with Transformer models.pdf:NLP with Transformer Models:ai_engineering"
    "Practical MLOps_ Operationalizing Machine Learning Models.pdf:Practical MLOps:ai_engineering"
    "Probabilistic Machine Learning Advanced Topics... (Z-Library).pdf:Probabilistic Machine Learning Advanced Topics:ai_engineering"
    "building-machine-learning-powered-applications-going-from-idea-to-product.pdf:Building ML Powered Applications:ai_engineering"
    "machine_learning.pdf:Machine Learning:ai_engineering"
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
    
    # Run ingestion (ingest.py is resume-capable)
    log_info "Starting ingestion (this may take 2-4 hours per book)..."
    if python "$PROJECT_DIR/src/ingestion/ingest.py" \
        "$PDF_PATH" \
        "$title" \
        "$category"; then
        
        log_success "Completed: $title"
        ((COMPLETED++))
    else
        EXIT_CODE=$?
        log_error "Failed with exit code $EXIT_CODE: $title"
        ((FAILED++))
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
