"""Command-line run of the fault-to-work-order pipeline.

    uv run python solve.py                 # uses the sample fault report
    uv run python solve.py "your report"   # or pass your own
"""
import json
import sys

from rag.retrieval import Retriever
from rag.workorder import solve

SAMPLE_REPORT = (
    "Pump P-104 (AquaDyne HF-300, serial HF3-22871) on the filtered-water line. Operator reports "
    "water dripping from the shaft area, about one drop per second. Vibration 7.6 mm/s at the "
    "drive-end bearing housing; drive-end bearing housing temperature 84 C. The pump ran dry for "
    "about 10 minutes last week during a tank changeover."
)


def main():
    report = sys.argv[1] if len(sys.argv) > 1 else SAMPLE_REPORT
    result = solve(report, Retriever())

    print("Sub-queries and the chunks each one retrieved:")
    for q, hits in result["hits_per_query"].items():
        print(f"  - {q}\n      {hits}")
    print("\nWork order:")
    print(json.dumps(result["work_order"].model_dump(), indent=2))
    print("\nCitation check:", result["citation_check"])


if __name__ == "__main__":
    main()
