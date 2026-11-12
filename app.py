"""Streamlit front end.  uv run streamlit run app.py"""
import json

import streamlit as st

from rag.config import DATA_DIR
from rag.retrieval import Retriever
from rag.workorder import solve
from solve import SAMPLE_REPORT

st.set_page_config(page_title="Fault to Work Order", layout="wide")
st.title("Fault report → work order")
st.caption("Hybrid parsing · contextual retrieval · BM25 + dense + rerank · cited, checked output")


@st.cache_resource
def retriever():
    return Retriever()


def cites(ids):
    return " ".join(f"`{i}`" for i in ids)


solve_tab, corpus_tab = st.tabs(["Solve a fault", "What the parser extracted"])

with solve_tab:
    report = st.text_area("Technician's fault report", SAMPLE_REPORT, height=120)
    if st.button("Plan the repair", type="primary"):
        with st.spinner("Decomposing, retrieving and planning..."):
            st.session_state.result = solve(report, retriever())

    result = st.session_state.get("result")
    if result:
        wo = result["work_order"]
        check = result["citation_check"]

        a, b, c = st.columns(3)
        a.metric("Priority", wo.priority)
        b.metric("Stop equipment now", "YES" if wo.stop_equipment_now else "no")
        c.metric("Citations valid", "✅" if check["ok"] else "❌",
                 help=f"{check['items']} items; unknown IDs {check['unknown_ids']}; "
                      f"uncited {check['uncited_items']}")
        st.subheader(wo.asset)

        for title, items in [("Condition assessment", wo.condition_assessment),
                             ("Probable causes", wo.probable_causes),
                             ("Tasks", wo.tasks),
                             ("Safety controls", wo.safety_controls),
                             ("Labour", wo.labour),
                             ("Source conflicts resolved", wo.source_conflicts)]:
            if items:
                st.markdown(f"**{title}**")
                for it in items:
                    st.markdown(f"- {it.statement} {cites(it.citations)}")

        st.markdown("**Parts**")
        st.table([{"Part": p.part_number, "Description": p.description, "Qty": p.quantity,
                   "Source": ", ".join(p.citations)} for p in wo.parts])
        if wo.open_questions:
            st.markdown("**Open questions**")
            for q in wo.open_questions:
                st.markdown(f"- {q}")

        with st.expander("Step 1 · Sub-queries and what each retrieved"):
            for q, hits in result["hits_per_query"].items():
                st.markdown(f"- {q}  \n  {', '.join(f'{i} ({s})' for i, s in hits)}")
        with st.expander("Step 2 · Evidence given to Claude"):
            for ch in result["evidence"]:
                st.markdown(f"**{ch.id}** · {ch.doc} · page {ch.page} · {ch.kind}")
                st.caption(ch.context)
                st.markdown(ch.text)
                st.divider()

with corpus_tab:
    path = DATA_DIR / "chunks.json"
    if not path.exists():
        st.info("Run `uv run python ingest.py` first.")
    else:
        chunks = json.loads(path.read_text())
        kind = st.radio("Show", ["figure", "scanned_page", "table", "text"], horizontal=True)
        for ch in (c for c in chunks if c["kind"] == kind):
            st.markdown(f"**{ch['id']}** · {ch['doc']} · page {ch['page']}")
            st.caption(f"Context: {ch['context']}")
            st.markdown(ch["text"])
            st.divider()
