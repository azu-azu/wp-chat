# Backup and Restore Guide

## 💾 Backup System Overview

The backup system provides comprehensive data protection for the Cross-Encoder Reranker system, including:

- **FAISS Index Files**: Search index and metadata
- **Cache Data**: Search result and embedding cache
- **Configuration**: System configuration files
- **Logs**: Application and system logs

## 🔧 Backup Types

### 1. Full Backup
- **Scope**: All system data (index, cache, config, logs)
- **Frequency**: Every 7 days (configurable)
- **Size**: Largest backup type
- **Use Case**: Complete system recovery

### 2. Incremental Backup
- **Scope**: Changes since last full backup
- **Frequency**: Every 24 hours (configurable)
- **Size**: Smaller than full backup
- **Use Case**: Regular data protection

### 3. Index Backup
- **Scope**: FAISS index files only
- **Frequency**: On-demand or scheduled
- **Size**: Medium size
- **Use Case**: Index corruption recovery

### 4. Cache Backup
- **Scope**: Cache files only
- **Frequency**: On-demand
- **Size**: Variable
- **Use Case**: Cache recovery

### 5. Config Backup
- **Scope**: Configuration files only
- **Frequency**: On-demand
- **Size**: Small
- **Use Case**: Configuration recovery

## 🚀 Quick Start

### Basic Commands
```bash
# Check backup status
make backup-status

# List available backups
make backup-list

# Create full backup
make backup-create

# Create index backup
make backup-create-index

# Clean up old backups
make backup-cleanup

# Schedule automatic backup
make backup-schedule

# Generate backup report
make backup-report
```

### CLI Commands
```bash
# Create backup
python src/backup_cli.py create --type full --description "Manual backup"

# List backups
python src/backup_cli.py list

# Restore backup
python src/backup_cli.py restore <backup_id>

# Verify backup
python src/backup_cli.py verify <backup_id>

# Delete backup
python src/backup_cli.py delete <backup_id>
```

## 📊 Backup Management

### Configuration
The backup system is configured in `config.yml`:

```yaml
api:
  backup:
    enabled: true
    schedule:
      full_backup_days: 7
      incremental_hours: 24
      retention_days: 30
      max_backups: 10
    paths:
      index: "data/index/"
      cache: "logs/cache/"
      config: "config.yml"
      logs: "logs/"
    compression: true
    verification: true
    auto_cleanup: true
```

### Backup Storage
- **Location**: `backups/` directory
- **Format**: Compressed tar.gz archives
- **Naming**: `backup_<timestamp>.tar.gz`
- **Metadata**: Stored in `logs/backup_history.jsonl`

## 🔄 Restore Procedures

### 1. Full System Restore
```bash
# List available backups
python src/backup_cli.py list

# Restore from full backup
python src/backup_cli.py restore <backup_id>

# Verify restore
python src/backup_cli.py verify <backup_id>
```

### 2. Index-Only Restore
```bash
# Create index backup first
python src/backup_cli.py create --type index

# Restore index
python src/backup_cli.py restore <backup_id> --target data/index/
```

### 3. Emergency Restore
```bash
# Find latest verified backup
python src/backup_cli.py list | grep verified

# Restore without verification (faster)
python src/backup_cli.py restore <backup_id> --no-verify
```

## 🛡️ Backup Verification

### Automatic Verification
- **Checksum Validation**: MD5 checksums for integrity
- **Archive Testing**: Tar.gz integrity check
- **File Count**: Verify all files are included
- **Size Validation**: Check backup size

### Manual Verification
```bash
# Verify specific backup
python src/backup_cli.py verify <backup_id>

# Check backup statistics
python src/backup_cli.py status
```

## 📈 Monitoring and Alerts

### Key Metrics
- **Success Rate**: Percentage of successful backups
- **Backup Size**: Total storage used
- **Frequency**: Number of backups per period
- **Age**: Time since last backup

### Alert Conditions
- **No Recent Backups**: No backup in 48+ hours
- **Failed Backups**: Backup failure rate > 10%
- **Large Size**: Backup size > 1GB
- **Low Success Rate**: Success rate < 90%

### Dashboard Integration
- **Backup Status**: Available in main dashboard
- **Statistics**: Backup metrics and trends
- **Alerts**: Backup-related incidents

## 🔧 Troubleshooting

### Common Issues

#### 1. Backup Creation Fails
```bash
# Check disk space
df -h

# Check permissions
ls -la backups/

# Check configuration
python src/backup_cli.py status
```

