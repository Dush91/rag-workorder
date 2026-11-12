"""Turn a technician's fault report into a cited, checkable work order.

1. Decompose  - Claude splits the report into the separate questions a planner would look up
                (vibration limits, likely causes, parts, torques, safety rules, labour...).
2. Retrieve   - each question runs through hybrid search + rerank; results are merged.
3. Plan       - Claude writes a structured work order where every item cites chunk IDs.
4. Verify     - code checks every citation points at evidence Claude was actually given.
"""
from typing import Literal

from pydantic import BaseModel, Field

from . import llm
from .config import MAX_EVIDENCE, TOP_K_PER_QUERY
from .retrieval import Retriever


class SearchPlan(BaseModel):
    asset: str = Field(description="Equipment model, tag and serial number if given")
    queries: list[str] = Field(description="4 to 8 standalone search queries")


class Item(BaseModel):
    statement: str
    citations: list[str] = Field(description="Chunk IDs, e.g. ['C04']")


class Part(BaseModel):
    part_number: str
    description: str
    quantity: int
    citations: list[str]


class WorkOrder(BaseModel):
    asset: str
    priority: Literal["P1", "P2", "P3"]
    stop_equipment_now: bool
    condition_assessment: list[Item] = Field(description="Each reading compared with its limit")
    probable_causes: list[Item] = Field(description="Most likely first")
    tasks: list[Item] = Field(description="Ordered steps, with torque values where relevant")
    parts: list[Part]
    safety_controls: list[Item]
    labour: list[Item]
    source_conflicts: list[Item] = Field(
        description="Where documents disagree, which one applies to this asset and why")
    open_questions: list[str] = Field(description="What the evidence cannot answer")


DECOMPOSE = """You are a maintenance planner. Read this fault report and list the separate
things you would need to look up in the equipment manuals, service bulletins and site safety
procedures to plan the repair. Write each as a standalone search query.

Cover, where relevant: the documented limit for each reading in the report; probable causes;
the repair procedure; part numbers (and any serial-number-dependent changes); tightening
torques; labour; and the site's safety requirements for this work and this asset tag.
Queries about the equipment should name the equipment model. Queries about site rules
(isolation, permits, lifting, PPE, escalation) should be phrased as questions about the site
safety procedure and the asset tag, not about the equipment model.

<fault_report>
{report}
</fault_report>"""

PLAN_SYSTEM = """You are a maintenance planner writing a work order for a field technician.
Use only the evidence chunks provided; cite the chunk IDs that support every item.
Compare each reading in the report with its documented limit and say which limit applies.
Where documents disagree, work out which one applies to this specific asset (check serial
ranges and dates) and record the decision under source_conflicts.
If the evidence does not cover something, put it in open_questions instead of guessing."""


def gather_evidence(retriever: Retriever, queries: list[str]):
    """Merge sub-query results by RANK, round-robin, not by raw reranker score.

    Cross-encoder scores are not comparable across different queries: a site-safety query
    scores lower in absolute terms than a query that matches manual tables almost verbatim,
    so a global sort by score let manual chunks crowd the site procedure out of the evidence
    (found by the eval: evidence_recall + missing safety controls). Taking each query's #1,
    then each query's #2, ... guarantees every sub-query's best hit a slot."""
    hits_per_query, ranked_lists = {}, []
    for q in queries:
        hits = retriever.search(q, TOP_K_PER_QUERY)
        hits_per_query[q] = [(c.id, round(s, 2)) for c, s in hits]
        ranked_lists.append([c for c, _ in hits])
    evidence, seen = [], set()
    for rank in range(TOP_K_PER_QUERY):
        for hits in ranked_lists:
            if rank < len(hits) and hits[rank].id not in seen and len(evidence) < MAX_EVIDENCE:
                evidence.append(hits[rank])
                seen.add(hits[rank].id)
    return evidence, hits_per_query


def format_evidence(chunks) -> str:
    return "\n\n".join(
        f'<chunk id="{c.id}" source="{c.doc}" page="{c.page}" type="{c.kind}">\n{c.text}\n</chunk>'
        for c in chunks)


def check_citations(order: WorkOrder, evidence_ids: set[str]) -> dict:
    """Every cited ID must be one we supplied, and every item must cite something."""
    items = (order.condition_assessment + order.probable_causes + order.tasks
             + order.safety_controls + order.labour + order.source_conflicts + order.parts)
    unknown = sorted({cid for it in items for cid in it.citations if cid not in evidence_ids})
    uncited = [getattr(it, "statement", None) or it.part_number for it in items if not it.citations]
    return {"items": len(items), "unknown_ids": unknown, "uncited_items": uncited,
            "ok": not unknown and not uncited}


def solve(report: str, retriever: Retriever) -> dict:
    plan = llm.structured(DECOMPOSE.format(report=report), SearchPlan, effort="low")
    evidence, hits_per_query = gather_evidence(retriever, plan.queries)
    order = llm.structured(
        f"<fault_report>\n{report}\n</fault_report>\n\n<evidence>\n{format_evidence(evidence)}\n</evidence>",
        WorkOrder, system=PLAN_SYSTEM, effort="high")
    return {
        "plan": plan,
        "hits_per_query": hits_per_query,
        "evidence": evidence,
        "work_order": order,
        "citation_check": check_citations(order, {c.id for c in evidence}),
    }
