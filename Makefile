eval:
	. .venv/bin/activate && python src/eval_retrieval.py --mode hybrid --k 5

bm25:
	. .venv/bin/activate && python src/build_bm25.py

hybrid:
	. .venv/bin/activate && python src/search_hybrid.py --query "お問い合わせ" --topk 5


