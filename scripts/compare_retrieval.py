#!/usr/bin/env python3
"""Compare retrieval reports only when labels and corpus hashes match."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare_reports(paths: list[Path]) -> dict:
    if len(paths) < 2:
        raise ValueError("Provide at least two reports")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    first = reports[0]
    for report in reports[1:]:
        if (
            report["dataset"]["sha256"] != first["dataset"]["sha256"]
            or report["corpus"]["sha256"] != first["corpus"]["sha256"]
        ):
            raise ValueError("Dataset and corpus SHA-256 hashes must match")
        if report["metrics"]["relevant_count"] != first["metrics"]["relevant_count"]:
            raise ValueError("Relevant query counts differ")
        if report["metrics"]["ood_count"] != first["metrics"]["ood_count"]:
            raise ValueError("Unsupported query counts differ")
    names = [report["metrics"]["name"] for report in reports]
    if len(set(names)) != len(names):
        raise ValueError("Strategy names must be unique")
    return {
        "dataset_sha256": first["dataset"]["sha256"],
        "corpus_sha256": first["corpus"]["sha256"],
        "strategies": [
            {
                "name": report["metrics"]["name"],
                "hit_at_1": report["metrics"]["hit_at_1"],
                "hit_at_3": report["metrics"]["hit_at_3"],
                "mrr": report["metrics"]["mrr"],
                "ood_false_accept_rate": report["metrics"]["ood_false_accept_rate"],
                "latency_p50_ms": report["metrics"]["latency_p50_ms"],
                "latency_p95_ms": report["metrics"]["latency_p95_ms"],
                "failures": [
                    {"id": row["id"], "type": row["failure_type"]}
                    for row in report["queries"]
                    if row.get("failure_type") and row.get("repeat", 0) == 0
                ],
            }
            for report in reports
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        comparison = compare_reports(args.reports)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(comparison, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
