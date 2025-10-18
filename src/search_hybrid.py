import json, numpy as np, faiss, argparse
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import load_npz
import joblib
from rerank import CrossEncoderReranker, mmr_diversify, rerank_with_ce, dedup_by_article, Candidate

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"
MODEL = "all-MiniLM-L6-v2"

def _minmax(x):
    mn, mx = float(x.min()), float(x.max())
    return (x - mn) / (mx - mn + 1e-9)

def hybrid_search(q: str, k_bm25: int = 100, k_dense: int = 100, alpha: float = 0.6):
    """Hybrid search returning Candidate objects with embeddings"""
    meta = json.load(open(META, "r", encoding="utf-8"))
    model = SentenceTransformer(MODEL)
    index = faiss.read_index(IDX)
    vec: TfidfVectorizer = joblib.load(TFIDF_VEC)
    mat = load_npz(TFIDF_MAT)

    # Dense search
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), k_dense)
    d_ids, d_scores = I[0], D[0]

    # BM25 search
    q_sparse = vec.transform([q])
    s_scores = (mat @ q_sparse.T).toarray().ravel()
    s_top = np.argsort(-s_scores)[:k_bm25]

    # Combine results
    ids = sorted(set(d_ids.tolist()) | set(s_top.tolist()))
    d_map = {int(i): float(s) for i, s in zip(d_ids, d_scores)}
    s_map = {int(i): float(s_scores[i]) for i in s_top}
    d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
    s_arr = np.array([s_map.get(i, 0.0) for i in ids], dtype="float32")

    combo = alpha * _minmax(d_arr) + (1 - alpha) * _minmax(s_arr)

    # Create Candidate objects
    candidates = []
    for i, score in enumerate(combo):
        if i < len(meta):
            m = meta[i]
            # Get dense embedding for this document
            doc_emb = model.encode(m["chunk"], normalize_embeddings=True).astype("float32")
            candidates.append(Candidate(
                doc_id=m["url"],  # Use URL as article identifier
                chunk_id=m["chunk_id"],
                text=m["chunk"],
                hybrid_score=float(score),
                emb=doc_emb,
                meta={"post_id": m["post_id"], "title": m["title"], "url": m["url"]}
            ))

    return candidates

def main(q: str, topk: int, wd: float, wb: float, rerank: str = "none", mmr_lambda: float = 0.7):
    # 1) Hybrid search to get candidates
    candidates = hybrid_search(q, k_bm25=100, k_dense=100, alpha=wd)

    # 2) Article-level deduplication
    candidates = dedup_by_article(candidates, limit_per_article=5)

    # 3) MMR diversification
    model = SentenceTransformer(MODEL)
    q_emb = model.encode(q, normalize_embeddings=True).astype("float32")
    diversified = mmr_diversify(q_emb, candidates, lambda_=mmr_lambda, topn=30)

    # 4) Reranking
    if rerank.startswith("ce"):
        model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ce = CrossEncoderReranker(model_name=model_name, batch_size=16)
        results = rerank_with_ce(q, diversified, ce, topk=topk, timeout_sec=5.0)
        rerank_status = True
    else:
        results = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]
        rerank_status = False

    # 5) Print results
    for rank, cand in enumerate(results, 1):
        snip = cand.text[:200] + ("…" if len(cand.text) > 200 else "")
        score_info = f"hybrid={cand.hybrid_score:.3f}"
        if rerank_status and "ce_score" in cand.meta:
            score_info += f" ce={cand.meta['ce_score']:.3f}"
        print(f"[{rank}] {cand.meta['title']}  {score_info}\n{cand.meta['url']}\n{snip}\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--wd", type=float, default=0.6)
    ap.add_argument("--wb", type=float, default=0.4)
    ap.add_argument("--rerank", default="none", choices=["none", "ce", "ce:mini"])
    ap.add_argument("--mmr_lambda", type=float, default=0.7)
    args = ap.parse_args()
    main(args.query, args.topk, args.wd, args.wb, args.rerank, args.mmr_lambda)
