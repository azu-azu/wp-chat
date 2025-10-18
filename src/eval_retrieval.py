import os, json, math, numpy as np, faiss
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import load_npz
import argparse, joblib

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"
MODEL = "all-MiniLM-L6-v2"

def dcg(rels: List[int]) -> float:
    return sum((rel / math.log2(i + 2)) for i, rel in enumerate(rels))

def ndcg_at_k(rels: List[int], k: int) -> float:
    rels_k = rels[:k]
    ideal = sorted(rels, reverse=True)[:k]
    denom = dcg(ideal) or 1.0
    return dcg(rels_k) / denom

def load_dense():
    model = SentenceTransformer(MODEL)
    index = faiss.read_index(IDX)
    meta = json.load(open(META, "r", encoding="utf-8"))
    return model, index, meta

def load_sparse():
    if not (os.path.exists(TFIDF_VEC) and os.path.exists(TFIDF_MAT)):
        raise RuntimeError("BM25 index not found. Run build_bm25.py first.")
    vec = joblib.load(TFIDF_VEC)
    mat = load_npz(TFIDF_MAT)
    meta = json.load(open(META, "r", encoding="utf-8"))
    return vec, mat, meta

def retrieve_dense(q: str, topk: int) -> List[Tuple[int, float]]:
    model, index, _ = load_dense()
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), topk)
    return list(zip(I[0].tolist(), D[0].tolist()))

def retrieve_bm25(q: str, topk: int) -> List[Tuple[int, float]]:
    vec, mat, _ = load_sparse()
    qv = vec.transform([q])
    scores = (mat @ qv.T).toarray().ravel()
    idx = np.argsort(-scores)[:topk]
    return [(int(i), float(scores[i])) for i in idx]

def minmax_norm(scores: np.ndarray) -> np.ndarray:
    mn, mx = float(scores.min()), float(scores.max())
    return (scores - mn) / (mx - mn + 1e-9)

def retrieve_hybrid(q: str, topk: int, wd=0.6, wb=0.4) -> List[Tuple[int, float]]:
    d_hits = retrieve_dense(q, topk=200)
    b_hits = retrieve_bm25(q, topk=200)
    ids = sorted(set([i for i, _ in d_hits] + [i for i, _ in b_hits]))
    d_map = {i: s for i, s in d_hits}
    b_map = {i: s for i, s in b_hits}
    d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
    b_arr = np.array([b_map.get(i, 0.0) for i in ids], dtype="float32")
    combo = wd * minmax_norm(d_arr) + wb * minmax_norm(b_arr)
    order = np.argsort(-combo)[:topk]
    return [(ids[i], float(combo[i])) for i in order]

def evaluate(mode: str, k: int, eval_path: str):
    meta = json.load(open(META, "r", encoding="utf-8"))
    def retrieve(q: str):
        if mode == "dense":
            return retrieve_dense(q, k)
        if mode == "bm25":
            return retrieve_bm25(q, k)
        return retrieve_hybrid(q, k)

    qs, recalls, mrrs, ndcgs = 0, [], [], []
    with open(eval_path, "r", encoding="utf-8") as f:
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

    print(
        f"mode={mode} k={k} N={qs} | R@{k}={avg(recalls):.3f} MRR={avg(mrrs):.3f} nDCG@{k}={avg(ndcgs):.3f}"
    )

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["dense", "bm25", "hybrid"], default="dense")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--eval", default="eval/queries.jsonl")
    args = ap.parse_args()
    evaluate(args.mode, args.k, args.eval)


