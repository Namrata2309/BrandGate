"""Evaluate labelled local-check and retrieval cases against the seeded SQLite DB.

Usage from backend/:
  python scripts/run_labelled_eval.py
  python scripts/run_labelled_eval.py --semantic  # optional; may download the local embedding model

This script intentionally does not call a hosted LLM or spend API credits.
Contextual claim/tone findings should also be evaluated with the mocked API tests
and the live demo checklist.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from app import models  # noqa: F401,E402 - register SQLAlchemy tables
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import ApprovedFact, BrandRule  # noqa: E402
from app.services.local_checks import (  # noqa: E402
    check_fact_mismatches,
    check_terminology,
    load_terminology_config,
)
from app.services.retrieval import search_sources  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic", action="store_true",
        help="Try local semantic embeddings as well as keyword retrieval. The model may need downloading once.",
    )
    parser.add_argument(
        "--cases", type=Path,
        default=PROJECT_ROOT / "demo" / "labelled_test_cases.json",
        help="Path to the labelled JSON test case file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.cases.exists():
        print(f"ERROR: labelled test file not found: {args.cases}", file=sys.stderr)
        return 2

    payload = json.loads(args.cases.read_text(encoding="utf-8"))
    terms, term_config_warnings = load_terminology_config()
    today = date.today()
    Base.metadata.create_all(bind=engine)

    failures: list[str] = []
    total = len(payload.get("cases", []))
    print(f"BrandGate labelled evaluation | cases={total} | semantic={args.semantic}")
    if term_config_warnings:
        print("Terminology configuration warnings:", "; ".join(term_config_warnings))

    with SessionLocal() as db:
        rules = list(db.scalars(select(BrandRule)).all())
        facts = list(db.scalars(select(ApprovedFact)).all())
        if not rules:
            print("ERROR: no brand rules found. Run `python seed_demo.py` from backend/ first.", file=sys.stderr)
            return 2

        for case in payload.get("cases", []):
            term_findings, term_warnings = check_terminology(
                case["content"], rules=rules, terms=terms, today=today
            )
            fact_findings = check_fact_mismatches(
                case["content"], facts=facts, today=today
            )
            local_ids = {
                str(item.get("source_id"))
                for item in [*term_findings, *fact_findings]
                if item.get("source_id")
            }
            expected_local_ids = set(case.get("expected_local_source_ids", []))

            retrieval_result = search_sources(
                query=case.get("retrieval_query", case["content"]),
                rules=rules,
                facts=facts,
                top_k=int(payload.get("top_k", 5)),
                include_facts=True,
                use_semantic=args.semantic,
                today=today,
            )
            retrieved_ids = {str(item.get("source_id")) for item in retrieval_result.get("results", [])}
            expected_retrieved_ids = set(case.get("expected_retrieved_source_ids", []))

            local_ok = local_ids == expected_local_ids
            retrieval_missing = expected_retrieved_ids - retrieved_ids
            retrieval_ok = not retrieval_missing
            passed = local_ok and retrieval_ok
            marker = "PASS" if passed else "FAIL"
            print(f"\n[{marker}] {case['case_id']} — {case['title']}")
            print(f"  local IDs expected={sorted(expected_local_ids)} actual={sorted(local_ids)}")
            print(f"  retrieval={retrieval_result.get('retrieval_mode')} expected-present={sorted(expected_retrieved_ids)}")
            print(f"  retrieved top IDs={[item.get('source_id') for item in retrieval_result.get('results', [])]}")
            for warning in [*term_warnings, *retrieval_result.get("warnings", [])]:
                print(f"  warning: {warning}")
            if not local_ok:
                failures.append(f"{case['case_id']}: local IDs mismatch")
            if not retrieval_ok:
                failures.append(
                    f"{case['case_id']}: missing retrieved source IDs {sorted(retrieval_missing)}"
                )

    passed_count = total - len({failure.split(":")[0] for failure in failures})
    print(f"\nResult: {passed_count}/{total} cases passed.")
    if failures:
        for failure in failures:
            print(" -", failure)
        return 1
    print("Note: This evaluation checks deterministic local findings and retrieval only; it does not score live LLM findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
