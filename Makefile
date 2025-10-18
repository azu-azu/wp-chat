eval:
	. .venv/bin/activate && python src/eval_retrieval.py --mode hybrid --k 5

eval-rerank:
	. .venv/bin/activate && python src/eval_retrieval.py --mode hybrid --k 5 --rerank ce

rerank:
	. .venv/bin/activate && python src/search_hybrid.py --query "お問い合わせ" --topk 10 --rerank ce

bm25:
	. .venv/bin/activate && python src/build_bm25.py

hybrid:
	. .venv/bin/activate && python src/search_hybrid.py --query "お問い合わせ" --topk 5

config-test:
	. .venv/bin/activate && python -c "from src.config import get_config_value; print('Config test:', get_config_value('hybrid.alpha'))"

ab-stats:
	. .venv/bin/activate && python -c "from src.ab_logging import get_ab_stats; import json; print(json.dumps(get_ab_stats(), indent=2, ensure_ascii=False))"

device-info:
	. .venv/bin/activate && python -c "from src.model_manager import get_device_status; import json; print(json.dumps(get_device_status(), indent=2, ensure_ascii=False))"

scoring-experiment:
	. .venv/bin/activate && python src/search_hybrid.py --query "データベース設計" --topk 3 --rerank ce --scoring-strategy ce_heavy

highlight-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.highlight import get_highlight_info; info = get_highlight_info('データベース設計について教えて'); print('Morphology available:', info['morphology_available']); print('Extracted keywords:', info['extracted_keywords']); print('Morphology keywords:', info['morphology_keywords']); print('Basic keywords:', info['basic_keywords'])"

highlight-compare:
	. .venv/bin/activate && python src/search_hybrid.py --query "データベース設計" --topk 2 --rerank ce --scoring-strategy balanced

scoring-strategies:
	. .venv/bin/activate && python -c "from src.composite_scoring import get_scoring_strategies; print('Available strategies:', get_scoring_strategies())"

cache-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.cache import cache_manager, cache_search_results, get_cached_search_results; test_data = [{'title': 'Test', 'snippet': 'Test content'}]; cache_search_results('test query', test_data, 60); cached = get_cached_search_results('test query'); print('Cache test:', 'SUCCESS' if cached else 'FAILED'); print('Cache stats:', cache_manager.get_stats())"

dashboard-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.dashboard import get_dashboard_data, get_ab_summary, get_cache_summary; print('=== ダッシュボード機能テスト ==='); dashboard_data = get_dashboard_data(days=1, hours=6); print('Dashboard data keys:', list(dashboard_data.keys())); ab_summary = get_ab_summary(days=1); print('A/B summary:', ab_summary); cache_summary = get_cache_summary(hours=6); print('Cache summary:', cache_summary)"

slo-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.slo_monitoring import slo_monitor, record_api_metric; import time; record_api_metric('search', 500, 200, rerank_enabled=True, cache_hit=False); record_api_metric('search', 1200, 200, rerank_enabled=True, cache_hit=False); record_api_metric('search', 300, 500, rerank_enabled=False, cache_hit=True); print('SLO test metrics recorded'); print('SLO status:', slo_monitor.get_slo_status())"

rate-limit-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.rate_limit import rate_limiter; allowed, info = rate_limiter.is_allowed('test_client', 5, 60); print('Rate limit test:', 'ALLOWED' if allowed else 'BLOCKED'); print('Rate info:', info); print('Global stats:', rate_limiter.get_global_stats())"

canary-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.canary_manager import canary_manager; print('=== カナリア機能テスト ==='); print('初期状態:', canary_manager.get_config()); canary_manager.enable_canary(0.1, 'test'); print('10%有効化後:', canary_manager.get_config()); print('ユーザー1 rerank有効:', canary_manager.is_rerank_enabled_for_user('user1')); print('ユーザー2 rerank有効:', canary_manager.is_rerank_enabled_for_user('user2')); canary_manager.update_rollout_percentage(0.5, 'test'); print('50%更新後:', canary_manager.get_config()); canary_manager.emergency_stop('test'); print('緊急停止後:', canary_manager.get_config()); canary_manager.clear_emergency_stop('test'); print('緊急停止解除後:', canary_manager.get_config())"

# Canary CLI commands
canary-status:
	. .venv/bin/activate && python src/canary_cli.py status

canary-enable:
	. .venv/bin/activate && python src/canary_cli.py enable 0.1

canary-disable:
	. .venv/bin/activate && python src/canary_cli.py disable

canary-update:
	. .venv/bin/activate && python src/canary_cli.py update 0.25

canary-test-users:
	. .venv/bin/activate && python src/canary_cli.py test user1 user2 user3 user4 user5

# Incident Response Commands
incident-status:
	. .venv/bin/activate && python src/incident_cli.py status

incident-active:
	. .venv/bin/activate && python src/incident_cli.py active

incident-detect:
	. .venv/bin/activate && python src/incident_cli.py detect high_latency high "High latency detected"

incident-auto-detect:
	. .venv/bin/activate && python src/incident_cli.py auto-detect

incident-emergency-ref:
	. .venv/bin/activate && python src/incident_cli.py emergency-ref

runbook-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.runbook import runbook, IncidentType, Severity; print('=== Runbook機能テスト ==='); incident = runbook.detect_incident(IncidentType.HIGH_LATENCY, Severity.HIGH, 'Test incident'); print('Incident detected:', incident.incident_id); procedures = runbook.get_emergency_procedures(IncidentType.HIGH_LATENCY); print('Procedures available:', len(procedures)); print('Summary:', runbook.get_incident_summary())"

# Backup Management Commands
backup-status:
	. .venv/bin/activate && python src/backup_cli.py status

backup-list:
	. .venv/bin/activate && python src/backup_cli.py list

backup-create:
	. .venv/bin/activate && python src/backup_cli.py create --type full --description "Manual backup"

backup-create-index:
	. .venv/bin/activate && python src/backup_cli.py create --type index --description "Index backup"

backup-cleanup:
	. .venv/bin/activate && python src/backup_cli.py cleanup

backup-schedule:
	. .venv/bin/activate && python src/backup_cli.py schedule

backup-report:
	. .venv/bin/activate && python src/backup_cli.py report

backup-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.backup_manager import backup_manager; print('=== バックアップ機能テスト ==='); print('Config:', backup_manager.config); stats = backup_manager.get_backup_statistics(); print('Statistics:', stats); print('Available backups:', len(backup_manager.list_backups()))"

logs-dir:
	mkdir -p logs
