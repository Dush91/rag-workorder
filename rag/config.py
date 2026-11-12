from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"

# One model for every LLM step. Swap the bulk steps (figure transcription,
# chunk context) to "claude-haiku-5-5" to cut ingest cost on a large corpus.
MODEL = "claude-opus-5-5"

# Local models, downloaded once by fastembed (ONNX, CPU only).
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"

CHUNK_WORDS = 180      # target size for prose chunks; tables and figures are never split
CANDIDATES = 30        # fused BM25 + dense candidates sent to the reranker
TOP_K_PER_QUERY = 5    # reranked chunks kept for each sub-query
MAX_EVIDENCE = 14      # chunks given to the planner after merging all sub-queries
