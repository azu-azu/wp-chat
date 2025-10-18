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

rate-limit-test:
	. .venv/bin/activate && python -c "import sys; sys.path.append('src'); from src.rate_limit import rate_limiter; allowed, info = rate_limiter.is_allowed('test_client', 5, 60); print('Rate limit test:', 'ALLOWED' if allowed else 'BLOCKED'); print('Rate info:', info); print('Global stats:', rate_limiter.get_global_stats())"

logs-dir:
	mkdir -p logs


