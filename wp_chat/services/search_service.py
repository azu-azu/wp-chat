"""
Search Service - Encapsulates search business logic

This service handles all search operations including:
- Dense search (FAISS)
- BM25 search (TF-IDF)
- Hybrid search with reranking
- MMR diversification
"""

import numpy as np
from fastapi import HTTPException

from ..retrieval.rerank import (
    Candidate,
    CrossEncoderReranker,
    dedup_by_article,
    mmr_diversify,
    rerank_with_ce,
)


class SearchResult:
    """Search result data class"""

    def __init__(
        self,
        query: str,
        mode: str,
        rerank_enabled: bool,
        results: list[tuple[int, float, float | None]],
    ):
        self.query = query
        self.mode = mode
        self.rerank_enabled = rerank_enabled
        self.results = results  # List of (idx, hybrid_score, ce_score)


class SearchService:
    """Service for handling search operations"""

    def __init__(self, model, index, meta, tfidf_vec, tfidf_mat):
        """
        Initialize search service with required resources

        Args:
            model: SentenceTransformer model for embeddings
            index: FAISS index for dense search
            meta: Metadata for documents
            tfidf_vec: TF-IDF vectorizer for BM25
            tfidf_mat: TF-IDF matrix for BM25
        """
        self.model = model
        self.index = index
        self.meta = meta
        self.tfidf_vec = tfidf_vec
        self.tfidf_mat = tfidf_mat

    def _minmax(self, x: np.ndarray) -> np.ndarray:
        """Normalize scores using min-max normalization"""
        mn, mx = float(x.min()), float(x.max())
        return (x - mn) / (mx - mn + 1e-9)

    def search_dense(self, query: str, topk: int) -> list[tuple[int, float]]:
        """
        Perform dense (semantic) search using FAISS

        Args:
            query: Search query
            topk: Number of results to return

        Returns:
            List of (doc_id, score) tuples
        """
        qv = self.model.encode(query, normalize_embeddings=True).astype("float32")
        D, I = self.index.search(np.expand_dims(qv, 0), topk)  # noqa: N806, E741
        return list(zip(I[0].tolist(), D[0].tolist(), strict=True))

    def search_bm25(self, query: str, topk: int) -> list[tuple[int, float]]:
        """
        Perform BM25 (keyword) search using TF-IDF

        Args:
            query: Search query
            topk: Number of results to return

        Returns:
            List of (doc_id, score) tuples

        Raises:
            HTTPException: If BM25 index is not built
        """
        if self.tfidf_vec is None or self.tfidf_mat is None:
            raise HTTPException(400, "BM25 index not built. Run build_bm25.py.")

        qv = self.tfidf_vec.transform([query])
        scores = (self.tfidf_mat @ qv.T).toarray().ravel()
        ids = np.argsort(-scores)[:topk]
        return [(int(i), float(scores[i])) for i in ids]

    def search_hybrid_with_rerank(
        self,
        query: str,
        topk: int,
        wd: float = 0.6,
        wb: float = 0.4,
        rerank: bool = False,
        mmr_lambda: float = 0.7,
    ) -> tuple[list[tuple[int, float, float | None]], bool]:
        """
        Perform hybrid search with optional reranking

        Args:
            query: Search query
            topk: Number of results to return
            wd: Weight for dense search (default: 0.6)
            wb: Weight for BM25 search (default: 0.4)
            rerank: Whether to use cross-encoder reranking
            mmr_lambda: Lambda parameter for MMR diversification (default: 0.7)

        Returns:
            Tuple of (results, rerank_status)
            - results: List of (idx, hybrid_score, ce_score) tuples
            - rerank_status: Whether reranking was successfully applied
        """
        # Step 1: Get candidates from both dense and BM25 search
        d = self.search_dense(query, 200)
        b = self.search_bm25(query, 200)

        # Step 2: Combine and normalize scores
        ids = sorted(set([i for i, _ in d] + [i for i, _ in b]))
        d_map = {i: s for i, s in d}
        b_map = {i: s for i, s in b}
        d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
        b_arr = np.array([b_map.get(i, 0.0) for i in ids], dtype="float32")
        combo = wd * self._minmax(d_arr) + wb * self._minmax(b_arr)

        # Step 3: Create Candidate objects
        candidates = []
        for i, score in enumerate(combo):
            if i < len(self.meta):
                m = self.meta[i]
                doc_emb = self.model.encode(m["chunk"], normalize_embeddings=True).astype("float32")
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

        # Step 4: Article deduplication
        candidates = dedup_by_article(candidates, limit_per_article=5)

        # Step 5: MMR diversification
        q_emb = self.model.encode(query, normalize_embeddings=True).astype("float32")
        diversified = mmr_diversify(q_emb, candidates, lambda_=mmr_lambda, topn=30)

        # Step 6: Reranking (optional)
        rerank_status = False
        if rerank:
            try:
                ce = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2", batch_size=16)
                ranked = rerank_with_ce(query, diversified, ce, topk=topk, timeout_sec=5.0)
                rerank_status = True
            except Exception as e:
                # Fallback to hybrid scores
                ranked = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]
                print(f"Reranking failed: {e}")
        else:
            ranked = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]

        # Step 7: Convert back to (idx, score, ce_score) format
        results = []
        for cand in ranked:
            # Find original index in meta
            for i, m in enumerate(self.meta):
                if m["url"] == cand.doc_id and m["chunk_id"] == cand.chunk_id:
                    ce_score = cand.meta.get("ce_score", None)
                    results.append((i, cand.hybrid_score, ce_score))
                    break

        return results, rerank_status

    def execute_search(
        self,
        query: str,
        topk: int,
        mode: str = "hybrid",
        rerank: bool = False,
    ) -> SearchResult:
        """
        Execute search based on specified mode

        Args:
            query: Search query
            topk: Number of results to return
            mode: Search mode ("dense", "bm25", or "hybrid")
            rerank: Whether to use reranking (only for hybrid mode)

        Returns:
            SearchResult object containing search results

        Raises:
            ValueError: If invalid mode is specified
        """
        if mode == "dense":
            hits = self.search_dense(query, topk)
            # Convert to (idx, score, None) format
            results = [(idx, score, None) for idx, score in hits]
            rerank_status = False

        elif mode == "bm25":
            hits = self.search_bm25(query, topk)
            # Convert to (idx, score, None) format
            results = [(idx, score, None) for idx, score in hits]
            rerank_status = False

        elif mode == "hybrid":
            results, rerank_status = self.search_hybrid_with_rerank(query, topk, rerank=rerank)

        else:
            raise ValueError(f"Invalid search mode: {mode}")

        return SearchResult(query=query, mode=mode, rerank_enabled=rerank_status, results=results)
