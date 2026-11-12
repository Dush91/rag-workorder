"""Structure-aware chunking plus Anthropic-style contextual retrieval.

Tables, figures and scanned pages stay whole: splitting a torque table in half is how a
RAG system ends up quoting the wrong bolt. Prose is packed into ~CHUNK_WORDS chunks that
never cross a page. Each chunk then gets a short, LLM-written context line that says
where it sits in its document, and that line is indexed together with the chunk.
"""
from dataclasses import asdict, dataclass

from . import llm
from .config import CHUNK_WORDS
from .parsing import Element

CONTEXT_PROMPT = """<chunk>
{chunk}
</chunk>
Write one or two sentences that situate this chunk within the document above, to improve
search retrieval: name the document, the equipment and what the chunk covers. Reply with
the context only."""


@dataclass
class Chunk:
    id: str
    doc: str
    page: int
    kind: str
    text: str
    context: str = ""

    @property
    def indexed_text(self) -> str:
        return f"{self.context}\n\n{self.text}" if self.context else self.text


def chunk_elements(elements: list[Element]) -> list[Chunk]:
    chunks: list[Chunk] = []
    buffer: list[Element] = []

    def flush():
        if buffer:
            chunks.append(Chunk("", buffer[0].doc, buffer[0].page, "text",
                                "\n".join(e.text for e in buffer)))
            buffer.clear()

    for el in elements:
        if el.kind != "text":
            flush()
            chunks.append(Chunk("", el.doc, el.page, el.kind, el.text))
            continue
        if buffer and (buffer[0].doc != el.doc or buffer[0].page != el.page
                       or sum(len(e.text.split()) for e in buffer) + len(el.text.split()) > CHUNK_WORDS):
            flush()
        buffer.append(el)
    flush()

    for i, c in enumerate(chunks, 1):
        c.id = f"C{i:02d}"
    return chunks


def add_context(chunks: list[Chunk], elements: list[Element]) -> None:
    """Contextual retrieval: one cheap call per chunk, with the whole document as a cached prefix."""
    full_docs: dict[str, str] = {}
    for el in elements:
        full_docs.setdefault(el.doc, "")
        full_docs[el.doc] += el.text + "\n\n"

    for c in chunks:
        document = {
            "type": "text",
            "text": f"<document name=\"{c.doc}\">\n{full_docs[c.doc]}</document>",
            # Same document for every chunk, so it is cached after the first call
            # (below the model's minimum cacheable length it is simply not cached).
            "cache_control": {"type": "ephemeral"},
        }
        c.context = llm.text([document, {"type": "text", "text": CONTEXT_PROMPT.format(chunk=c.text)}],
                             effort="low", max_tokens=2000)  # room for thinking + 1-2 sentences


def to_dicts(chunks):
    return [asdict(c) for c in chunks]
