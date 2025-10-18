# src/rerank.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
import math, time
from functools import lru_cache

import numpy as np
from sentence_transformers import CrossEncoder

@dataclass
class Candidate:
    doc_id: str          # article id or url
    chunk_id: int
    text: str
    hybrid_score: float  # 0-1 normalized before渡し
    emb: np.ndarray      # dense embedding (for MMR用)
    meta: dict

class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                device: Optional[str] = None,
                batch_size: int = 16):
        self.model = CrossEncoder(model_name, device=device)
        self.batch_size = batch_size

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-x))

    @lru_cache(maxsize=4096)
    def _score_pair_cached(self, q: str, d: str) -> float:
        # NOTE: 1件だけの推論は低速なのでバッチを優先。これはフォールバック用途。
        return float(self._sigmoid(np.array(self.model.predict([(q, d)]))))  # 0-1

    def score_pairs(self, q: str, docs: List[str]) -> List[float]:
        pairs = [(q, d) for d in docs]
        scores: List[float] = []
        for i in range(0, len(pairs), self.batch_size):
            chunk = pairs[i:i+self.batch_size]
            s = self.model.predict(chunk)  # raw
            s = self._sigmoid(np.array(s))  # 0-1
            scores.extend(s.tolist())
        return scores

def mmr_diversify(query_emb: np.ndarray,
                candidates: List[Candidate],
                lambda_: float = 0.7,
                topn: int = 30) -> List[Candidate]:
    """
    MMR (Maximal Marginal Relevance)
    relevance: candidate.hybrid_score（0-1）
    diversity: cosine(query_emb, cand.emb) と cand間の類似を使う
    """
    if not candidates:
        return []

    selected: List[Candidate] = []
    remaining = candidates.copy()

    # 事前正規化（安全策）：embはL2正規化前提
    def cos(a: np.ndarray, b: np.ndarray) -> float:
        # assume a,b normalized
        return float(np.dot(a, b))

    # 先頭は最も関連（hybrid_score最大）
    remaining.sort(key=lambda c: c.hybrid_score, reverse=True)
    selected.append(remaining.pop(0))

    while remaining and len(selected) < topn:
        mmr_scores: List[Tuple[float, Candidate]] = []
        for cand in remaining:
            rel = cand.hybrid_score
            div = max(cos(cand.emb, s.emb) for s in selected)  # 既選択との最大類似
            mmr = lambda_ * rel - (1 - lambda_) * div
            mmr_scores.append((mmr, cand))
        mmr_scores.sort(key=lambda x: x[0], reverse=True)
        best = mmr_scores[0][1]
        selected.append(best)
        remaining.remove(best)

    return selected

def rerank_with_ce(query: str,
                diversified: List[Candidate],
                ce: CrossEncoderReranker,
                topk: int = 10,
                timeout_sec: float = 5.0) -> List[Candidate]:
    if not diversified:
        return []

    start = time.time()
    try:
        texts = [c.text for c in diversified]
        ce_scores = ce.score_pairs(query, texts)  # 0-1
        elapsed = time.time() - start
        # タイムアウト超過チェック（バッチ後でも超過ならフォールバック）
        if elapsed > timeout_sec:
            # フォールバック：hybrid順
            return sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]

        for c, s in zip(diversified, ce_scores):
            c.meta["ce_score"] = float(s)

        # 最終はCEスコア優先（必要なら線形合成も可）
        ranked = sorted(diversified, key=lambda c: c.meta["ce_score"], reverse=True)
        return ranked[:topk]

    except Exception as e:
        # 失敗時はフォールバック
        for c in diversified:
            c.meta["ce_error"] = str(e)
        return sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]

def dedup_by_article(candidates: List[Candidate], limit_per_article: int = 5) -> List[Candidate]:
    """
    Article-level deduplication: limit consecutive hits from same article
    """
    if not candidates:
        return []

    # Group by article (using doc_id as article identifier)
    article_counts = {}
    deduped = []

    for cand in candidates:
        article_id = cand.doc_id
        if article_counts.get(article_id, 0) < limit_per_article:
            deduped.append(cand)
            article_counts[article_id] = article_counts.get(article_id, 0) + 1

    return deduped
