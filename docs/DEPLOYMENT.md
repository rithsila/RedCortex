# Mac Mini 24/7 Ingestion Deployment Guide

> Complete guide for deploying RedCortex on a Mac Mini for continuous book ingestion.

## 📋 Prerequisites

- Mac Mini (M1/M2/M4 recommended)
- macOS 12+ (Monterey or later)
- SSH access enabled
- Stable internet connection
- External storage (optional, for 1000+ books)

---

## 1. Initial Setup on Mac Mini

### 1.1 System Requirements

```bash
# Check macOS version
sw_vers -productVersion

# Check available storage
df -h /

# Check memory
system_profiler SPHardwareDataType | grep Memory
```

**Recommended:**
- macOS 13+ (Ventura/Sonoma)
- 16GB+ RAM (for Ollama)
- 100GB+ free storage

### 1.2 Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 1.3 Install Ollama

```bash
brew install ollama

# Pull embedding model (~500MB)
ollama pull nomic-embed-text

# Test Ollama
ollama run nomic-embed-text
# Type /bye to exit
```

### 1.4 Install Python

```bash
brew install python@3.10

# Verify
python3 --version  # Should show 3.10+
```

---

## 2. Project Deployment

### 2.1 Copy Project from MacBook Pro

**Option A: Using rsync (recommended)**

```bash
# On Mac Mini, create directory
mkdir -p ~/Projects
cd ~/Projects

# From MacBook Pro, run:
rsync -avz --exclude 'secondbrain' \
  --exclude '__pycache__' \
  --exclude '.kimi' \
  --exclude 'data/library.db' \
  ~/Projects/RedCortex/ \
  user@macmini.local:~/Projects/RedCortex/
```

**Option B: Using USB/External Drive**

```bash
# Copy to drive on MacBook
cp -r ~/Projects/RedCortex /Volumes/ExternalDrive/

# Copy from drive on Mac Mini
cp -r /Volumes/ExternalDrive/RedCortex ~/Projects/
```

**Option C: Using Git (if you pushed to repo)**

```bash
# On Mac Mini
cd ~/Projects
git clone <your-repo-url>
cd RedCortex
```

### 2.2 Setup Python Environment

```bash
cd ~/Projects/RedCortex

# Create virtual environment
python3 -m venv secondbrain

# Activate
source secondbrain/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2.3 Copy Configuration

**From your MacBook Pro, copy the `.env` file:**

```bash
# Secure copy
scp ~/.env user@macmini.local:~/Projects/RedCortex/.env
```

**Or manually create on Mac Mini:**

```bash
cd ~/Projects/RedCortex
nano .env
```

Add your credentials:
```bash
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-key-here
OPENROUTER_API_KEY=your-key-here
```

### 2.4 Copy Existing Database (Optional)

If you want to continue from current progress:

```bash
# From MacBook Pro
scp data/library.db user@macmini.local:~/Projects/RedCortex/data/
```

---

## 3. Testing the Setup

### 3.1 Verify Installation

```bash
cd ~/Projects/RedCortex
source secondbrain/bin/activate

# Test database
python src/utils/init_db.py

# Test Qdrant connection
python tests/test_qdrant.py

# Test ingestion (small sample)
python tests/test_ingest.py
```

### 3.2 Test with One Book

```bash
# Copy one PDF for testing
scp "Redhat E-Books/System Administration l-9.0-student-guide.pdf" \
  user@macmini.local:~/Projects/RedCortex/Redhat\ E-Books/

# Run ingestion test
cd ~/Projects/RedCortex
source secondbrain/bin/activate
python src/ingestion/ingest.py \
  "Redhat E-Books/System Administration l-9.0-student-guide.pdf" \
  "Test Book" \
  red_hat
```

---

## 4. 24/7 Ingestion Setup

### 4.1 Copy All Books

```bash
# From MacBook Pro - copy all books
rsync -avz ~/Projects/RedCortex/Redhat\ E-Books/ \
  user@macmini.local:~/Projects/RedCortex/Redhat\ E-Books/
```

### 4.2 Create Ingestion Script

Create `scripts/batch_ingest.sh`:

```bash
#!/bin/bash
# 24/7 Batch Ingestion Script

set -e  # Exit on error

PROJECT_DIR="$HOME/Projects/RedCortex"
BOOKS_DIR="$PROJECT_DIR/Redhat E-Books"
LOG_DIR="$PROJECT_DIR/logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Activate environment
source "$PROJECT_DIR/secondbrain/bin/activate"
cd "$PROJECT_DIR"

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/ingest_$TIMESTAMP.log"

