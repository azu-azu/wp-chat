import os, json, numpy as np, faiss
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, conint
from sentence_transformers import SentenceTransformer
from fastapi.responses import JSONResponse
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import load_npz
import joblib
from .rerank import CrossEncoderReranker, mmr_diversify, rerank_with_ce, dedup_by_article, Candidate
from .highlight import highlight_results
from .config import get_config_value

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
MODEL = "all-MiniLM-L6-v2"
TOPK_DEFAULT = get_config_value("api.topk_default", 5)
TOPK_MAX = get_config_value("api.topk_max", 10)
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"

class AskReq(BaseModel):
    question: str
    topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT
    mode: str = "hybrid"  # dense|bm25|hybrid
    rerank: bool = False
    highlight: bool = True  # Enable query highlighting

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
model = SentenceTransformer(MODEL)
index = faiss.read_index(IDX)
meta = json.load(open(META, "r", encoding="utf-8"))
tfidf_vec = joblib.load(TFIDF_VEC) if os.path.exists(TFIDF_VEC) else None
tfidf_mat = load_npz(TFIDF_MAT) if os.path.exists(TFIDF_MAT) else None

def _minmax(x):
    mn, mx = float(x.min()), float(x.max())
    return (x - mn) / (mx - mn + 1e-9)

def _search_dense(q: str, topk: int):
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), topk)
    return list(zip(I[0].tolist(), D[0].tolist()))

def _search_bm25(q: str, topk: int):
    if tfidf_vec is None or tfidf_mat is None:
        raise HTTPException(400, "BM25 index not built. Run build_bm25.py.")
    qv = tfidf_vec.transform([q])
    scores = (tfidf_mat @ qv.T).toarray().ravel()
    ids = np.argsort(-scores)[:topk]
    return [(int(i), float(scores[i])) for i in ids]

def _search_hybrid_with_rerank(q: str, topk: int, wd=0.6, wb=0.4, rerank=False, mmr_lambda=0.7):
    """Enhanced hybrid search with optional reranking"""
    d = _search_dense(q, 200)
    b = _search_bm25(q, 200)
    ids = sorted(set([i for i, _ in d] + [i for i, _ in b]))
    d_map = {i: s for i, s in d}
    b_map = {i: s for i, s in b}
    d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
    b_arr = np.array([b_map.get(i, 0.0) for i in ids], dtype="float32")
    combo = wd * _minmax(d_arr) + wb * _minmax(b_arr)

    # Create Candidate objects
    candidates = []
    for i, score in enumerate(combo):
        if i < len(meta):
            m = meta[i]
            doc_emb = model.encode(m["chunk"], normalize_embeddings=True).astype("float32")
            candidates.append(Candidate(
                doc_id=m["url"],
                chunk_id=m["chunk_id"],
                text=m["chunk"],
                hybrid_score=float(score),
                emb=doc_emb,
                meta={"post_id": m["post_id"], "title": m["title"], "url": m["url"]}
            ))

    # Article deduplication
    candidates = dedup_by_article(candidates, limit_per_article=5)

    # MMR diversification
    q_emb = model.encode(q, normalize_embeddings=True).astype("float32")
    diversified = mmr_diversify(q_emb, candidates, lambda_=mmr_lambda, topn=30)

    # Reranking
    if rerank:
        try:
            ce = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2", batch_size=16)
            ranked = rerank_with_ce(q, diversified, ce, topk=topk, timeout_sec=5.0)
            rerank_status = True
        except Exception as e:
            # Fallback to hybrid scores
            ranked = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]
            rerank_status = False
            print(f"Reranking failed: {e}")
    else:
        ranked = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]
        rerank_status = False

    # Convert back to (idx, score, ce_score) format
    results = []
    for cand in ranked:
        # Find original index in meta
        for i, m in enumerate(meta):
            if m["url"] == cand.doc_id and m["chunk_id"] == cand.chunk_id:
                ce_score = cand.meta.get("ce_score", None)
                results.append((i, cand.hybrid_score, ce_score))
                break

    return results, rerank_status

@app.get("/search")
def search(q: str, topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT, mode: str = "hybrid", rerank: bool = False, highlight: bool = True):
    if not q.strip():
        raise HTTPException(400, "q is empty")
    if mode == "dense":
        hits = _search_dense(q, topk)
        rerank_status = False
    elif mode == "bm25":
        hits = _search_bm25(q, topk)
        rerank_status = False
    else:
        hits, rerank_status = _search_hybrid_with_rerank(q, topk, rerank=rerank)
    out = []
    for rank, hit in enumerate(hits, 1):
        if len(hit) == 3:  # (idx, hybrid_score, ce_score)
            idx, hybrid_sc, ce_sc = hit
        else:  # (idx, score) - backward compatibility
            idx, hybrid_sc = hit
            ce_sc = None

        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]

        result_item = {
            "rank": rank,
            "hybrid_score": hybrid_sc,
            "post_id": m["post_id"],
            "chunk_id": m["chunk_id"],
            "title": m["title"],
            "url": m["url"]
        }

        # Add ce_score if available (for A/B analysis)
        if ce_sc is not None:
            result_item["ce_score"] = ce_sc

        out.append(result_item)

    # Apply highlighting if requested
    if highlight:
        out = highlight_results(out, q, get_config_value("api.snippet_length", 400))

    return JSONResponse({"q": q, "mode": mode, "rerank": rerank_status, "highlight": highlight, "contexts": out})

@app.post("/ask")
def ask(req: AskReq):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "question is empty")
    mode = req.mode
    if mode == "dense":
        pairs = _search_dense(q, req.topk)
        rerank_status = False
    elif mode == "bm25":
        pairs = _search_bm25(q, req.topk)
        rerank_status = False
    else:
        pairs, rerank_status = _search_hybrid_with_rerank(q, req.topk, rerank=req.rerank)
    hits = []
    for rank, hit in enumerate(pairs, 1):
        if len(hit) == 3:  # (idx, hybrid_score, ce_score)
            idx, hybrid_sc, ce_sc = hit
        else:  # (idx, score) - backward compatibility
            idx, hybrid_sc = hit
            ce_sc = None

        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]
        chunk = m["chunk"]
        snip = chunk[:400] + ("…" if len(chunk) > 400 else "")

        hit_item = {
            "rank": rank,
            "hybrid_score": hybrid_sc,
            "post_id": m["post_id"],
            "chunk_id": m["chunk_id"],
            "title": m["title"],
            "url": m["url"],
            "snippet": snip
        }

        # Add ce_score if available (for A/B analysis)
        if ce_sc is not None:
            hit_item["ce_score"] = ce_sc

        hits.append(hit_item)

    # Apply highlighting if requested
    if req.highlight:
        hits = highlight_results(hits, q, get_config_value("api.snippet_length", 400))

    return JSONResponse({"question": q, "mode": mode, "rerank": rerank_status, "highlight": req.highlight, "contexts": hits})
