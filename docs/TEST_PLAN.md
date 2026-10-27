# BrandGate quality and regression plan

## Test layers

1. **Unit tests:** terminology matching, approved price comparison, source freshness, keyword ranking and output validation.
2. **Regression tests:** inactive rules and expired facts must not be retrieved; semantic failures must report `keyword_fallback`; citations must retain source and section.
3. **Workflow integration tests:** create review, persist findings, create immutable revision, reject stale version operations, bind approval to the reviewed version and avoid duplicate local/AI finding cards.
4. **Labelled cases:** `demo/labelled_test_cases.json` records expected local source IDs and expected retrieval source IDs for a small deterministic set.
5. **Live smoke test:** check the deployed health route, rules/facts endpoints and workflow list; perform one review only when provider quota permits.

## Commands (run from backend/)

Install test dependencies:

```powershell
python -m pip install -r requirements-test.txt
```

Run all automated tests:

```powershell
python -m pytest tests -q
```

Run the read-only local API smoke check (start FastAPI first):

```powershell
python scripts/smoke_test_deployment.py
```

Run labelled checks without downloading or calling any model:

```powershell
python scripts/run_labelled_eval.py
```

Optional semantic retrieval evaluation (may download the local embedding model once):

```powershell
python scripts/run_labelled_eval.py --semantic
```

The labelled script does not make hosted LLM calls. LLM behaviour is covered by mocked regression tests; the judge demo separately demonstrates the live provider when configured.

## Reliability criteria

- Every shown source ID exists in the active retrieved source set.
- Inactive rules and expired facts are excluded.
- If embeddings fail, retrieval reports keyword fallback rather than claiming hybrid mode.
- If the LLM provider fails, the result is partial, not an implicit pass.
- A successful analysis is not an approval.
- Approval is bound to one content version; an edited version must be reviewed again.
- The database preserves prior versions and reviewer decisions.
- A revision request needs a human-readable comment.

## Record results honestly

Before final submission, record the actual commands, pass/fail counts, test-set size, provider/model used for the live demo, defects found and fixes made. Do not report a fabricated accuracy, precision, recall or time-saving number.
