"""Read-only smoke checks for a local or deployed BrandGate backend.

Examples (from backend/):
  python scripts/smoke_test_deployment.py
  python scripts/smoke_test_deployment.py --base-url https://YOUR-BACKEND-HOST

This script does not call the hosted LLM or create reviews, so it does not consume
LLM credits or mutate review data. It checks health, rules, facts, retrieval and
workflow route availability.
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


def request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    url = base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=25) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, {"error": body[:500]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL without /api")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failures: list[str] = []

    def check(name: str, method: str, path: str, payload: dict[str, Any] | None = None, validate=None) -> Any:
        try:
            code, body = request_json(base, method, path, payload)
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            print(f"[FAIL] {name}: connection/response error ({type(exc).__name__})")
            failures.append(name)
            return None
        if code < 200 or code >= 300:
            print(f"[FAIL] {name}: HTTP {code}; response={body}")
            failures.append(name)
            return None
        if validate and not validate(body):
            print(f"[FAIL] {name}: unexpected response shape")
            failures.append(name)
            return body
        print(f"[PASS] {name}: HTTP {code}")
        return body

    health = check(
        "health", "GET", "/health",
        validate=lambda body: isinstance(body, dict) and body.get("status") == "ok",
    )
    rules = check("brand rules", "GET", "/api/rules", validate=lambda body: isinstance(body, list))
    facts = check("approved facts", "GET", "/api/facts", validate=lambda body: isinstance(body, list))
    check("retrieval status", "GET", "/api/retrieval/status", validate=lambda body: isinstance(body, dict))
    check("review workflow list", "GET", "/api/workflow/reviews", validate=lambda body: isinstance(body, list))
    retrieval_body = check(
        "keyword retrieval", "POST", "/api/retrieval/search",
        {"query": "guaranteed sales outcomes promotional claim", "top_k": 5, "include_facts": True, "use_semantic": False},
        validate=lambda body: isinstance(body, dict) and isinstance(body.get("results"), list),
    )

    if isinstance(rules, list) and not any(item.get("rule_code") == "BG-003" for item in rules if isinstance(item, dict)):
        print("[WARN] BG-003 not found in /api/rules. Seed the fictional demo data if expected.")
    if isinstance(facts, list) and not any(item.get("fact_code") == "FACT-001" for item in facts if isinstance(item, dict)):
        print("[WARN] FACT-001 not found in /api/facts. Seed the fictional demo data if expected.")
    if isinstance(retrieval_body, dict):
        ids = {item.get("source_id") for item in retrieval_body.get("results", []) if isinstance(item, dict)}
        if "BG-003" not in ids:
            print("[WARN] BG-003 was not in the top retrieval results; inspect seeded rules and retrieval ranking.")

    if failures:
        print(f"\nSmoke checks failed: {len(failures)}. Fix routes/configuration before the demo.")
        return 1
    print("\nAll route smoke checks passed. Warnings above are data/retrieval advisories, not HTTP failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