# Books to process
BOOKS=(
    "Enterprise Kubernetes Storage with Red Hat OpenShift Data Foundation4.7.pdf:Enterprise Kubernetes Storage:red_hat"
    "Enterprise Linux Automation with Ansible9.0.pdf:Enterprise Linux Automation:red_hat"
    "Microsoft Windows Automation with Red Hat Ansible 2.8.pdf:Windows Automation with Ansible:red_hat"
    "Network Automation with Red Hat Ansible Automation Platform2.3.pdf:Network Automation:red_hat"
    "OpenShift Administration I Operating a Production Cluster-4.14.pdf:OpenShift Admin I:red_hat"
    "OpenShift Administration II Operating a Production Kubernetes Cluster4.12.pdf:OpenShift Admin II:red_hat"
    "OpenShift Administration III Scaling Kubernetes Deployments in the Enterprise4.10.pdf:OpenShift Admin III:red_hat"
)

# Process each book
for book_info in "${BOOKS[@]}"; do
    IFS=':' read -r filename title category <<< "$book_info"
    
    PDF_PATH="$BOOKS_DIR/$filename"
    
    if [ ! -f "$PDF_PATH" ]; then
        echo "⚠️  Book not found: $filename" | tee -a "$LOG_FILE"
        continue
    fi
    
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Processing: $title" | tee -a "$LOG_FILE"
    echo "Started: $(date)" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    
    # Run ingestion with timeout (4 hours per book max)
    timeout 14400 python src/ingestion/ingest.py \
        "$PDF_PATH" \
        "$title" \
        "$category" \
        2>&1 | tee -a "$LOG_FILE"
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Completed: $title" | tee -a "$LOG_FILE"
    elif [ $EXIT_CODE -eq 124 ]; then
        echo "⏰ Timeout: $title (will resume on next run)" | tee -a "$LOG_FILE"
    else
        echo "❌ Error ($EXIT_CODE): $title" | tee -a "$LOG_FILE"
    fi
    
    echo "Finished: $(date)" | tee -a "$LOG_FILE"
    
    # Sleep between books to let system cool down
    echo "Sleeping 60 seconds..." | tee -a "$LOG_FILE"
    sleep 60
done

echo "" | tee -a "$LOG_FILE"
echo "🎉 Batch processing complete!" | tee -a "$LOG_FILE"
```

Make executable:
```bash
chmod +x scripts/batch_ingest.sh
```

### 4.3 Create LaunchDaemon for Auto-Start (Optional)

Create `~/Library/LaunchAgents/com.redcortex.ingest.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.redcortex.ingest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/YOUR_USERNAME/Projects/RedCortex/scripts/batch_ingest.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Projects/RedCortex/logs/launchd.out</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Projects/RedCortex/logs/launchd.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
```

Load the daemon:
```bash
launchctl load ~/Library/LaunchAgents/com.redcortex.ingest.plist
```

### 4.4 Simple Cron Alternative (Easier)

Edit crontab:
```bash
crontab -e
```

Add:
```bash
# Run ingestion daily at 2 AM
0 2 * * * cd ~/Projects/RedCortex && ./scripts/batch_ingest.sh >> logs/cron.log 2>&1

# Or run continuously with restart every 6 hours
0 */6 * * * pkill -f "ingest.py"; sleep 5; cd ~/Projects/RedCortex && ./scripts/batch_ingest.sh >> logs/cron.log 2>&1
```

---

## 5. Monitoring & Management

### 5.1 Check Progress

```bash
# SSH into Mac Mini
ssh user@macmini.local

# Check current status
cd ~/Projects/RedCortex
source secondbrain/bin/activate

# Database stats
sqlite3 data/library.db "SELECT title, status, total_pages FROM books;"
sqlite3 data/library.db "SELECT COUNT(*) as chunks FROM chunks;"

# Qdrant stats
python -c "
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv
load_dotenv()
client = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY'))
info = client.get_collection('books_hot')
print(f'Vectors: {info.points_count}')
"
```

### 5.2 Monitor Logs

```bash
# Live log tail
tail -f ~/Projects/RedCortex/logs/ingest_*.log

# Check recent logs
ls -lt ~/Projects/RedCortex/logs/ | head -20

# Search for errors
grep -i "error\|failed\|timeout" ~/Projects/RedCortex/logs/ingest_*.log
```

### 5.3 System Monitoring

```bash
# Check CPU/Memory
htop

# Or use Activity Monitor GUI
open -a "Activity Monitor"

# Check Ollama is running
ps aux | grep ollama

# Check disk space
df -h
```

### 5.4 Restart Ingestion

If ingestion stops:

```bash
# Kill any stuck processes
pkill -f "ingest.py"
pkill -f "ollama"

# Restart Ollama
ollama serve &

# Resume ingestion
cd ~/Projects/RedCortex
source secondbrain/bin/activate
python src/ingestion/ingest.py \
  "Redhat E-Books/BOOK_NAME.pdf" \
  "Book Title" \
  red_hat
```

---

## 6. Power Management

### 6.1 Prevent Sleep During Ingestion

```bash
# Prevent sleep (run in terminal)
caffeinate -i &

# Or use built-in macOS command
pmset -c sleep 0  # Disable sleep on AC power
```

### 6.2 Energy Saver Settings

```bash
# Show current settings
pmset -g

