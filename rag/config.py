import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"

# Project-local secrets (git-ignored), e.g. DOUBLEWORD_API_KEY. The .env file wins over
# the shell environment so a stale key exported in a shell profile can't shadow it.
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

# One model for every LLM step. "claude-*" IDs go to the Anthropic API; any other ID goes to
# Doubleword's OpenAI-compatible API (e.g. APP_MODEL=deepseek-ai/DeepSeek-V4-Pro-0813).
# Swap the bulk ingest steps to "claude-haiku-5-5" to cut cost on a large corpus.
MODEL = os.getenv("APP_MODEL", "claude-opus-5-5")
DOUBLEWORD_BASE_URL = os.getenv("DOUBLEWORD_BASE_URL", "https://api.doubleword.ai/v1")

# Local models, downloaded once by fastembed (ONNX, CPU only).
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"

CHUNK_WORDS = 180      # target size for prose chunks; tables and figures are never split
CANDIDATES = 30        # fused BM25 + dense candidates sent to the reranker
TOP_K_PER_QUERY = 5    # reranked chunks kept for each sub-query
MAX_EVIDENCE = 14      # chunks given to the planner after merging all sub-queries
