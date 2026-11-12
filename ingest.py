"""Offline ingestion: parse every PDF in docs/, chunk, add context, embed.

    uv run python ingest.py
"""
import json
import time

from rag import chunking, parsing, retrieval
from rag.config import DATA_DIR, DOCS_DIR


def main():
    DATA_DIR.mkdir(exist_ok=True)
    t0 = time.time()

    elements = []
    for pdf in sorted(DOCS_DIR.glob("*.pdf")):
        found = parsing.parse_pdf(pdf)
        kinds = {k: sum(e.kind == k for e in found) for k in ("text", "table", "figure", "scanned_page")}
        print(f"parsed {pdf.name}: {kinds}")
        elements += found
    (DATA_DIR / "elements.json").write_text(json.dumps(parsing.to_dicts(elements), indent=2))

    chunks = chunking.chunk_elements(elements)
    print(f"{len(chunks)} chunks; writing context for each...")
    chunking.add_context(chunks, elements)

    retrieval.build_index(chunks)
    print(f"index written to {DATA_DIR} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
