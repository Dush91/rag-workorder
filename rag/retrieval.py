"""Hybrid retrieval: BM25 + dense embeddings, fused with Reciprocal Rank Fusion, then reranked.

BM25 catches exact tokens that embeddings blur ("HF3-450B", "M10", "7.1"); dense search
catches paraphrase ("water dripping from the shaft" -> "leakage at shaft seal"). RRF merges
the two rankings without having to calibrate their scores, and a cross-encoder reranker
reads each query-chunk pair together to put the best evidence first.
"""
import json
import re

import numpy as np
from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from rank_bm25 import BM25Okapi

from .chunking import Chunk
from .config import CANDIDATES, DATA_DIR, EMBED_MODEL, RERANK_MODEL

TOKEN = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")  # keeps "hf3-450b" and "7.1" as single tokens
RRF_K = 60


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def build_index(chunks: list[Chunk]) -> None:
    vectors = np.array(list(TextEmbedding(EMBED_MODEL).embed([c.indexed_text for c in chunks])))
    np.save(DATA_DIR / "embeddings.npy", vectors)
    (DATA_DIR / "chunks.json").write_text(json.dumps([c.__dict__ for c in chunks], indent=2))


class Retriever:
    def __init__(self):
        self.chunks = [Chunk(**c) for c in json.loads((DATA_DIR / "chunks.json").read_text())]
        vectors = np.load(DATA_DIR / "embeddings.npy")
        self.vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        self.bm25 = BM25Okapi([tokenize(c.indexed_text) for c in self.chunks])
        self.embedder = TextEmbedding(EMBED_MODEL)
        self.reranker = TextCrossEncoder(RERANK_MODEL)

    def _dense_ranking(self, query: str) -> np.ndarray:
        q = next(iter(self.embedder.query_embed(query)))
        return np.argsort(-(self.vectors @ (q / np.linalg.norm(q))))

    def _bm25_ranking(self, query: str) -> np.ndarray:
        return np.argsort(-self.bm25.get_scores(tokenize(query)))

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        fused: dict[int, float] = {}
        for ranking in (self._bm25_ranking(query), self._dense_ranking(query)):
            for rank, idx in enumerate(ranking[:CANDIDATES]):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
        candidates = sorted(fused, key=fused.get, reverse=True)[:CANDIDATES]

        scores = list(self.reranker.rerank(query, [self.chunks[i].indexed_text for i in candidates]))
        ranked = sorted(zip(candidates, scores), key=lambda p: p[1], reverse=True)
        return [(self.chunks[i], float(s)) for i, s in ranked[:k]]
