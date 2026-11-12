"""End-to-end eval: run the real pipeline (rag.workorder.solve) on every case, grade, summarise.

    uv run python evals/run_eval.py --reps 3                 # full run -> evals/runs/baseline/
    uv run python evals/run_eval.py --cases c01_original --reps 1   # pilot
    uv run python evals/run_eval.py --summary-only           # re-summarise existing rows
    uv run python evals/run_eval.py --variant v1 --reps 3    # after changing the app
    uv run python evals/run_eval.py --compare baseline v1    # paired before/after

Output per variant (resumable at the (case, rep) key):
  evals/runs/<variant>/results.jsonl    one graded row per (case, rep)
  evals/runs/<variant>/traces/*.json    full pipeline transcript per (case, rep)
  evals/runs/<variant>/errors.jsonl     attempts that produced nothing scorable (never scored as 0)
  evals/results/e2e_summary.md          headline table with 95% CIs, pass^k, cost, latency
"""
import argparse
import json
import math
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag import llm  # noqa: E402
from rag.config import MODEL  # noqa: E402
from rag.retrieval import Retriever  # noqa: E402
from rag.workorder import PLAN_SYSTEM, solve  # noqa: E402

import graders  # noqa: E402

EVALS = Path(__file__).resolve().parent
RUNS = EVALS / "runs"
# $/MTok (input, output, cache read). Claude: first-party rates, cache write 1.25x input.
# Doubleword: realtime tier list prices, Nov 2026.
PRICES = {"claude-opus-5-5": (4.0, 20.0, 0.40), "claude-sonnet-5-5": (2.0, 10.0, 0.20),
          "claude-haiku-5-5": (0.10, 0.50, 0.01),
          "deepseek-ai/DeepSeek-V4-Pro-0813": (1.32, 3.96, 0.13), "zai-org/GLM-5.3": (1.40, 4.40, 0.28),
          "moonshotai/Kimi-K3.1-Pro": (2.00, 10.00, 0.20)}
METRICS = [  # order matters: first binary metric is the headline
    ("pass", "Pass", "binary", "hard facts all correct AND every rubric criterion met"),
    ("hard_facts", "Hard facts", "binary", "priority, stop, parts, torque, open question, citations valid"),
    ("rubric_score", "Rubric", "continuous", "share of case rubric criteria met (LLM judge)"),
    ("faithfulness", "Faithfulness", "continuous", "work-order items supported by the chunks they cite"),
    ("evidence_recall", "Evid. recall", "continuous", "gold evidence chunks that reached the planner"),
    ("citations_ok", "Citations", "binary", "every cited ID was supplied and every item cites something"),
]


class LockedRetriever:
    """Retrieval is fast and local; serialise it so ONNX sessions are never shared across threads."""

    def __init__(self):
        self._r, self._lock = Retriever(), threading.Lock()
        self.chunks = self._r.chunks

    def search(self, query, k):
        with self._lock:
            return self._r.search(query, k)


def cost(model, usage):
    pin, pout, pread = PRICES[model]
    return (usage["input_tokens"] * pin + usage["output_tokens"] * pout
            + usage["cache_creation_input_tokens"] * pin * 1.25
            + usage["cache_read_input_tokens"] * pread) / 1e6


def sum_usage(calls):
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    return {k: sum(c["usage"][k] for c in calls) for k in keys}


def resolve_gold(case, chunks):
    ids = []
    for s in case["gold"]:
        hit = [c.id for c in chunks if s in c.text]
        assert len(hit) == 1, f"{case['id']}: gold {s!r} matched {hit}"
        ids.append(hit[0])
    return ids


