# RedCortex Operations Runbook

| Document | Details |
|----------|---------|
| **Project** | RedCortex - RAG System for Technical Documentation |
| **Version** | 1.0.0 |
| **Last Updated** | 2026-03-26 |
| **Status** | Production |
| **Audience** | Operations Team, DevOps Engineers |

---

## Table of Contents

1. [Overview](#overview)
2. [Daily Operations](#daily-operations)
3. [Incident Response](#incident-response)
4. [Maintenance Procedures](#maintenance-procedures)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Backup & Recovery](#backup--recovery)
7. [Scaling Guidelines](#scaling-guidelines)
8. [Security Operations](#security-operations)
9. [Appendix](#appendix)

---

## Overview

This runbook provides operational procedures for maintaining the RedCortex RAG system in production. It covers routine operations, incident response, maintenance tasks, and troubleshooting steps.

### System Components

| Component | Purpose | Criticality |
|-----------|---------|-------------|
| Ollama | Local embedding generation | High |
| Qdrant Cloud | Vector database | Critical |
| SQLite | Metadata & query logging | High |
| OpenRouter | LLM API | Critical |
| FastAPI | REST API backend | Medium |
| Streamlit | Web UI | Low |

### Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| Primary On-Call | TBD | - |
| Engineering Lead | TBD | +1 hour |
| Product Owner | TBD | +4 hours |

---

## Daily Operations

### Morning Check (09:00)

```bash
# 1. Health Check
python src/utils/health_check.py

# 2. Check overnight ingestion
sqlite3 data/library.db "SELECT title, status FROM books WHERE status != 'indexed';"

# 3. Review recent errors
grep -i "error\|failed\|timeout" logs/ingest_*.log | tail -20

# 4. Check disk space
df -h /
```

### Evening Check (18:00)

```bash
# 1. Query statistics
python src/utils/query_logger.py stats 1

# 2. Ingestion progress
sqlite3 data/library.db "SELECT COUNT(*) as total_books FROM books;"
sqlite3 data/library.db "SELECT COUNT(*) as total_chunks FROM chunks;"

# 3. Check cache hit rate
python src/utils/query_logger.py stats 7 | grep "Cache Hit Rate"

# 4. Verify Ollama is running
pgrep -f ollama || echo "⚠️ Ollama not running"
```

### Query Monitoring

```bash
# Recent queries
python src/utils/query_logger.py recent 10

# High error rate check
sqlite3 data/library.db "SELECT COUNT(*) FROM queries WHERE timestamp >= datetime('now', '-1 hour') AND error IS NOT NULL;"
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 | Service down | 15 min | All queries failing, Ollama down |
| P2 | Degraded service | 1 hour | Slow queries, partial ingestion failure |
| P3 | Non-critical issue | 4 hours | Cache misses, UI glitches |
| P4 | Enhancement | 1-2 days | Feature requests, optimizations |

### Incident Response Workflow

1. **Detect** → Monitoring alert or user report
2. **Assess** → Determine severity and impact
3. **Respond** → Follow specific runbook procedure
4. **Resolve** → Fix and verify
5. **Post-Incident** → Document and review

### Common Incidents

#### P1: Ollama Service Down

**Symptoms:**
- All embeddings fail
- Health check: "Ollama not reachable"

**Response:**
```bash
# 1. Check if Ollama is running
pgrep -f ollama

# 2. If not running, start it
ollama serve &

# 3. Verify model is available
ollama list | grep nomic-embed-text

# 4. If model missing, pull it
ollama pull nomic-embed-text

# 5. Test embedding
curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
```

#### P1: Qdrant Connection Failure

**Symptoms:**
- Search returning no results
- Health check: "Qdrant error"

**Response:**
```bash
# 1. Test connectivity
curl -H "api-key: $QDRANT_API_KEY" \
  https://your-cluster.cloud.qdrant.io/collections

# 2. Check Qdrant Cloud status
# Visit: https://status.qdrant.io

# 3. If credentials issue, verify .env
cat .env | grep QDRANT

# 4. Restart API server to refresh connection
pkill -f "src/api/main.py"
python src/api/main.py
```

#### P2: Slow Query Performance

**Symptoms:**
- Average latency > 5 seconds
- User complaints about slow responses

**Response:**
```bash
# 1. Check current metrics
python src/utils/query_logger.py stats 1

# 2. Check cache hit rate
# If < 50%, cache may need warming

# 3. Check Ollama performance
tail -f ~/.ollama/logs/server.log

# 4. Check system resources
htop  # or top

# 5. Mitigations:
# - Increase OLLAMA_KEEP_ALIVE
# - Clear expired cache entries
# - Restart Ollama to free memory
```

#### P2: Ingestion Stuck

**Symptoms:**
- Ingestion process not progressing
- Same page being processed repeatedly

**Response:**
```bash
# 1. Check current ingestion
ps aux | grep ingest.py

# 2. Check logs for errors
tail -100 logs/ingest_*.log

# 3. Kill stuck process
pkill -f ingest.py

# 4. Check database status
sqlite3 data/library.db "SELECT title, status, total_pages FROM books WHERE status = 'indexing';"

# 5. Resume ingestion (it will auto-resume from last page)
./scripts/batch_ingest.sh
```

---

## Maintenance Procedures

### Weekly Maintenance (Every Monday)

```bash
# 1. Rotate logs
cd logs
mkdir -p archive/$(date +%Y%m)
mv ingest_$(date -v-7d +%Y%m)*.log archive/$(date +%Y%m)/ 2>/dev/null

# 2. Clean expired cache
find data/cache -name "*.json" -mtime +7 -delete

# 3. Database optimization
sqlite3 data/library.db "VACUUM;"
sqlite3 data/library.db "ANALYZE;"

# 4. Check for updates
pip list --outdated | grep -E "qdrant|langchain|fastapi"

# 5. Backup database
cp data/library.db backups/library_$(date +%Y%m%d).db
```

### Monthly Maintenance (First Sunday)

```bash
# 1. Full system health check
python src/utils/health_check.py

# 2. Review and archive old query logs
sqlite3 data/library.db "DELETE FROM queries WHERE timestamp < datetime('now', '-90 days');"
sqlite3 data/library.db "VACUUM;"

# 3. Update dependencies (test first)
pip install --upgrade -r requirements.txt --dry-run

# 4. Security check
chmod 600 .env
find . -name "*.log" -perm /o+r -exec chmod o-r {} \;

# 5. Capacity planning
sqlite3 data/library.db "SELECT COUNT(*) FROM chunks;"  # Vector count
df -h /  # Disk usage
```

### Quarterly Maintenance

1. **Dependency Updates**
   - Review changelog for all dependencies
   - Test updates in staging environment
   - Deploy updates during maintenance window

2. **Security Review**
   - Rotate API keys
   - Review access logs
   - Update firewall rules if needed

3. **Performance Review**
   - Analyze query patterns
   - Optimize slow queries
   - Review cache effectiveness

4. **Documentation Update**
   - Update runbook with new procedures
   - Document any architectural changes

---

## Monitoring & Alerting

### Key Metrics

| Metric | Warning | Critical | Query/Command |
|--------|---------|----------|---------------|
| Query latency | > 3000ms | > 10000ms | `SELECT AVG(latency_ms) FROM queries WHERE timestamp >= datetime('now', '-1 hour')` |
| Error rate | > 5% | > 20% | Check error count in last hour |
| Cache hit rate | < 30% | < 10% | `python src/utils/query_logger.py stats 1` |
| Disk usage | > 80% | > 95% | `df -h /` |
| Memory usage | > 80% | > 95% | `vm_stat` (macOS) / `free` (Linux) |
| Ollama response | > 2000ms | > 5000ms | Check Ollama logs |

### Health Check Automation

```bash
# Create automated health check script
cat > scripts/health_monitor.sh << 'EOF'
#!/bin/bash
source secondbrain/bin/activate
python src/utils/health_check.py > logs/health_$(date +%Y%m%d_%H%M%S).log
if [ $? -ne 0 ]; then
    echo "ALERT: Health check failed at $(date)" | mail -s "RedCortex Alert" ops@example.com
fi
EOF
chmod +x scripts/health_monitor.sh

# Add to cron (every 15 minutes)
*/15 * * * * cd ~/Projects/RedCortex && ./scripts/health_monitor.sh
```

### Log Aggregation

```bash
# Centralized logging with timestamp
tail -f logs/ingest_*.log | while read line; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line" >> logs/all_ingest.log
done
```

---

## Backup & Recovery

### Backup Strategy

| Data | Frequency | Method | Retention |
|------|-----------|--------|-----------|
| SQLite DB | Daily | Automated script | 30 days |
| .env file | Weekly | Manual copy | Forever |
| Query cache | Weekly | Archive old entries | 7 days |
| Logs | Monthly | Compression | 90 days |

### Automated Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="$HOME/Backups/RedCortex/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup database
cp data/library.db "$BACKUP_DIR/"

# Backup .env
cp .env "$BACKUP_DIR/"

# Backup logs (last 7 days)
tar -czf "$BACKUP_DIR/logs_$(date +%Y%m%d).tar.gz" logs/*.log --newer-mtime '7 days ago' 2>/dev/null

# Sync to remote (optional)
# rsync -avz "$BACKUP_DIR/" backup-server:/backups/redcortex/

echo "Backup complete: $BACKUP_DIR"
```

### Recovery Procedures

#### Database Recovery

```bash
# 1. Stop all ingestion
pkill -f ingest.py

# 2. Backup current (corrupted) database
cp data/library.db data/library_$(date +%Y%m%d)_corrupted.db

# 3. Restore from backup
cp backups/library_20260320.db data/library.db

# 4. Verify integrity
sqlite3 data/library.db "PRAGMA integrity_check;"
sqlite3 data/library.db "SELECT COUNT(*) FROM books;"

# 5. Resume ingestion
./scripts/batch_ingest.sh
```

#### Complete System Recovery

```bash
# 1. Reinstall from scratch
# Follow DEPLOYMENT.md

# 2. Restore database
cp backups/library_20260320.db data/library.db

# 3. Restore .env
cp backups/env_20260320 .env

# 4. Reinstall dependencies
pip install -r requirements.txt

# 5. Verify
python src/utils/health_check.py
```

---

## Scaling Guidelines

### Vertical Scaling

| Bottleneck | Symptom | Solution |
|------------|---------|----------|
| Ollama memory | Slow embeddings | Increase RAM, use GPU |
| Disk I/O | Slow queries | Use SSD |
| CPU | High load | Upgrade CPU cores |

### Horizontal Scaling (Future)

For high query volumes:

1. **API Server Scaling**
   - Deploy behind load balancer
   - Multiple API instances
   - Shared SQLite (move to PostgreSQL)

2. **Ollama Scaling**
   - Dedicated Ollama server
   - Multiple Ollama instances
   - Use GPU acceleration

3. **Caching Strategy**
   - Redis for distributed caching
   - CDN for static assets

---

## Security Operations

### Access Control

```bash
# Set proper file permissions
chmod 700 ~/Projects/RedCortex
chmod 600 .env
chmod 755 scripts/*.sh

# Check for unauthorized access
last | head -20
sudo grep "Failed password" /var/log/auth.log
```

### Secret Rotation

**Monthly Procedure:**

1. Generate new API keys
2. Update `.env` file
3. Restart services
4. Revoke old keys
5. Verify functionality

### Security Monitoring

```bash
# Check for suspicious queries
sqlite3 data/library.db "SELECT query, COUNT(*) as count FROM queries WHERE timestamp >= datetime('now', '-1 day') GROUP BY query ORDER BY count DESC LIMIT 10;"

# Check logins
sudo grep "sshd" /var/log/auth.log | tail -20
```

---

## Appendix

### Useful Queries

```sql
-- Top queries today
SELECT question, COUNT(*) as count 
FROM queries 
WHERE timestamp >= datetime('now', '-1 day')
GROUP BY query_hash 
ORDER BY count DESC 
LIMIT 10;

-- Error summary
SELECT error, COUNT(*) as count 
FROM queries 
WHERE timestamp >= datetime('now', '-7 days') 
AND error IS NOT NULL 
GROUP BY error 
ORDER BY count DESC;

-- Ingestion progress
SELECT title, status, 
       (SELECT COUNT(*) FROM chunks WHERE book_id = books.id) as chunks,
       total_pages
FROM books 
ORDER BY id;
```

### Performance Tuning

```bash
# Ollama optimization
export OLLAMA_KEEP_ALIVE=60m
export OLLAMA_NUM_PARALLEL=4

# Python optimization
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# SQLite optimization
sqlite3 data/library.db "PRAGMA journal_mode=WAL;"
sqlite3 data/library.db "PRAGMA synchronous=NORMAL;"
```

### Emergency Contacts Template

```
RedCortex Operations
====================

Primary On-Call: [Name] - [Phone] - [Email]
Escalation: [Name] - [Phone] - [Email]

Infrastructure:
- Qdrant Cloud: support@qdrant.tech
- OpenRouter: support@openrouter.ai
- Ollama: github.com/ollama/ollama/issues

Internal Resources:
- Repository: [GitHub URL]
- Documentation: docs/
- Monitoring Dashboard: [URL]
```

### Runbook Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-03-26 | - | Initial runbook creation |

---

**Document Owner:** Operations Team  
**Review Cycle:** Monthly  
**Next Review:** 2026-04-26
