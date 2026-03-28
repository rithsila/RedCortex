# RedCortex Deployment Guide

| Document | Details |
|----------|---------|
| **Project** | RedCortex - RAG System for Technical Documentation |
| **Version** | 2.2.0 |
| **Last Updated** | 2026-03-26 |
| **Environment** | Mac Mini (macOS) / Linux |
| **Status** | Production Ready |

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [System Requirements](#system-requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Deployment Procedures](#deployment-procedures)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [Appendix](#appendix)

---

## Overview

This guide covers the deployment of RedCortex, a production-grade Retrieval-Augmented Generation (RAG) system for technical books. The deployment targets a Mac Mini for 24/7 continuous book ingestion with hybrid search (BM25 + Vector), cross-encoder reranking, and query caching.

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Mac Mini      │────▶│   Qdrant Cloud   │◀────│   MacBook Pro   │
│  (Ingestion)    │     │   (Vector DB)    │     │   (Query/Dev)   │
│                 │     └──────────────────┘     └─────────────────┘
│  • Ollama       │               │
│  • SQLite       │     ┌─────────▼──────────┐
│  • Python       │     │   OpenRouter API   │
└─────────────────┘     │   (LLM Queries)    │
                        └────────────────────┘
```

---

## Prerequisites

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Apple Silicon M1 / x86_64 | M2/M4 Pro |
| RAM | 8 GB | 16 GB+ |
| Storage | 50 GB free | 100 GB+ SSD |
| Network | 10 Mbps | 100 Mbps+ |

### Software

- macOS 12+ (Monterey) or Linux (Ubuntu 22.04+)
- SSH access enabled
- Stable internet connection
- Git (optional, for version control)

### External Services

| Service | Purpose | Setup Required |
|---------|---------|----------------|
| Qdrant Cloud | Vector database | Account + API key |
| OpenRouter | LLM API access | Account + API key |
| Ollama | Local embeddings | Self-hosted |

---

## System Requirements

### macOS

```bash
# Check macOS version
sw_vers -productVersion
# Required: 12.0+

# Check available resources
df -h /                                    # Disk space
system_profiler SPHardwareDataType | grep Memory  # RAM
system_profiler SPHardwareDataType | grep Processor # CPU
```

### Linux

```bash
# Check OS version
lsb_release -a
# Required: Ubuntu 22.04+ / RHEL 8+

# Check resources
free -h                                    # Memory
df -h /                                    # Disk
cat /proc/cpuinfo | grep "model name" | head -1  # CPU
```

---

## Installation

### Step 1: Install System Dependencies

#### macOS

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Ollama
brew install ollama

# Install Python 3.10+
brew install python@3.10

# Verify installations
python3 --version  # Should show 3.10+
ollama --version
```

#### Linux (Ubuntu/Debian)

```bash
# Update packages
sudo apt-get update

# Install Python and dependencies
sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Install Ollama (see https://ollama.ai for latest install)
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Pull Embedding Model

```bash
# Pull nomic-embed-text model (~500MB)
ollama pull nomic-embed-text

# Test Ollama
ollama run nomic-embed-text
# Type /bye to exit
```

### Step 3: Deploy Project

```bash
# Create project directory
mkdir -p ~/Projects
cd ~/Projects

# Clone or copy project
git clone <repository-url> RedCortex
# OR copy from source

# Change to project directory
cd RedCortex
```

### Step 4: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv secondbrain

# Activate environment
source secondbrain/bin/activate  # macOS/Linux

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
cp .env.example .env
nano .env
```

**Required variables:**

```bash
# Qdrant Cloud Configuration
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key

# OpenRouter Configuration
OPENROUTER_API_KEY=your-openrouter-api-key

# Ollama Configuration (optional)
OLLAMA_HOST=http://localhost:11434

# API Configuration (optional)
API_HOST=0.0.0.0
API_PORT=8000
```

### Security

```bash
# Set proper permissions on .env
chmod 600 .env

# Verify .env is in .gitignore
grep -q "^\.env$" .gitignore && echo "✓ .env is ignored" || echo "⚠️ Add .env to .gitignore"
```

### Initialize Database

```bash
# Initialize SQLite schema
python src/utils/init_db.py

# Setup Qdrant collection
python src/utils/setup_collection.py
```

---

## Deployment Procedures

### 24/7 Ingestion Setup

#### Option A: Batch Ingestion Script

```bash
# Create logs directory
mkdir -p logs

# Run batch ingestion
./scripts/batch_ingest.sh
```

#### Option B: Cron Schedule

```bash
# Edit crontab
crontab -e

# Add daily ingestion at 2 AM
0 2 * * * cd ~/Projects/RedCortex && ./scripts/batch_ingest.sh >> logs/cron.log 2>&1
```

#### Option C: LaunchDaemon (macOS)

```bash
# Create plist file
cat > ~/Library/LaunchAgents/com.redcortex.ingest.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.redcortex.ingest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/USER/Projects/RedCortex/scripts/batch_ingest.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/Users/USER/Projects/RedCortex/logs/launchd.out</string>
    <key>StandardErrorPath</key>
    <string>/Users/USER/Projects/RedCortex/logs/launchd.err</string>
</dict>
</plist>
EOF

# Load daemon
launchctl load ~/Library/LaunchAgents/com.redcortex.ingest.plist
```

### API Server Deployment

```bash
# Start FastAPI server
python src/api/main.py

# Server will be available at:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health
```

### Web UI Deployment

```bash
# Start Streamlit
streamlit run src/web_ui.py

# UI will be available at:
# http://localhost:8501
```

---

## Verification

### Health Check

```bash
# Run comprehensive health check
python src/utils/health_check.py
```

Expected output:
```
🔍 RedCortex Health Check
============================================================
Time: 2026-03-26 10:30:00

✅ Environment: All required variables set
✅ Database: Connected (5 books, 1234 chunks, 50 queries)
✅ Ollama: Connected (3 models, nomic-embed-text available)
✅ Qdrant: Connected (1234 vectors in books_hot)
✅ OpenRouter: API key valid
✅ Books: 5 indexed, 0 in progress
✅ Chunks: 1234 hot / 1234 total
✅ Disk Space: 45.2GB free (78% used)
✅ Cache: 23 cached responses

Result: 9/9 checks passed
🎉 System is healthy and ready for production!
```

### Quick Test Queries

```bash
# Quick validation (3 queries, no LLM)
python tests/test_queries.py --quick

# Full test suite without LLM
python tests/test_queries.py --no-llm
```

### Manual Verification

```bash
# Test CLI query
python src/query.py "How do I create a user in RHEL?"

# Test search
python src/search.py "systemctl commands"

# Test ingestion
python src/ingestion/ingest.py \
  "Redhat E-Books/test.pdf" \
  "Test Book" \
  red_hat
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Ollama connection error | Ollama not running | `ollama serve &` |
| Qdrant auth error | Invalid API key | Check `.env` file |
| No search results | Empty database | Run ingestion first |
| Import errors | Virtual env not activated | `source secondbrain/bin/activate` |
| Permission denied | Wrong file permissions | `chmod +x scripts/*.sh` |

### Log Locations

| Component | Log Location |
|-----------|--------------|
| Ingestion | `logs/ingest_*.log` |
| Ollama | `~/.ollama/logs/server.log` |
| API | `logs/api.log` |
| Cron | `logs/cron.log` |

### Restart Procedures

```bash
# Restart Ollama
pkill ollama
ollama serve &

# Restart ingestion
pkill -f ingest.py
./scripts/batch_ingest.sh

# Restart API server
pkill -f "src/api/main.py"
python src/api/main.py
```

### Getting Help

1. Check logs: `tail -f logs/ingest_*.log`
2. Run health check: `python src/utils/health_check.py`
3. Review documentation in `docs/`
4. Check GitHub issues (if applicable)

---

## Appendix

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QDRANT_URL` | Yes | - | Qdrant Cloud URL |
| `QDRANT_API_KEY` | Yes | - | Qdrant API key |
| `OPENROUTER_API_KEY` | Yes | - | OpenRouter API key |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama endpoint |
| `API_HOST` | No | `0.0.0.0` | API server host |
| `API_PORT` | No | `8000` | API server port |

### Directory Structure

```
RedCortex/
├── data/              # SQLite database & cache
├── docs/              # Documentation
├── logs/              # Log files
├── scripts/           # Deployment scripts
├── src/               # Source code
│   ├── api/           # FastAPI backend
│   ├── ingestion/     # PDF ingestion
│   ├── utils/         # Utilities
│   └── *.py           # Core modules
├── tests/             # Test suite
├── .env               # Environment variables
└── requirements.txt   # Python dependencies
```

### Useful Commands

```bash
# Database queries
sqlite3 data/library.db "SELECT title, status FROM books;"
sqlite3 data/library.db "SELECT COUNT(*) FROM chunks;"

# Sync data
rsync -avz data/library.db user@host:~/Projects/RedCortex/data/

# Monitor progress
tail -f logs/ingest_*.log
watch -n 5 'sqlite3 data/library.db "SELECT COUNT(*) FROM chunks;"'

# Clean up cache
rm -f data/cache/*.json
```

### Deployment Checklist

- [ ] Hardware meets minimum requirements
- [ ] macOS/Linux installed and updated
- [ ] Homebrew/apt packages installed
- [ ] Ollama installed and model pulled
- [ ] Python 3.10+ installed
- [ ] Project copied to target machine
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with API keys
- [ ] Database initialized
- [ ] Qdrant collection set up
- [ ] Health check passes
- [ ] Test ingestion successful
- [ ] Batch script configured
- [ ] Log rotation configured (optional)
- [ ] Monitoring set up (optional)
- [ ] Backup strategy defined (optional)

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 2.2.0 | 2026-03-26 | Standardized format, added troubleshooting section |
| 2.1.0 | 2026-03-20 | Added API server deployment |
| 2.0.0 | 2026-03-15 | Initial deployment guide |

---

**Document Owner:** RedCortex Team  
**Review Cycle:** Quarterly  
**Next Review:** 2026-06-26
