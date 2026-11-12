# v1: evidence assembly — rank-merge sub-queries + coverage-aware decomposition

Baseline failures clustered on one thing: work orders missing site safety controls (LOTO,
line-break permit, signed lifting plan, goggles/gloves, notify reliability engineer). Traces
showed why: chunk C15 (the site procedure's controls table) never reached the planner.

Two root causes, both in `rag/workorder.py`:

1. **Merge by score.** `gather_evidence` sorted all sub-query hits by raw cross-encoder score
   and kept the top 14. Cross-encoder scores are not comparable across queries, so manual
   chunks matching their query near-verbatim crowded out the site procedure.
   Fix: round-robin merge by rank (every sub-query's #1, then every #2, ...).
2. **Every query forced to name the equipment model.** The decomposition prompt said each
   query "includes the equipment model", so the safety query became "AquaDyne HF-300 pump
   lockout/tagout ..." and matched manual text. Phrased as a site question, C15 ranks #1 by
   a wide margin (6.2 vs -1.6). Fix: site-rule queries are phrased about the site procedure
   and asset tag, and the prompt lists the facets a planner must cover (limits, causes,
   procedure, parts incl. serial changes, torques, labour, site safety).
