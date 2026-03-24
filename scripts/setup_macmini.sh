#!/bin/bash
# Mac Mini Setup Script for RedCortex
# Run this on the Mac Mini for initial setup

set -e

PROJECT_DIR="$HOME/Projects/RedCortex"
VENV_DIR="$PROJECT_DIR/secondbrain"

echo "========================================"
echo "RedCortex Mac Mini Setup"
echo "========================================"
echo ""

# Check macOS version
echo "Checking macOS version..."
MACOS_VERSION=$(sw_vers -productVersion)
echo "  macOS: $MACOS_VERSION"

if [[ $(echo "$MACOS_VERSION 12.0" | awk '{print ($1 < $2)}') -eq 1 ]]; then
    echo "❌ macOS 12.0+ required"
    exit 1
fi
echo "✅ macOS version OK"
echo ""

# Check if running on Apple Silicon
echo "Checking hardware..."
if [[ $(uname -m) == "arm64" ]]; then
    echo "✅ Apple Silicon detected (M1/M2/M4)"
else
    echo "⚠️  Intel Mac detected (slower embeddings)"
fi
echo ""

# Install Homebrew if needed
echo "Checking Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add to PATH for Apple Silicon
    if [[ -f /opt/homebrew/bin/brew ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew installed"
fi
echo ""

# Install Python
echo "Installing Python..."
brew install python@3.10
brew link python@3.10 --force || true
echo "✅ Python installed"
echo ""

# Install Ollama
echo "Installing Ollama..."
brew install ollama
echo "✅ Ollama installed"
echo ""

# Create project directory
echo "Setting up project directory..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
echo "  Project directory: $PROJECT_DIR"
echo ""

# Check if project files exist
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "⚠️  Project files not found!"
    echo "Please copy the project files first:"
    echo "  From MacBook: rsync -avz ~/Projects/RedCortex/ user@macmini.local:~/Projects/RedCortex/"
    exit 1
fi
echo "✅ Project files found"
echo ""

# Create virtual environment
echo "Creating Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate and install dependencies
echo "Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"
echo "✅ Dependencies installed"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/Redhat E-Books"
echo "✅ Directories created"
echo ""

# Setup .env file
echo "Setting up environment configuration..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  .env file not found!"
    echo "Please create $PROJECT_DIR/.env with your API keys:"
    echo ""
    echo "QDRANT_URL=https://your-cluster.cloud.qdrant.io"
    echo "QDRANT_API_KEY=your-key"
    echo "OPENROUTER_API_KEY=your-key"
    echo ""
    
    # Create template
    cat > "$PROJECT_DIR/.env.template" <<EOF
# Copy this to .env and fill in your keys
QDRANT_URL=
QDRANT_API_KEY=
OPENROUTER_API_KEY=
EOF
    echo "Template created at: $PROJECT_DIR/.env.template"
else
    echo "✅ .env file exists"
fi
echo ""

# Pull Ollama model
echo "Pulling Ollama embedding model..."
ollama pull nomic-embed-text
echo "✅ Model downloaded"
echo ""

# Configure system settings for 24/7 operation
echo "Configuring system for 24/7 operation..."

# Disable sleep on AC power
sudo pmset -c sleep 0
sudo pmset -c autopoweroff 0
sudo pmset -c displaysleep 10

echo "✅ Sleep disabled on AC power"
echo "✅ Display sleep set to 10 minutes"
echo ""

# Initialize database
echo "Initializing database..."
source "$VENV_DIR/bin/activate"
python "$PROJECT_DIR/src/utils/init_db.py"
echo ""

# Test Qdrant connection (if .env is configured)
if [ -f "$PROJECT_DIR/.env" ] && grep -q "QDRANT_API_KEY" "$PROJECT_DIR/.env"; then
    echo "Testing Qdrant connection..."
    source "$PROJECT_DIR/.env"
    if [ -n "$QDRANT_API_KEY" ]; then
        python "$PROJECT_DIR/src/utils/setup_collection.py" || {
            echo "⚠️  Qdrant connection failed - check your API keys"
        }
    fi
else
    echo "⚠️  Skipping Qdrant test (no API keys configured)"
fi
echo ""

# Make scripts executable
echo "Setting up scripts..."
chmod +x "$PROJECT_DIR/scripts/"*.sh
echo "✅ Scripts made executable"
echo ""

# Create LaunchAgent plist (optional)
echo "Creating LaunchAgent for auto-start..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.redcortex.ingest.plist"
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.redcortex.ingest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PROJECT_DIR/scripts/batch_ingest.sh</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/launchd.out</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/launchd.err</string>
</dict>
</plist>
EOF

echo "✅ LaunchAgent created at: $PLIST_PATH"
echo "   To enable: launchctl load $PLIST_PATH"
echo ""

# Final summary
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Project location: $PROJECT_DIR"
echo "Virtual environment: $VENV_DIR"
echo ""
echo "Next steps:"
echo ""
echo "1. Copy your PDF books to:"
echo "   $PROJECT_DIR/Redhat E-Books/"
echo ""
echo "2. Configure API keys in:"
echo "   $PROJECT_DIR/.env"
echo ""
echo "3. Test the setup:"
echo "   cd $PROJECT_DIR"
echo "   source secondbrain/bin/activate"
echo "   ./scripts/monitor.sh"
echo ""
echo "4. Start ingestion:"
echo "   ./scripts/batch_ingest.sh"
echo ""
echo "5. Monitor progress:"
echo "   ./scripts/monitor.sh"
echo "   tail -f logs/ingest_*.log"
echo ""
echo "6. Sync back to MacBook when done:"
echo "   ./scripts/sync_to_macbook.sh macbook-pro.local"
echo ""
