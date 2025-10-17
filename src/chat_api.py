import os, json, numpy as np, faiss
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, conint
from sentence_transformers import SentenceTransformer
from fastapi.responses import JSONResponse

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
MODEL = "all-MiniLM-L6-v2"
TOPK_DEFAULT = 5
TOPK_MAX = 10

class AskReq(BaseModel):
    question: str
    topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT

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

@app.post("/ask")
def ask(req: AskReq):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "question is empty")
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), req.topk)
    hits = []
    for rank, idx in enumerate(I[0].tolist(), 1):
        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]
        chunk = m["chunk"]
        snip = chunk[:400] + ("…" if len(chunk) > 400 else "")
        hits.append({"rank": rank, "title": m["title"], "url": m["url"], "snippet": snip})
    return JSONResponse({"question": q, "contexts": hits})

