import json, numpy as np, faiss, argparse
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import load_npz
import joblib

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"
MODEL = "all-MiniLM-L6-v2"

def _minmax(x):
    mn, mx = float(x.min()), float(x.max())
    return (x - mn) / (mx - mn + 1e-9)

def main(q: str, topk: int, wd: float, wb: float):
    meta = json.load(open(META, "r", encoding="utf-8"))
    model = SentenceTransformer(MODEL)
    index = faiss.read_index(IDX)
    vec: TfidfVectorizer = joblib.load(TFIDF_VEC)
    mat = load_npz(TFIDF_MAT)

    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), 200)
    d_ids, d_scores = I[0], D[0]

    q_sparse = vec.transform([q])
    s_scores = (mat @ q_sparse.T).toarray().ravel()
    s_top = np.argsort(-s_scores)[:200]

    ids = sorted(set(d_ids.tolist()) | set(s_top.tolist()))
    d_map = {int(i): float(s) for i, s in zip(d_ids, d_scores)}
    s_map = {int(i): float(s_scores[i]) for i in s_top}
    d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
    s_arr = np.array([s_map.get(i, 0.0) for i in ids], dtype="float32")

    combo = wd * _minmax(d_arr) + wb * _minmax(s_arr)
    order = np.argsort(-combo)[:topk]
    for rank, j in enumerate(order, 1):
        mid = ids[j]
        m = meta[mid]
        snip = m["chunk"][:200] + ("…" if len(m["chunk"]) > 200 else "")
        print(f"[{rank}] {m['title']}  score={combo[j]:.3f}\n{m['url']}\n{snip}\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--wd", type=float, default=0.6)
    ap.add_argument("--wb", type=float, default=0.4)
    args = ap.parse_args()
    main(args.query, args.topk, args.wd, args.wb)


