"""Layout-aware PDF parsing that routes each part of a page to the cheapest reader that works.

- Digital text      -> PyMuPDF text blocks (free, exact)
- Ruled tables      -> PyMuPDF table detection, kept whole as Markdown tables
- Figures / charts  -> cropped and transcribed by Claude vision (values that exist only in pixels)
- Scanned pages     -> whole page transcribed by Claude vision (no text layer at all)

Elements come back in reading order, with captions attached to the table or figure they describe.
"""
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

from . import llm

CAPTION = re.compile(r"^(Figure|Table)\s+\d", re.IGNORECASE)

FIGURE_PROMPT = """This image was cropped from page {page} of "{doc}".
Transcribe it for a search index. Say what it shows, then list every label, callout number,
axis value, threshold and range as explicit text (for example "Zone C: 4.5 to 7.1 mm/s").
Do not add information that is not in the image. Output Markdown only."""

SCAN_PROMPT = """This is a scanned page from "{doc}". Transcribe it to Markdown exactly:
keep headings, numbered lists and tables (as Markdown tables). Do not summarise or add anything."""


@dataclass
class Element:
    doc: str
    page: int
    kind: str  # text | table | figure | scanned_page
    text: str
    y: float = 0.0  # top of the element on the page, for reading order


def _cell_text(words, cell) -> str:
    """Words whose centre lies inside the cell. table.extract() can drop spaces between
    words, and a plain text-box clip picks up text that only grazes the cell edge."""
    if not cell:
        return ""
    r = pymupdf.Rect(cell)
    return " ".join(w[4] for w in words
                    if r.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))


def table_to_markdown(page, table) -> str:
    words = page.get_text("words", sort=True)
    rows = [[_cell_text(words, cell) for cell in row.cells] for row in table.rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _inside(rect, boxes) -> bool:
    """True if the block's centre is inside a table or figure (so it is already covered)."""
    r = pymupdf.Rect(rect)
    centre = pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    return any(b.contains(centre) for b in boxes)


def _attach_captions(elements: list[Element]) -> list[Element]:
    """Merge 'Figure 2 - ...' / 'Table 5 - ...' text into the nearest table or figure."""
    out = []
    for i, el in enumerate(elements):
        if el.kind == "text" and CAPTION.match(el.text):
            neighbours = [j for j in (i - 1, i + 1)
                          if 0 <= j < len(elements) and elements[j].kind in ("table", "figure")]
            if neighbours:
                wanted = CAPTION.match(el.text).group(1).lower()  # "figure" or "table"
                target = min(neighbours, key=lambda j: (elements[j].kind != wanted,
                                                        abs(elements[j].y - el.y)))
                elements[target].text = f"{el.text}\n\n{elements[target].text}"
                continue
        out.append(el)
    return out


def parse_page(page, doc_name: str) -> list[Element]:
    pno = page.number + 1

    if not page.get_text().strip():  # no text layer: treat as a scan
        png = page.get_pixmap(dpi=150).tobytes("png")
        md = llm.text([llm.image_block(png), {"type": "text", "text": SCAN_PROMPT.format(doc=doc_name)}],
                      effort="medium")
        return [Element(doc_name, pno, "scanned_page", md)]

    elements, skip_boxes = [], []

    for t in page.find_tables().tables:
        elements.append(Element(doc_name, pno, "table", table_to_markdown(page, t), t.bbox[1]))
        skip_boxes.append(pymupdf.Rect(t.bbox))

    for img in page.get_images(full=True):
        for rect in page.get_image_rects(img[0]):
            png = page.get_pixmap(clip=rect, dpi=150).tobytes("png")
            md = llm.text([llm.image_block(png),
                           {"type": "text", "text": FIGURE_PROMPT.format(page=pno, doc=doc_name)}],
                          effort="medium")
            elements.append(Element(doc_name, pno, "figure", md, rect.y0))
            skip_boxes.append(rect)

    for x0, y0, x1, y1, txt, *_ in page.get_text("blocks"):
        if txt.strip() and not _inside((x0, y0, x1, y1), skip_boxes):
            elements.append(Element(doc_name, pno, "text", " ".join(txt.split()), y0))

    elements.sort(key=lambda e: e.y)
    return _attach_captions(elements)


def parse_pdf(path: Path) -> list[Element]:
    with pymupdf.open(path) as pdf:
        return [el for page in pdf for el in parse_page(page, path.name)]


def to_dicts(elements):
    return [asdict(e) for e in elements]
