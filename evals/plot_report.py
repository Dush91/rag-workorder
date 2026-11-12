"""Before/after chart for evals/REPORT.md, rendered for GitHub light and dark themes.

    uv run python evals/plot_report.py [runs_dir=runs_doubleword] [a=baseline] [b=v1]
"""
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

EVALS = Path(__file__).resolve().parent
RUNS = EVALS / (sys.argv[1] if len(sys.argv) > 1 else "runs_doubleword")
A, B = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("baseline", "v1")
METRICS = [("pass", "Pass"), ("rubric_score", "Rubric"), ("evidence_recall", "Evidence recall"),
           ("hard_facts", "Hard facts"), ("faithfulness", "Faithfulness")]
# Reference palette, categorical slots 1-2 (validated light and dark), plus text/surface tokens.
THEMES = {
    "light": dict(surface="#fcfcfb", text="#0b0b0b", muted="#52514e", grid="#e4e3df",
                  a="#2a78d6", b="#eb6834"),
    "dark": dict(surface="#1a1a19", text="#f0efec", muted="#c3c2b7", grid="#34332f",
                 a="#3987e5", b="#d95926"),
}


def per_case(variant):
    d = {}
    for line in (RUNS / variant / "results.jsonl").read_text().splitlines():
        r = json.loads(line)
        d.setdefault(r["prompt_id"], []).append(r)
    return d


def mean(xs):
    return sum(xs) / len(xs)


def paired(a, b, key, ids):
    ma = [mean([r["grade"][key] for r in a[i]]) for i in ids]
    mb = [mean([r["grade"][key] for r in b[i]]) for i in ids]
    diffs = [y - x for x, y in zip(ma, mb)]
    d = mean(diffs)
    sd = math.sqrt(sum((x - d) ** 2 for x in diffs) / (len(diffs) - 1))
    return mean(ma), mean(mb), d, 1.96 * sd / math.sqrt(len(diffs))


def draw(theme, out):
    t = THEMES[theme]
    a, b = per_case(A), per_case(B)
    ids = sorted(set(a) & set(b))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6.6), dpi=160,
                                   gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.95})
    fig.patch.set_facecolor(t["surface"])

    def dumbbell(ax, rows, title):
        ax.set_facecolor(t["surface"])
        for y, (label, va, vb, note) in enumerate(rows):
            ax.plot([va, vb], [y, y], color=t["muted"], lw=2, alpha=0.55, solid_capstyle="round", zorder=1)
            ax.scatter(va, y, s=150, marker="o", facecolor="none", edgecolor=t["a"], linewidth=2.2, zorder=3)
            ax.scatter(vb, y, s=55, marker="D", color=t["b"], edgecolor=t["surface"], linewidth=1.5, zorder=4)
            if note:
                ax.text(1.08, y, note, va="center", ha="left", color=t["text"], fontsize=9.5,
                        transform=ax.get_yaxis_transform())
        ax.set_yticks(range(len(rows)), [r[0] for r in rows], color=t["text"])
        ax.invert_yaxis()
        ax.set_xlim(-0.03, 1.03)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0", ".25", ".50", ".75", "1.0"], color=t["muted"])
        ax.grid(axis="x", color=t["grid"], lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(title, loc="left", color=t["text"], fontsize=12, fontweight="bold", pad=12)

    rows = []
    for key, label in METRICS:
        va, vb, d, ci = paired(a, b, key, ids)
        rows.append((label, va, vb, f"{d:+.2f} ±{ci:.2f}"))
    dumbbell(ax1, rows, "Mean over 16 cases × 3 reps")
    ax1.text(1.08, -0.7, "Δ  (95% CI)", ha="left", color=t["muted"], fontsize=9.5)

    case_rows = []
    for i in ids:
        pa, pb = mean([r["grade"]["pass"] for r in a[i]]), mean([r["grade"]["pass"] for r in b[i]])
        case_rows.append((i.split("_", 1)[0] + " " + i.split("_", 1)[1].replace("_", " ")[:22], pa, pb, ""))
    dumbbell(ax2, case_rows, "Pass rate per case (share of 3 runs)")

    handles = [plt.Line2D([], [], ls="", marker="o", ms=10, mfc="none", mec=t["a"], mew=2.2, label=f"{A} (pre-fix)"),
               plt.Line2D([], [], ls="", marker="D", ms=7, color=t["b"], label=f"{B} (rank-merge + site-aware queries)")]
    leg = fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.45, 0.0), ncol=2, frameon=False,
                     fontsize=10)
    for txt in leg.get_texts():
        txt.set_color(t["text"])
    fig.text(0.02, 0.025, "App: Kimi K3.1 Pro · Judge: GLM 5.3 · paired over the same 16 cases",
             color=t["muted"], fontsize=9)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.13)
    fig.savefig(out, facecolor=t["surface"])
    print("wrote", out)


if __name__ == "__main__":
    for theme in THEMES:
        draw(theme, EVALS / "results" / f"before_after_{theme}.png")