def run_one(case, rep, retriever, out):
    """Returns ('ok', row) or ('error', error_row). Never raises."""
    t0 = time.time()
    app_calls = llm.start_recording()
    try:
        result = solve(case["report"], retriever)
    except Exception as e:  # noqa: BLE001 - classify, record, move on
        msg = str(e)
        cls = ("refusal" if "declined" in msg else "truncated" if "max_tokens" in msg
               else "api_error" if isinstance(e, anthropic.APIError) else "harness_error")
        return "error", {"prompt_id": case["id"], "rep": rep, "stage": "app", "failure_class": cls,
                         "error": msg[:500], "calls": list(app_calls), "traceback": traceback.format_exc()[-1500:]}
    app_calls = list(app_calls)
    app_latency = round(time.time() - t0, 1)

    served = {c["model"] for c in app_calls}
    if served != {MODEL}:
        return "error", {"prompt_id": case["id"], "rep": rep, "stage": "app",
                         "failure_class": "served_model_mismatch", "error": f"served {served}",
                         "calls": app_calls}

    order, evidence = result["work_order"], result["evidence"]
    evidence_ids = {c.id for c in evidence}
    gold_ids = resolve_gold(case, retriever.chunks)
    prog = graders.programmatic(order, case["expect"], result["citation_check"], evidence_ids, gold_ids)

    judge_calls = llm.start_recording()
    try:
        j = graders.judge(case["report"], order, case["rubric"], {c.id: c.text for c in evidence})
    except Exception as e:  # noqa: BLE001
        return "error", {"prompt_id": case["id"], "rep": rep, "stage": "judge",
                         "failure_class": "grader_error", "error": str(e)[:500],
                         "calls": app_calls + list(judge_calls)}
    judge_calls = list(judge_calls)

    p = prog["grade"]
    hard = [v for k, v in p.items() if k != "evidence_recall"]
    grade = {
        "hard_facts": float(all(v == 1.0 for v in hard)),
        "rubric_score": j["rubric"]["rubric_score"],
        "faithfulness": j["faithfulness"]["faithfulness"],
        "evidence_recall": p["evidence_recall"],
        "citations_ok": p["citations_ok"],
    }
    grade["pass"] = float(grade["hard_facts"] == 1.0 and j["rubric"]["rubric_all"] == 1.0)
    grade = {k: grade[k] for k, *_ in METRICS}

    trace = [
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": case["report"]},
        {"role": "tool_call", "name": "decompose", "content": json.dumps(result["plan"].model_dump(), indent=2)},
        {"role": "tool_result", "content": json.dumps(result["hits_per_query"], indent=2)},
        {"role": "tool_call", "name": "evidence_given_to_planner", "content": json.dumps(sorted(evidence_ids))},
        {"role": "tool_result", "content": "\n\n".join(f"[{c.id}] {c.doc} p{c.page} ({c.kind})\n{c.text}"
                                                      for c in evidence)},
        {"role": "assistant", "content": order.model_dump_json(indent=2)},
    ]
    (out / "traces" / f"{case['id']}_rep{rep}.json").write_text(json.dumps(trace, indent=1))

    return "ok", {
        "prompt_id": case["id"], "rep": rep, "prompt": case["report"], "tags": case["tags"],
        "status": "ok", "stop_reason": app_calls[-1]["stop_reason"],
        "grade": grade,
        "explanation": {**prog["explanation"],
                        "rubric": json.dumps(j["rubric"]["detail"]),
                        "faithfulness": json.dumps(j["faithfulness"]["unsupported"])},
        "model": MODEL, "usage": sum_usage(app_calls), "latency_s": app_latency,
        "llm_calls": len(app_calls),
        "judge_model": graders.JUDGE_MODEL, "judge_usage": sum_usage(judge_calls),
        "meta": {"checks": p, "priority": order.priority, "stop": order.stop_equipment_now,
                 "parts": [x.part_number for x in order.parts]},
    }


# ---------- summary ----------

def mean_ci(per_case):
    """Mean over cases (each case = mean of its reps) with a normal-approx 95% CI."""
    n = len(per_case)
    m = sum(per_case) / n
    if n < 2:
        return m, float("nan")
    sd = math.sqrt(sum((x - m) ** 2 for x in per_case) / (n - 1))
    return m, 1.96 * sd / math.sqrt(n)