# Recommended settings for 24/7 operation
sudo pmset -c sleep 0          # Never sleep on AC
sudo pmset -c displaysleep 10  # Display sleep after 10 min
sudo pmset -c autopoweroff 0   # Disable auto power off
```

### 6.3 Auto-Restart on Power Failure

System Preferences → Energy Saver → "Start up automatically after a power failure"

---

## 7. Sync Data Back to MacBook Pro

### 7.1 Automatic Sync Script

Create `scripts/sync_back.sh`:

```bash
#!/bin/bash
# Sync completed data back to MacBook Pro

MACBOOK_USER="your_macbook_username"
MACBOOK_IP="your_macbook_ip_or_hostname"
PROJECT_DIR="$HOME/Projects/RedCortex"

echo "Syncing data back to MacBook Pro..."

# Sync database
rsync -avz "$PROJECT_DIR/data/library.db" \
  "$MACBOOK_USER@$MACBOOK_IP:~/Projects/RedCortex/data/"

# Sync logs for reference
rsync -avz "$PROJECT_DIR/logs/" \
  "$MACBOOK_USER@$MACBOOK_IP:~/Projects/RedCortex/logs/"

echo "✅ Sync complete!"
```

### 7.2 Manual Sync

```bash
# On Mac Mini, run:
rsync -avz ~/Projects/RedCortex/data/library.db \
  user@macbook-pro.local:~/Projects/RedCortex/data/
```

### 7.3 Cloud Backup (Optional)

```bash
# Backup to iCloud
cp ~/Projects/RedCortex/data/library.db \
  ~/Library/Mobile\ Documents/com~apple~CloudDocs/RedCortex/

# Or use rclone for other cloud services
rclone sync ~/Projects/RedCortex/data/ remote:RedCortex-backup/
```

---

## 8. Troubleshooting

### 8.1 Ollama Crashes Frequently

```bash
# Check Ollama logs
tail -f ~/.ollama/logs/server.log

# Restart Ollama with more memory
pkill ollama
OLLAMA_KEEP_ALIVE=60m ollama serve &

# Reduce batch size in ingest.py
# Edit: DELAY = 0.5  # Increase delay
```

### 8.2 Network Issues

```bash
# Test Qdrant connectivity
curl -H "api-key: YOUR_KEY" \
  https://your-cluster.cloud.qdrant.io/collections

# Check internet
ping cloud.qdrant.io
```

### 8.3 Disk Space Full

```bash
# Check what's using space
du -sh ~/* 2>/dev/null | sort -hr | head -20

# Clean old logs
cd ~/Projects/RedCortex/logs
rm -f ingest_2024*.log  # Keep only recent logs
```

### 8.4 SSH Access Issues

```bash
# Enable SSH on Mac Mini
sudo systemsetup -setremotelogin on

# Check SSH service
sudo launchctl list | grep ssh

# Test connection from MacBook
ssh user@macmini.local
```

---

## 9. Performance Optimization

### 9.1 Ollama Performance

```bash
# Keep model loaded longer
export OLLAMA_KEEP_ALIVE=60m

# Use GPU if available (Apple Silicon)
ollama serve &
```

### 9.2 System Performance

```bash
# Disable unnecessary services
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.metadata.mds.plist

# Check thermal throttling
sudo powermetrics --samplers smc | grep -i thermal
```

### 9.3 Network Optimization

```bash
# Use wired ethernet if possible
# Check connection speed
ifconfig en0  # WiFi
ifconfig en1  # Ethernet
```

---

## 10. Security Considerations

### 10.1 Secure SSH Access

```bash
# Use key-based auth only
ssh-copy-id user@macmini.local

# Disable password auth in /etc/ssh/sshd_config
# PasswordAuthentication no
```

### 10.2 Protect .env File

```bash
# Set proper permissions
chmod 600 ~/Projects/RedCortex/.env

# Never commit to git
echo ".env" >> .gitignore
```

### 10.3 Firewall Rules

```bash
# Enable firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on

# Allow SSH
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/sbin/sshd
```

---

## 📞 Quick Reference

| Command | Purpose |
|---------|---------|
| `ssh user@macmini.local` | Remote access |
| `tail -f logs/ingest_*.log` | Monitor progress |
| `sqlite3 data/library.db "SELECT * FROM books;"` | Check book status |
| `pkill -f ingest.py` | Stop ingestion |
| `ollama serve &` | Start Ollama |
| `rsync -avz data/library.db user@macbook:~/Projects/RedCortex/data/` | Sync back |

---

## ✅ Pre-Deployment Checklist

- [ ] Mac Mini has macOS 12+
- [ ] Homebrew installed
- [ ] Ollama installed and tested
- [ ] Python 3.10+ installed
- [ ] Project copied to ~/Projects/RedCortex
- [ ] .env file configured with API keys
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Test ingestion successful
- [ ] All PDFs copied to Redhat E-Books/
- [ ] batch_ingest.sh created and executable
- [ ] Log directory created
- [ ] Sleep disabled for AC power
- [ ] SSH access working
- [ ] Sync script configured (optional)

---

**Ready to deploy! 🚀**
