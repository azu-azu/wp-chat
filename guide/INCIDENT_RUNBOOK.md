# Incident Response Runbook

## 🚨 Emergency Procedures

### Quick Reference

| Incident Type | Severity | Primary Action | Secondary Action |
|---------------|----------|----------------|------------------|
| High Latency | High | Disable Reranking | Clear Cache |
| High Error Rate | Critical | Emergency Stop | Check Logs |
| Model Failure | High | Disable Reranking | Check Model Files |
| Index Corruption | Critical | Verify Index | Rebuild Index |
| Memory Exhaustion | High | Clear Cache | Restart Service |
| Cache Failure | Medium | Disable Cache | Clear Cache |
| Rate Limit Attack | High | Adjust Limits | Block IPs |
| Canary Failure | High | Emergency Stop | Disable Canary |

## 📋 Detailed Procedures

### 1. High Latency Incident

**Symptoms:**
- p95 latency > 800ms
- User complaints about slow responses
- High response times in monitoring

**Immediate Actions:**
1. **Disable Cross-Encoder Reranking** (30s)
   ```bash
   curl -X POST http://localhost:8080/admin/canary/disable
   ```

2. **Clear Cache** (60s)
   ```bash
   curl -X POST http://localhost:8080/admin/cache/clear
   ```

3. **Restart Service** (120s)
   ```bash
   pkill -f uvicorn && sleep 5 && uvicorn wp_chat.chat_api:app --host 0.0.0.0 --port 8080 --reload &
   ```

**Verification:**
- Check latency metrics: `curl http://localhost:8080/stats/metrics`
- Monitor dashboard: `http://localhost:8080/dashboard`

### 2. High Error Rate Incident

**Symptoms:**
- Success rate < 99.5%
- 5xx errors in logs
- User reports of failed requests

**Immediate Actions:**
1. **Emergency Stop All Features** (30s)
   ```bash
   curl -X POST http://localhost:8080/admin/canary/emergency-stop
   ```

2. **Check Error Logs** (60s)
   ```bash
   tail -n 100 logs/api_errors.log
   ```

3. **Restart Service** (120s)
   ```bash
   pkill -f uvicorn && sleep 5 && uvicorn wp_chat.chat_api:app --host 0.0.0.0 --port 8080 --reload &
   ```

**Verification:**
- Check error rate: `curl http://localhost:8080/stats/slo`
- Monitor success rate in dashboard

### 3. Model Failure Incident

**Symptoms:**
- Cross-Encoder model loading errors
- Fallback to hybrid search
- Model-related exceptions in logs

**Immediate Actions:**
1. **Disable Reranking** (30s)
   ```bash
   curl -X POST http://localhost:8080/admin/canary/disable
   ```

2. **Check Model Files** (30s)
   ```bash
   ls -la ~/.cache/huggingface/transformers/
   ```

3. **Reload Model** (180s)
   ```bash
   pkill -f uvicorn && sleep 5 && uvicorn wp_chat.chat_api:app --host 0.0.0.0 --port 8080 --reload &
   ```

**Verification:**
- Check model status: `curl http://localhost:8080/stats/device`
- Test reranking: `curl "http://localhost:8080/search?q=test&rerank=true"`

### 4. Index Corruption Incident

**Symptoms:**
- FAISS index loading errors
- Search returning empty results
- Index file corruption warnings

**Immediate Actions:**
1. **Verify Index Integrity** (60s)
   ```bash
   python -c "import faiss; idx = faiss.read_index('data/index/wp.faiss'); print(f'Index size: {idx.ntotal}')"
   ```

2. **Rebuild Index** (1800s)
   ```bash
   make rebuild-index
   ```

3. **Restore from Backup** (300s)
   ```bash
   cp data/index/wp.faiss.backup data/index/wp.faiss
   ```

**Verification:**
- Test search functionality
- Check index statistics

### 5. Memory Exhaustion Incident

**Symptoms:**
- High memory usage (>80%)
- Out of memory errors
- Slow response times

**Immediate Actions:**
1. **Check Memory Usage** (30s)
   ```bash
   free -h && ps aux --sort=-%mem | head -10
   ```

2. **Clear Cache** (60s)
   ```bash
   curl -X POST http://localhost:8080/admin/cache/clear
   ```

3. **Restart Service** (120s)
   ```bash
   pkill -f uvicorn && sleep 5 && uvicorn wp_chat.chat_api:app --host 0.0.0.0 --port 8080 --reload &
   ```

**Verification:**
- Monitor memory usage
- Check service health

### 6. Cache Failure Incident

**Symptoms:**
- Cache errors in logs
- Cache hit rate dropping
- Cache-related exceptions

**Immediate Actions:**
1. **Disable Caching** (30s)
   ```bash
   curl -X POST http://localhost:8080/admin/cache/disable
   ```

2. **Clear Cache** (60s)
   ```bash
   curl -X POST http://localhost:8080/admin/cache/clear
   ```

