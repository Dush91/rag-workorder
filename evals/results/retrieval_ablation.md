# Retrieval ablation (22 probes, 16 whole-report queries, 16 chunks)

| Retriever | Chunk text indexed | Probe recall@5 | Probe MRR | Whole-report recall@5 |
|---|---|---|---|---|
| BM25 only | with context | 1.00 | 0.91 | 0.51 |
| Dense only | with context | 1.00 | 0.84 | 0.53 |
| Hybrid (RRF) | with context | 1.00 | 0.90 | 0.55 |
| Hybrid + rerank | with context | 1.00 | 0.97 | 0.41 |
| BM25 only | raw chunk only | 0.98 | 0.92 | 0.46 |
| Dense only | raw chunk only | 0.86 | 0.83 | 0.41 |
| Hybrid (RRF) | raw chunk only | 0.98 | 0.88 | 0.49 |
| Hybrid + rerank | raw chunk only | 0.98 | 0.86 | 0.34 |
