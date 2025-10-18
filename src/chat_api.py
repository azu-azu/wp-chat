import os, json, numpy as np, faiss
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, conint
from sentence_transformers import SentenceTransformer
from fastapi.responses import JSONResponse
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import load_npz
import joblib

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
MODEL = "all-MiniLM-L6-v2"
TOPK_DEFAULT = 5
TOPK_MAX = 10
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"

class AskReq(BaseModel):
    question: str
    topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT
    mode: str = "hybrid"  # dense|bm25|hybrid

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

def _search_hybrid(q: str, topk: int, wd=0.6, wb=0.4):
    d = _search_dense(q, 200)
    b = _search_bm25(q, 200)
    ids = sorted(set([i for i, _ in d] + [i for i, _ in b]))
    d_map = {i: s for i, s in d}
    b_map = {i: s for i, s in b}
    d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
    b_arr = np.array([b_map.get(i, 0.0) for i in ids], dtype="float32")
    combo = wd * _minmax(d_arr) + wb * _minmax(b_arr)
    order = np.argsort(-combo)[:topk]
    return [(ids[j], float(combo[j])) for j in order]

@app.get("/search")
def search(q: str, topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT, mode: str = "hybrid"):
    if not q.strip():
        raise HTTPException(400, "q is empty")
    if mode == "dense":
        hits = _search_dense(q, topk)
    elif mode == "bm25":
        hits = _search_bm25(q, topk)
    else:
        hits = _search_hybrid(q, topk)
    out = []
    for rank, (idx, sc) in enumerate(hits, 1):
        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]
        out.append({
            "rank": rank,
            "score": sc,
            "post_id": m["post_id"],
            "chunk_id": m["chunk_id"],
            "title": m["title"],
            "url": m["url"]
        })
    return JSONResponse({"q": q, "mode": mode, "contexts": out})

@app.post("/ask")
def ask(req: AskReq):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "question is empty")
    mode = req.mode
    if mode == "dense":
        pairs = _search_dense(q, req.topk)
    elif mode == "bm25":
        pairs = _search_bm25(q, req.topk)
    else:
        pairs = _search_hybrid(q, req.topk)
    hits = []
    for rank, (idx, sc) in enumerate(pairs, 1):
        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]
        chunk = m["chunk"]
        snip = chunk[:400] + ("…" if len(chunk) > 400 else "")
        hits.append({
            "rank": rank,
            "score": sc,
            "post_id": m["post_id"],
            "chunk_id": m["chunk_id"],
            "title": m["title"],
            "url": m["url"],
            "snippet": snip
        })
    return JSONResponse({"question": q, "mode": mode, "contexts": hits})

