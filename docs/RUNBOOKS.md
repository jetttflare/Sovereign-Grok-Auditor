# GrokApp Operational Runbooks
# ============================
# Production runbooks for incident response and operational procedures

## Table of Contents
1. [Service Down: GrokAPI](#runbook-grok-api-down)
2. [Service Down: OrbitBridge](#runbook-orbit-bridge-down)
3. [Service Down: JobMaster](#runbook-job-master-down)
4. [Security: API Key Exposure](#runbook-api-key-exposure)
5. [Security: Failed Login Attempts](#runbook-failed-logins)
6. [Backup: Restore Procedure](#runbook-backup-restore)
7. [Performance: High Latency](#runbook-high-latency)
8. [Disaster Recovery: Full System](#runbook-disaster-recovery)

---

## Runbook: GrokAPI Down {#runbook-grok-api-down}

### Alert
`GrokAPIDown` - GrokAPI has been unreachable for more than 1 minute

### Severity
🔴 **CRITICAL**

### Impact
- All AI inference requests will fail
- WebSocket clients will lose connection
- Dependent services (JobMaster, OrbitBridge) may degrade

### Diagnosis Steps

```bash
# 1. Check if process is running
ps aux | grep grokapi

# 2. Check port availability
lsof -i :8080

# 3. Check recent logs
tail -100 /var/log/grokapp/grokapi.log

# 4. Check system resources
free -m && df -h && top -bn1 | head -20

# 5. Check network connectivity
curl -v http://localhost:8080/health
```

### Resolution Steps

```bash
# Step 1: Attempt graceful restart
systemctl restart grokapi

# Step 2: Wait 30 seconds
sleep 30

# Step 3: Verify service is up
curl http://localhost:8080/health

# If still failing:
# Step 4: Check for port conflicts
netstat -tulpn | grep 8080

# Step 5: Review error logs
journalctl -u grokapi -n 200 --no-pager

# Step 6: If OOM, increase memory limits
# Edit /etc/systemd/system/grokapi.service
# Add: MemoryMax=4G

# Step 7: Force restart
systemctl stop grokapi
sleep 5
systemctl start grokapi
```

### Escalation
- **After 5 minutes:** Page on-call engineer
- **After 15 minutes:** Page engineering manager
- **After 30 minutes:** Initiate DR procedure

---

## Runbook: OrbitBridge Down {#runbook-orbit-bridge-down}

### Alert
`OrbitBridgeDown` - OrbitBridge WebSocket server unreachable

### Severity
🔴 **CRITICAL**

### Impact
- Real-time dashboard updates will stop
- Mobile app will show stale data
- AI agent coordination will be impaired

### Diagnosis Steps

```bash
# 1. Check Node.js process
ps aux | grep node | grep orbitbridge

# 2. Check WebSocket port
lsof -i :3001

# 3. Test WebSocket connection
wscat -c ws://localhost:3001/status

# 4. Check Node.js logs
pm2 logs orbitbridge --lines 100
```

### Resolution Steps

```bash
# Step 1: Restart via PM2
pm2 restart orbitbridge

# Step 2: If PM2 fails, manual restart
pm2 stop orbitbridge
sleep 3
pm2 start orbitbridge

# Step 3: If still failing, check npm dependencies
cd /opt/grokapp/orbitbridge
npm install
pm2 restart orbitbridge

# Step 4: Nuclear option - full reset
pm2 delete orbitbridge
pm2 start server.js --name orbitbridge
```

### Escalation
- **After 5 minutes:** Page on-call engineer
- **After 15 minutes:** Failover to backup WebSocket server

---

## Runbook: JobMaster Down {#runbook-job-master-down}

### Alert
`JobMasterDown` - JobMaster job scheduling service unreachable

### Severity
🟡 **HIGH**

### Impact
- Scheduled jobs will not execute
- Job queue will back up
- Background processing will halt

### Diagnosis Steps

```bash
# 1. Check process
ps aux | grep jobmaster

# 2. Check job queue depth
redis-cli llen jobmaster:queue

# 3. Check database connection
python3 -c "from jobmaster import db; print(db.ping())"
```

### Resolution Steps

```bash
# Step 1: Restart service
systemctl restart jobmaster

# Step 2: Clear stuck jobs (if needed)
redis-cli del jobmaster:stuck_jobs

# Step 3: Reprocess failed jobs
python3 -m jobmaster.cli reprocess-failed --limit 100
```

---

## Runbook: API Key Exposure {#runbook-api-key-exposure}

### Alert
`APIKeyExposureDetected` - Potential API key exposure detected

### Severity
🔴 **CRITICAL - SECURITY**

### Impact
- Compromised API keys may be used maliciously
- Potential unauthorized access to external services
- Compliance violation

### Immediate Actions (< 5 minutes)

```bash
# STEP 1: ROTATE AFFECTED KEY IMMEDIATELY
# Do this BEFORE any investigation

# For Gemini API:
# 1. Go to console.cloud.google.com
# 2. Navigate to APIs & Services > Credentials
# 3. Delete compromised key
# 4. Create new key

# For Grok API:
# 1. Go to x.ai/api
# 2. Revoke current key
# 3. Generate new key

# STEP 2: Update application
export NEW_API_KEY="your-new-key"
echo "NEW_API_KEY=${NEW_API_KEY}" >> /opt/grokapp/.env

# STEP 3: Restart services
systemctl restart grokapi jobmaster

# STEP 4: Clear from git history (if applicable)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/exposed/file' \
  --prune-empty --tag-name-filter cat -- --all
git push origin --force --all
```

### Investigation Steps

```bash
# Determine scope of exposure
git log --all --full-history -- "**/.*env*"
grep -r "sk-" . --include="*.py" --include="*.js"

# Check audit logs for unauthorized usage
cat /var/log/grokapp/audit/*.log | grep -i "unauthorized\|failed\|denied"

# Review access logs from API provider dashboard
```

### Post-Incident
1. Document timeline in incident report
2. Update security scanning rules
3. Review and strengthen .gitignore
4. Conduct team security review

---

## Runbook: Failed Login Attempts {#runbook-failed-logins}

### Alert
`HighFailedLoginAttempts` - More than 10 failed login attempts in 15 minutes

### Severity
🟡 **WARNING - SECURITY**

### Diagnosis

```bash
# Check source IPs
cat /var/log/grokapp/audit/*.log | \
  jq 'select(.action == "LOGIN" and .result == "FAILED")' | \
  jq -r '.metadata.source_ip' | sort | uniq -c | sort -rn

# Check targeted accounts
cat /var/log/grokapp/audit/*.log | \
  jq 'select(.action == "LOGIN" and .result == "FAILED")' | \
  jq -r '.user_id' | sort | uniq -c | sort -rn
```

### Resolution

```bash
# Block suspicious IPs
for ip in $(suspicious_ips); do
  iptables -A INPUT -s $ip -j DROP
done

# If targeting specific account, temporarily lock it
python3 -c "from grokapp.auth import lock_account; lock_account('username')"

# Enable enhanced logging
export GROKAPP_AUTH_DEBUG=1
systemctl restart grokapi
```

---

## Runbook: Backup Restore {#runbook-backup-restore}

### Alert
`BackupFailed` or manual restore request

### Severity
🟡 **HIGH**

### Pre-Restore Checklist
- [ ] Identify target backup to restore
- [ ] Verify backup integrity
- [ ] Notify all stakeholders
- [ ] Schedule maintenance window

### Restore Procedure

```bash
# Step 1: List available backups
python3 -m backup.disaster_recovery list

# Step 2: Verify backup integrity
python3 -m backup.disaster_recovery verify --backup-id grokapp_full_YYYYMMDD_HHMMSS

# Step 3: Create pre-restore backup
python3 -m backup.disaster_recovery create --type pre_restore

# Step 4: Stop all services
systemctl stop grokapi orbitbridge jobmaster

# Step 5: Perform restore
python3 -m backup.disaster_recovery restore --backup-id grokapp_full_YYYYMMDD_HHMMSS

# Step 6: Restart services
systemctl start grokapi orbitbridge jobmaster

# Step 7: Verify system health
python3 -m monitoring.health_checks
```

---

## Runbook: High Latency {#runbook-high-latency}

### Alert
`HighAPILatency` - 99th percentile latency above 2 seconds

### Severity
🟡 **WARNING**

### Diagnosis

```bash
# Check current latency metrics
curl -s http://localhost:9090/api/v1/query?query=http_request_duration_seconds | jq

# Check slow queries
grep -i "slow" /var/log/grokapp/grokapi.log | tail -20

# Check external API response times
curl -w "@curl-format.txt" -o /dev/null -s https://api.x.ai/health

# Check system load
uptime && vmstat 1 5
```

### Resolution

```bash
# Step 1: If CPU-bound, scale horizontally
systemctl start grokapi@2  # Start second instance

# Step 2: If external API slow, enable caching
export GROKAPP_CACHE_ENABLED=true
systemctl restart grokapi

# Step 3: If DB slow, check connections
python3 -c "from grokapp import db; print(db.pool_status())"

# Step 4: Clear any stale connections
python3 -c "from grokapp import db; db.clear_stale_connections()"
```

---

## Runbook: Disaster Recovery - Full System {#runbook-disaster-recovery}

### Alert
Multiple critical services down OR catastrophic failure

### Severity
🔴 **CRITICAL**

### Prerequisites
- Access to backup storage
- DR site credentials
- Team communication channel established

### Full DR Procedure

```bash
# PHASE 1: ASSESS (5 minutes)
# ===========================
# Determine scope of failure
python3 -m monitoring.health_checks

# Check all service statuses
systemctl status grokapi orbitbridge jobmaster prometheus

# PHASE 2: COMMUNICATE (2 minutes)
# ================================
# Post in #incidents channel
# Page all on-call engineers

# PHASE 3: RECOVER (15-30 minutes)
# ================================

# Option A: In-place recovery
python3 -m backup.service_recovery --run-playbook

# Option B: Restore from backup
python3 -m backup.disaster_recovery restore --latest

# Option C: Failover to DR site
./scripts/failover-to-dr.sh

# PHASE 4: VALIDATE (10 minutes)
# ==============================
# Run full health check suite
python3 -m monitoring.health_checks --full

# Verify all endpoints
curl http://localhost:8080/health
curl http://localhost:3001/status
curl http://localhost:5010/health

# PHASE 5: POST-INCIDENT (1-2 hours)
# ==================================
# Document timeline
# Root cause analysis
# Update runbooks if needed
# Schedule post-mortem meeting
```

### RTO/RPO Targets
- **RTO (Recovery Time Objective):** 30 minutes
- **RPO (Recovery Point Objective):** 24 hours (daily backups)

---

## Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| On-Call Engineer | Rotating | PagerDuty |
| Engineering Manager | TBD | Slack: @manager |
| Security Team | TBD | security@company.com |
| Cloud Provider | AWS/Azure | Support Portal |

---

*Last Updated: 2026-01-02*
*Version: 1.0.0*