def summarise(variant):
    out = RUNS / variant
    rows = [json.loads(line) for line in (out / "results.jsonl").read_text().splitlines() if line.strip()]
    errs_path = out / "errors.jsonl"
    errors = [json.loads(line) for line in errs_path.read_text().splitlines()] if errs_path.exists() else []
    by_case = {}
    for r in rows:
        by_case.setdefault(r["prompt_id"], []).append(r)
    reps = max(len(v) for v in by_case.values())

    lines = [f"# End-to-end eval: `{variant}`", "",
             f"{len(by_case)} cases x up to {reps} reps = {len(rows)} graded runs; "
             f"{len(errors)} failed attempts (not scored). App model `{MODEL}`, judge `{graders.JUDGE_MODEL}`.", "",
             "| Metric | Mean | 95% CI | What it measures |", "|---|---|---|---|"]
    for key, label, _, desc in METRICS:
        m, ci = mean_ci([sum(r["grade"][key] for r in v) / len(v) for v in by_case.values()])
        lines.append(f"| {label} | {m:.2f} | ±{ci:.2f} | {desc} |")
    full = [v for v in by_case.values() if len(v) == reps]
    if reps > 1 and full:
        pk = sum(all(r["grade"]["pass"] == 1.0 for r in v) for v in full) / len(full)
        p_any = sum(any(r["grade"]["pass"] == 1.0 for r in v) for v in full) / len(full)
        lines += ["", f"**Consistency:** pass^{reps} = **{pk:.2f}** (passes on all {reps} runs), "
                      f"pass@{reps} = {p_any:.2f} (passes on at least one run)."]

    app_cost = [cost(r["model"], r["usage"]) for r in rows]
    judge_cost = [cost(r["judge_model"], r["judge_usage"]) for r in rows]
    lat = sorted(r["latency_s"] for r in rows)
    lines += ["", f"**Cost (measured from `usage`):** app ${sum(app_cost) / len(rows):.3f}/run, "
                  f"judge ${sum(judge_cost) / len(rows):.3f}/run, total ${sum(app_cost) + sum(judge_cost):.2f} "
                  f"for this run. **Latency:** median {lat[len(lat) // 2]:.0f}s, max {lat[-1]:.0f}s per work order."]

    lines += ["", "## Per case", "",
              "| Case | Tag | Pass | Hard facts | Rubric | Faithful | Failing checks (any rep) |",
              "|---|---|---|---|---|---|---|"]
    for cid, v in by_case.items():
        avg = lambda k: sum(r["grade"][k] for r in v) / len(v)  # noqa: E731
        fails = sorted({k for r in v for k, x in r["meta"]["checks"].items()
                        if k != "evidence_recall" and x < 1.0})
        missed = sorted({d["criterion"][:60] for r in v for d in json.loads(r["explanation"]["rubric"])
                         if not d["met"]})
        detail = ", ".join(fails + [f'rubric: "{m}…"' for m in missed]) or "—"
        lines.append(f"| `{cid}` | {v[0]['tags'][0]} | {avg('pass'):.2f} | {avg('hard_facts'):.2f} | "
                     f"{avg('rubric_score'):.2f} | {avg('faithfulness'):.2f} | {detail} |")
    if errors:
        lines += ["", "## Failed attempts", ""] + [f"- `{e['prompt_id']}` rep {e['rep']}: "
                                                   f"{e['failure_class']} ({e['error'][:120]})" for e in errors]
    (EVALS / "results").mkdir(exist_ok=True)
    tag = "" if RUNS.name == "runs" else RUNS.name.removeprefix("runs_") + "_"
    (EVALS / "results" / f"e2e_summary_{tag}{variant}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def compare(a, b):
    """Paired per-case comparison of two variants (same cases), with a 95% CI on the difference."""
    def per_case(v):
        rows = [json.loads(x) for x in (RUNS / v / "results.jsonl").read_text().splitlines() if x.strip()]
        d = {}
        for r in rows:
            d.setdefault(r["prompt_id"], []).append(r)
        return d
    A, B = per_case(a), per_case(b)
    ids = sorted(set(A) & set(B))
    lines = [f"# `{a}` vs `{b}` (paired over {len(ids)} cases)", "",
             f"| Metric | {a} | {b} | Δ | 95% CI of Δ |", "|---|---|---|---|---|"]
    for key, label, *_ in METRICS:
        ma = [sum(r["grade"][key] for r in A[i]) / len(A[i]) for i in ids]
        mb = [sum(r["grade"][key] for r in B[i]) / len(B[i]) for i in ids]
        d, ci = mean_ci([y - x for x, y in zip(ma, mb)])
        lines.append(f"| {label} | {sum(ma) / len(ids):.2f} | {sum(mb) / len(ids):.2f} | {d:+.2f} | ±{ci:.2f} |")
    k = max(len(x) for D in (A, B) for x in D.values())
    both = [i for i in ids if len(A[i]) == k and len(B[i]) == k]
    for v, D in ((a, A), (b, B)):
        pk = sum(all(r["grade"]["pass"] == 1 for r in D[i]) for i in both) / len(both)
        lines.append(f"\n`{v}` pass^{k} = **{pk:.2f}** (over the {len(both)} cases with all {k} reps in both variants)")
    lines += ["", "| Case | " + a + " pass | " + b + " pass |", "|---|---|---|"]
    for i in ids:
        pa = sum(r["grade"]["pass"] for r in A[i]) / len(A[i])
        pb = sum(r["grade"]["pass"] for r in B[i]) / len(B[i])
        lines.append(f"| `{i}` | {pa:.2f} | {pb:.2f}{' ⬆' if pb > pa else ' ⬇' if pb < pa else ''} |")
    tag = "" if RUNS.name == "runs" else RUNS.name.removeprefix("runs_") + "_"
    (EVALS / "results" / f"compare_{tag}{a}_vs_{b}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def regrade(variant):
    """Recompute programmatic grades from saved traces after a grader/case fix (no API calls).
    Judge verdicts are kept; app outputs are untouched."""
    from rag.workorder import WorkOrder, check_citations
    out = RUNS / variant
    cases = {c["id"]: c for c in json.loads((EVALS / "cases.json").read_text())["cases"]}
    chunks = LockedRetriever().chunks
    rows = [json.loads(line) for line in (out / "results.jsonl").read_text().splitlines() if line.strip()]
    for r in rows:
        trace = json.loads((out / "traces" / f"{r['prompt_id']}_rep{r['rep']}.json").read_text())
        order = WorkOrder.model_validate_json(trace[-1]["content"])
        evidence_ids = set(json.loads(trace[4]["content"]))
        case = cases[r["prompt_id"]]
        prog = graders.programmatic(order, case["expect"], check_citations(order, evidence_ids),
                                    evidence_ids, resolve_gold(case, chunks))
        p = prog["grade"]
        r["grade"]["hard_facts"] = float(all(v == 1.0 for k, v in p.items() if k != "evidence_recall"))
        r["grade"]["citations_ok"], r["grade"]["evidence_recall"] = p["citations_ok"], p["evidence_recall"]
        rubric_all = all(d["met"] for d in json.loads(r["explanation"]["rubric"]))
        r["grade"]["pass"] = float(r["grade"]["hard_facts"] == 1.0 and rubric_all)
        r["explanation"].update(prog["explanation"])
        r["meta"]["checks"] = p
    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"regraded {len(rows)} rows in {variant}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="baseline")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--cases", nargs="*", help="case ids (default: all)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--runs-dir", default="runs", help="under evals/; e.g. runs_doubleword")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--regrade", action="store_true", help="recompute programmatic grades from traces")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"), help="paired comparison of two variants")
    args = ap.parse_args()
    global RUNS
    RUNS = EVALS / args.runs_dir

    if args.compare:
        return compare(*args.compare)
    if args.regrade:
        regrade(args.variant)
    elif not args.summary_only:
        out = RUNS / args.variant
        (out / "traces").mkdir(parents=True, exist_ok=True)
        (RUNS / "_state.json").write_text(json.dumps({"metrics": [
            {"id": k, "label": lab, "kind": kind, "description": d} for k, lab, kind, d in METRICS]}, indent=2))
        llm._client = anthropic.Anthropic(timeout=600, max_retries=4)  # per-call ceiling + jittered retries

        cases = json.loads((EVALS / "cases.json").read_text())["cases"]
        if args.cases:
            cases = [c for c in cases if c["id"] in args.cases]
        res_path = out / "results.jsonl"
        done = set()
        if res_path.exists():
            done = {(r["prompt_id"], r["rep"]) for r in map(json.loads, res_path.read_text().splitlines())}
        todo = [(c, k) for c in cases for k in range(args.reps) if (c["id"], k) not in done]
        print(f"{len(todo)} runs to do ({len(done)} already done)", flush=True)

        retriever, write_lock = LockedRetriever(), threading.Lock()
        with ThreadPoolExecutor(args.workers) as pool:
            futures = {pool.submit(run_one, c, k, retriever, out): (c["id"], k) for c, k in todo}
            for f in as_completed(futures):
                kind, row = f.result()
                with write_lock:
                    with open(out / ("results.jsonl" if kind == "ok" else "errors.jsonl"), "a") as fh:
                        fh.write(json.dumps(row) + "\n")
                cid, k = futures[f]
                msg = (f"pass={row['grade']['pass']:.0f} rubric={row['grade']['rubric_score']:.2f} "
                       f"faith={row['grade']['faithfulness']:.2f} {row['latency_s']}s" if kind == "ok"
                       else f"ERROR {row['failure_class']}: {row['error'][:100]}")
                print(f"{cid} rep{k}: {msg}", flush=True)
    summarise(args.variant)


if __name__ == "__main__":
    main()