#### 2. Restore Fails
```bash
# Verify backup integrity
python src/backup_cli.py verify <backup_id>

# Check target directory permissions
ls -la data/index/

# Try restore without verification
python src/backup_cli.py restore <backup_id> --no-verify
```

#### 3. Large Backup Size
```bash
# Clean up old backups
python src/backup_cli.py cleanup

# Check what's being backed up
python src/backup_cli.py list --type full
```

### Recovery Procedures

#### 1. Index Corruption
```bash
# Stop service
pkill -f uvicorn

# Restore index from backup
python src/backup_cli.py restore <latest_index_backup>

# Restart service
uvicorn src.chat_api:app --host 0.0.0.0 --port 8080 --reload &
```

#### 2. Cache Issues
```bash
# Clear current cache
curl -X POST http://localhost:8080/admin/cache/clear

# Restore cache from backup
python src/backup_cli.py restore <cache_backup>
```

#### 3. Configuration Problems
```bash
# Backup current config
cp config.yml config.yml.backup

# Restore from backup
python src/backup_cli.py restore <config_backup> --target .
```

## 📅 Backup Schedule

### Recommended Schedule
- **Full Backup**: Weekly (Sunday 2 AM)
- **Incremental Backup**: Daily (2 AM)
- **Index Backup**: Before major deployments
- **Config Backup**: Before configuration changes

### Automated Scheduling
```bash
# Add to crontab
crontab -e

# Add these lines:
0 2 * * 0 cd /path/to/wp-chat && make backup-create
0 2 * * 1-6 cd /path/to/wp-chat && make backup-schedule
```

## 🔒 Security Considerations

### Backup Security
- **Access Control**: Restrict backup directory access
- **Encryption**: Consider encrypting sensitive backups
- **Offsite Storage**: Store backups in separate location
- **Retention Policy**: Follow data retention requirements

### Restore Security
- **Verification**: Always verify backup integrity
- **Testing**: Test restore procedures regularly
- **Documentation**: Document restore procedures
- **Access Logs**: Log all restore operations

## 📚 API Reference

### Backup Endpoints
- `GET /admin/backup/status` - Get backup statistics
- `GET /admin/backup/list` - List available backups
- `POST /admin/backup/create` - Create new backup
- `POST /admin/backup/restore` - Restore from backup
- `DELETE /admin/backup/{id}` - Delete backup
- `POST /admin/backup/cleanup` - Clean up old backups
- `POST /admin/backup/schedule` - Schedule automatic backup

### Example API Usage
```bash
# Create backup via API
curl -X POST http://localhost:8080/admin/backup/create \
  -H "Content-Type: application/json" \
  -d '{"backup_type": "full", "description": "API backup"}'

# Get backup status
curl http://localhost:8080/admin/backup/status

# List backups
curl http://localhost:8080/admin/backup/list
```

## 🎯 Best Practices

### Backup Strategy
1. **Regular Backups**: Maintain consistent backup schedule
2. **Multiple Types**: Use different backup types for different needs
3. **Verification**: Always verify backup integrity
4. **Testing**: Regularly test restore procedures
5. **Documentation**: Keep backup procedures documented

### Restore Strategy
1. **Quick Recovery**: Have restore procedures ready
2. **Testing**: Test restore procedures in non-production
3. **Monitoring**: Monitor restore operations
4. **Rollback**: Have rollback procedures ready
5. **Communication**: Notify stakeholders of restore operations

### Maintenance
1. **Cleanup**: Regularly clean up old backups
2. **Monitoring**: Monitor backup system health
3. **Updates**: Keep backup system updated
4. **Training**: Train team on backup procedures
5. **Review**: Regularly review backup strategy

## 🆘 Emergency Procedures

### Complete System Failure
1. **Assess Damage**: Determine what needs to be restored
2. **Stop Services**: Stop all running services
3. **Restore Data**: Restore from latest verified backup
4. **Verify Restore**: Test system functionality
5. **Restart Services**: Start services and monitor
6. **Document**: Document the incident and resolution

### Partial Data Loss
1. **Identify Loss**: Determine what data is missing
2. **Select Backup**: Choose appropriate backup
3. **Partial Restore**: Restore only affected data
4. **Verify**: Test affected functionality
5. **Monitor**: Monitor system for issues

### Backup System Failure
1. **Manual Backup**: Create manual backup if possible
2. **Fix System**: Repair backup system
3. **Resume Schedule**: Resume normal backup schedule
4. **Review**: Review backup system configuration
5. **Improve**: Implement improvements to prevent recurrence
