import os, json, hashlib
import numpy as np
import faiss
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from utils_chunk import sentence_chunks

INP = "data/clean/posts_clean.jsonl"
IDX_DIR = "data/index"
IDX_PATH = os.path.join(IDX_DIR, "wp.faiss")
META_PATH = os.path.join(IDX_DIR, "wp.meta.json")
CACHE_PATH = os.path.join(IDX_DIR, "embeddings.cache.jsonl")  # optional
MODEL_NAME = "all-MiniLM-L6-v2"
DIM = 384

def sha1(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_cache():
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                k, vec = json.loads(line)
                cache[k] = np.array(vec, dtype="float32")
    return cache

def append_cache(k, vec):
    with open(CACHE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps([k, vec.tolist()], ensure_ascii=False) + "\n")

if __name__ == "__main__":
    os.makedirs(IDX_DIR, exist_ok=True)
    model = SentenceTransformer(MODEL_NAME)
    cache = load_cache()
    vectors, metas, ids = [], [], []
    next_id = 0

    with open(INP, "r", encoding="utf-8") as f:
        for line in tqdm(f):
            rec = json.loads(line)
            text = rec.get("text") or ""
            if not text.strip():
                continue
            k = 0
            for ck in sentence_chunks(text, size=900, overlap=150):
                meta = {
                    "post_id": rec["id"], "title": rec["title"],
                    "url": rec["url"], "chunk_id": k, "chunk": ck
                }
                metas.append(meta)
                key = sha1(ck)
                if key in cache:
                    vec = cache[key]
                else:
                    vec = model.encode(ck, normalize_embeddings=True).astype("float32")
                    append_cache(key, vec)
                    cache[key] = vec
                vectors.append(vec)
                ids.append(next_id)
                next_id += 1
                k += 1

    mat = np.vstack(vectors).astype("float32")
    index = faiss.IndexIDMap2(faiss.IndexFlatIP(DIM))
    index.add_with_ids(mat, np.array(ids, dtype="int64"))
    faiss.write_index(index, IDX_PATH)
    with open(META_PATH, "w", encoding="utf-8") as mf:
        json.dump(metas, mf, ensure_ascii=False, indent=2)

    print(f"✅ index -> {IDX_PATH}\n✅ meta  -> {META_PATH}\ncount: {len(ids)}")