3. **Check Cache Directory** (30s)
   ```bash
   ls -la logs/cache/ && df -h logs/cache/
   ```

**Verification:**
- Check cache status: `curl http://localhost:8080/stats/cache`
- Monitor cache hit rate

### 7. Rate Limit Attack Incident

**Symptoms:**
- Unusual traffic spikes
- Rate limit violations
- DoS attack patterns

**Immediate Actions:**
1. **Check Rate Limit Status** (30s)
   ```bash
   curl http://localhost:8080/stats/rate-limit
   ```

2. **Adjust Rate Limits** (60s)
   ```bash
   curl -X POST http://localhost:8080/admin/rate-limit/adjust -d '{"max_requests": 10, "window_seconds": 3600}'
   ```

3. **Block Attacker IPs** (120s)
   ```bash
   iptables -A INPUT -s <ATTACKER_IP> -j DROP
   ```

**Verification:**
- Monitor traffic patterns
- Check rate limit effectiveness

### 8. Canary Failure Incident

**Symptoms:**
- Canary deployment issues
- A/B test failures
- Rollout problems

**Immediate Actions:**
1. **Emergency Stop Canary** (30s)
   ```bash
   curl -X POST http://localhost:8080/admin/canary/emergency-stop
   ```

2. **Disable Canary** (30s)
   ```bash
   curl -X POST http://localhost:8080/admin/canary/disable
   ```

3. **Check Canary Status** (30s)
   ```bash
   curl http://localhost:8080/admin/canary/status
   ```

**Verification:**
- Check canary status
- Monitor user experience

## 🛠️ CLI Commands

### Incident Management
```bash
# Check incident status
make incident-status

# Get active incidents
make incident-active

# Detect incident manually
make incident-detect

# Auto-detect incidents from SLO
make incident-auto-detect

# Show emergency procedures reference
make incident-emergency-ref
```

### Emergency Actions
```bash
# Get procedures for incident
python src/incident_cli.py procedures <incident_id>

# Execute emergency action
python src/incident_cli.py execute <incident_id> <action_id> --confirm

# Resolve incident
python src/incident_cli.py resolve <incident_id> --notes "Fixed by restart"
```

## 📞 Escalation Procedures

### Severity Levels
- **Critical**: Service completely down, data loss risk
- **High**: Major functionality affected, performance severely degraded
- **Medium**: Minor functionality affected, some users impacted
- **Low**: Cosmetic issues, minimal user impact

### Escalation Contacts
- **Level 1**: On-call Engineer (+1-XXX-XXX-XXXX)
- **Level 2**: Senior Engineer (+1-XXX-XXX-XXXX)
- **Level 3**: Engineering Manager (+1-XXX-XXX-XXXX)
- **Level 4**: CTO (+1-XXX-XXX-XXXX)

### Communication Channels
- **Slack**: #incident-response
- **Email**: incidents@company.com
- **PagerDuty**: Escalation policy configured

## 📊 Monitoring and Alerting

### Key Metrics to Monitor
- **Latency**: p95 < 800ms, p99 < 2000ms
- **Success Rate**: > 99.5%
- **Error Rate**: < 0.5%
- **Cache Hit Rate**: > 50%
- **Memory Usage**: < 80%
- **CPU Usage**: < 80%

### Alert Thresholds
- **Critical**: Success rate < 95%, Latency > 5000ms
- **High**: Success rate < 99%, Latency > 2000ms
- **Medium**: Success rate < 99.5%, Latency > 1000ms
- **Low**: Success rate < 99.8%, Latency > 800ms

### Dashboard URLs
- **Main Dashboard**: http://localhost:8080/dashboard
- **SLO Status**: http://localhost:8080/stats/slo
- **Incident Status**: http://localhost:8080/admin/incidents/status
- **Canary Status**: http://localhost:8080/admin/canary/status

## 🔄 Post-Incident Procedures

### 1. Incident Resolution
- [ ] Root cause identified
- [ ] Immediate fix applied
- [ ] Service restored
- [ ] Monitoring confirmed
- [ ] Incident marked as resolved

### 2. Post-Mortem Process
- [ ] Incident timeline documented
- [ ] Root cause analysis completed
- [ ] Action items identified
- [ ] Prevention measures planned
- [ ] Post-mortem report written

### 3. Follow-up Actions
- [ ] Monitoring improvements
- [ ] Process updates
- [ ] Training recommendations
- [ ] Tool enhancements
- [ ] Documentation updates

## 📚 Additional Resources

### Documentation
- [API Documentation](http://localhost:8080/docs)
- [Configuration Guide](config.yml)
- [Deployment Guide](README.md)

### Tools
- **Incident CLI**: `src/incident_cli.py`
- **Canary CLI**: `src/canary_cli.py`
- **Dashboard**: `dashboard.html`

### Logs Location
- **API Logs**: `logs/api_errors.log`
- **Incident Logs**: `logs/incidents.jsonl`
- **SLO Metrics**: `logs/slo_metrics.jsonl`
- **A/B Metrics**: `logs/ab_metrics.jsonl`
