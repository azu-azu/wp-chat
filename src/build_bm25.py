import os, json
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import save_npz
import joblib

META = "data/index/wp.meta.json"
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"

if __name__ == "__main__":
    os.makedirs("data/index", exist_ok=True)
    meta = json.load(open(META, "r", encoding="utf-8"))
    docs = [m["chunk"] for m in meta]
    # 日本語向けの素朴な字n-gram TF-IDF（BM25厳密実装ではないが実務で効く）
    vec = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        min_df=2,
        max_features=200000,
        lowercase=False,
        norm="l2",
    )
    X = vec.fit_transform(docs)
    joblib.dump(vec, TFIDF_VEC)
    save_npz(TFIDF_MAT, X)
    print(f"✅ tfidf -> {TFIDF_VEC}\n✅ matrix -> {TFIDF_MAT}\ncount: {X.shape[0]}")


