"""Retrieval ablation: which parts of the retrieval stack earn their place?

Free to run (local embedder + reranker only, no Claude calls):

    uv run python evals/retrieval_ablation.py

Two query sets, both with hand-labelled gold chunks from evals/cases.json:
  - probes:   short targeted queries, like the ones the planner's decomposition step writes
  - reports:  each whole fault report as a single query (what you'd get without decomposition),
              scored at the same k=5 against all of that case's gold evidence

Each retriever config runs with and without the contextual-retrieval line on every chunk.
Writes evals/results/retrieval_ablation.md and .json.
"""
import json
import sys
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.chunking import Chunk  # noqa: E402
from rag.config import CANDIDATES, DATA_DIR, EMBED_MODEL, RERANK_MODEL  # noqa: E402
from rag.retrieval import RRF_K, tokenize  # noqa: E402

EVALS = Path(__file__).resolve().parent
OUT = EVALS / "results"
K = 5  # TOP_K_PER_QUERY in the app


def resolve(snippet, chunks):
    ids = [c.id for c in chunks if snippet in c.text]
    assert len(ids) == 1, f"gold snippet {snippet!r} matched {ids}"
    return ids[0]


class Index:
    def __init__(self, chunks, texts, embedder, reranker):
        self.chunks, self.texts = chunks, texts
        v = np.array(list(embedder.embed(texts)))
        self.vectors = v / np.linalg.norm(v, axis=1, keepdims=True)
        self._bm25 = BM25Okapi([tokenize(t) for t in texts])
        self.embedder, self.reranker = embedder, reranker

    def bm25(self, q):
        return list(np.argsort(-self._bm25.get_scores(tokenize(q))))

    def dense(self, q):
        e = next(iter(self.embedder.query_embed(q)))
        return list(np.argsort(-(self.vectors @ (e / np.linalg.norm(e)))))

    def hybrid(self, q):
        fused = {}
        for ranking in (self.bm25(q), self.dense(q)):
            for rank, i in enumerate(ranking[:CANDIDATES]):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        return sorted(fused, key=fused.get, reverse=True)

    def rerank(self, q):
        cands = self.hybrid(q)[:CANDIDATES]
        scores = list(self.reranker.rerank(q, [self.texts[i] for i in cands]))
        return [i for i, _ in sorted(zip(cands, scores), key=lambda p: p[1], reverse=True)]

    def ranked_ids(self, method, q):
        return [self.chunks[i].id for i in getattr(self, method)(q)]


def score(ranked, gold, k):
    top = ranked[:k]
    recall = sum(g in top for g in gold) / len(gold)
    first = next((r for r, cid in enumerate(ranked, 1) if cid in gold), None)
    return recall, (1.0 / first if first else 0.0)


def main():
    chunks = [Chunk(**c) for c in json.loads((DATA_DIR / "chunks.json").read_text())]
    cases = json.loads((EVALS / "cases.json").read_text())["cases"]
    probes = [(q, [resolve(s, chunks) for s in gold]) for c in cases for q, gold in c["probes"]]
    reports = [(c["report"], [resolve(s, chunks) for s in c["gold"]]) for c in cases]

    embedder, reranker = TextEmbedding(EMBED_MODEL), TextCrossEncoder(RERANK_MODEL)
    indexes = {
        "with context": Index(chunks, [c.indexed_text for c in chunks], embedder, reranker),
        "raw chunk only": Index(chunks, [c.text for c in chunks], embedder, reranker),
    }
    methods = [("bm25", "BM25 only"), ("dense", "Dense only"),
               ("hybrid", "Hybrid (RRF)"), ("rerank", "Hybrid + rerank")]

    rows = []
    for ctx_name, idx in indexes.items():
        for m, label in methods:
            p = [score(idx.ranked_ids(m, q), g, K) for q, g in probes]
            r = [score(idx.ranked_ids(m, q), g, K)[0] for q, g in reports]
            rows.append({"retriever": label, "chunk_text": ctx_name,
                         "probe_recall@5": float(np.mean([x[0] for x in p])),
                         "probe_mrr": float(np.mean([x[1] for x in p])),
                         "report_recall@5": float(np.mean(r))})

    OUT.mkdir(exist_ok=True)
    (OUT / "retrieval_ablation.json").write_text(json.dumps(
        {"n_probes": len(probes), "n_reports": len(reports), "rows": rows}, indent=2))
    md = [f"# Retrieval ablation ({len(probes)} probes, {len(reports)} whole-report queries, "
          f"{len(chunks)} chunks)", "",
          "| Retriever | Chunk text indexed | Probe recall@5 | Probe MRR | Whole-report recall@5 |",
          "|---|---|---|---|---|"]
    md += [f"| {r['retriever']} | {r['chunk_text']} | {r['probe_recall@5']:.2f} | {r['probe_mrr']:.2f} "
           f"| {r['report_recall@5']:.2f} |" for r in rows]
    (OUT / "retrieval_ablation.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
