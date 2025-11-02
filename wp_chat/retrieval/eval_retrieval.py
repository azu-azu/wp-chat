import argparse
import json
import math
import os

import faiss
import joblib
import numpy as np
from scipy.sparse import load_npz
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

from .rerank import Candidate, CrossEncoderReranker, dedup_by_article, mmr_diversify, rerank_with_ce

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"
MODEL = "all-MiniLM-L6-v2"


def dcg(rels: list[int]) -> float:
    return sum((rel / math.log2(i + 2)) for i, rel in enumerate(rels))


def ndcg_at_k(rels: list[int], k: int) -> float:
    rels_k = rels[:k]
    ideal = sorted(rels, reverse=True)[:k]
    denom = dcg(ideal) or 1.0
    return dcg(rels_k) / denom


def load_dense():
    model = SentenceTransformer(MODEL)
    index = faiss.read_index(IDX)
    meta = json.load(open(META, encoding="utf-8"))
    return model, index, meta


def load_sparse():
    if not (os.path.exists(TFIDF_VEC) and os.path.exists(TFIDF_MAT)):
        raise RuntimeError("BM25 index not found. Run build_bm25.py first.")
    vec = joblib.load(TFIDF_VEC)
    mat = load_npz(TFIDF_MAT)
    meta = json.load(open(META, encoding="utf-8"))
    return vec, mat, meta


def retrieve_dense(q: str, topk: int) -> list[tuple[int, float]]:
    model, index, _ = load_dense()
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), topk)  # noqa: N806, E741
    return list(zip(I[0].tolist(), D[0].tolist(), strict=True))


def retrieve_bm25(q: str, topk: int) -> list[tuple[int, float]]:
    vec, mat, _ = load_sparse()
    qv = vec.transform([q])
    scores = (mat @ qv.T).toarray().ravel()
    idx = np.argsort(-scores)[:topk]
    return [(int(i), float(scores[i])) for i in idx]


def minmax_norm(scores: np.ndarray) -> np.ndarray:
    mn, mx = float(scores.min()), float(scores.max())
    return (scores - mn) / (mx - mn + 1e-9)


def retrieve_hybrid(
    q: str, topk: int, wd=0.6, wb=0.4, rerank_mode="none", mmr_lambda=0.7
) -> tuple[list[tuple[int, float]], dict]:
    """Enhanced hybrid retrieval with optional reranking"""
    meta = json.load(open(META, encoding="utf-8"))
    model = SentenceTransformer(MODEL)
    index = faiss.read_index(IDX)
    vec: TfidfVectorizer = joblib.load(TFIDF_VEC)
    mat = load_npz(TFIDF_MAT)

    # Dense search
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), 200)  # noqa: N806, E741
    d_ids, d_scores = I[0], D[0]

    # BM25 search
    q_sparse = vec.transform([q])
    s_scores = (mat @ q_sparse.T).toarray().ravel()
    s_top = np.argsort(-s_scores)[:200]

    # Combine results
    ids = sorted(set(d_ids.tolist()) | set(s_top.tolist()))
    d_map = {int(i): float(s) for i, s in zip(d_ids, d_scores, strict=True)}
    s_map = {int(i): float(s_scores[i]) for i in s_top}
    d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
    s_arr = np.array([s_map.get(i, 0.0) for i in ids], dtype="float32")

    combo = wd * minmax_norm(d_arr) + wb * minmax_norm(s_arr)

    # Create Candidate objects
    candidates = []
    for i, score in enumerate(combo):
        if i < len(meta):
            m = meta[i]
            doc_emb = model.encode(m["chunk"], normalize_embeddings=True).astype("float32")
            candidates.append(
                Candidate(
                    doc_id=m["url"],
                    chunk_id=m["chunk_id"],
                    text=m["chunk"],
                    hybrid_score=float(score),
                    emb=doc_emb,
                    meta={"post_id": m["post_id"], "title": m["title"], "url": m["url"]},
                )
            )

    # Article deduplication
    candidates = dedup_by_article(candidates, limit_per_article=5)

    # MMR diversification
    q_emb = model.encode(q, normalize_embeddings=True).astype("float32")
    diversified = mmr_diversify(q_emb, candidates, lambda_=mmr_lambda, topn=30)

    # Reranking
    if rerank_mode.startswith("ce"):
        ce = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2", batch_size=16)
        ranked = rerank_with_ce(q, diversified, ce, topk=topk, timeout_sec=5.0)
        rerank_info = {"rerank": "ce"}
    else:
        ranked = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]
        rerank_info = {"rerank": "none"}

    # Convert back to (doc_id, score) format for compatibility
    results = []
    for cand in ranked:
        # Find original index in meta
        for i, m in enumerate(meta):
            if m["url"] == cand.doc_id and m["chunk_id"] == cand.chunk_id:
                results.append((i, cand.hybrid_score))
                break

    return results, rerank_info


def evaluate(mode: str, k: int, eval_path: str, rerank_mode: str = "none", mmr_lambda: float = 0.7):
    meta = json.load(open(META, encoding="utf-8"))

    def retrieve(q: str):
        if mode == "dense":
            return retrieve_dense(q, k)
        if mode == "bm25":
            return retrieve_bm25(q, k)
        if mode == "hybrid":
            results, rerank_info = retrieve_hybrid(
                q, k, rerank_mode=rerank_mode, mmr_lambda=mmr_lambda
            )
            return results
        return retrieve_hybrid(q, k, rerank_mode=rerank_mode, mmr_lambda=mmr_lambda)[0]

    qs, recalls, mrrs, ndcgs = 0, [], [], []
    with open(eval_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            q = item["q"]
            gold_urls = set(item["gold_urls"])
            hits = retrieve(q)
            urls = [meta[i]["url"] for i, _ in hits if 0 <= i < len(meta)]
            rels = [1 if u in gold_urls else 0 for u in urls]
            recalls.append(1.0 if any(rels) else 0.0)
            rr = 0.0
            for rank, r in enumerate(rels, 1):
                if r == 1:
                    rr = 1.0 / rank
                    break
            mrrs.append(rr)
            ndcgs.append(ndcg_at_k(rels, k))
            qs += 1

    def avg(x):
        return sum(x) / max(1, len(x))

    rerank_suffix = f" rerank={rerank_mode}" if rerank_mode != "none" else ""
    print(
        f"mode={mode} k={k} N={qs}{rerank_suffix} | R@{k}={avg(recalls):.3f} MRR={avg(mrrs):.3f} nDCG@{k}={avg(ndcgs):.3f}"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["dense", "bm25", "hybrid"], default="dense")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--eval", default="eval/queries.jsonl")
    ap.add_argument("--rerank", default="none", choices=["none", "ce", "ce:mini"])
    ap.add_argument("--mmr_lambda", type=float, default=0.7)
    args = ap.parse_args()
    evaluate(args.mode, args.k, args.eval, args.rerank, args.mmr_lambda)
