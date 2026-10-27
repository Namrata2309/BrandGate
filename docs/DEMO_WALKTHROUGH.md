# BrandGate — 3-minute judge demo

Use the fictional Northstar Workspace brand only. Do not place confidential client material into the demo.

## Prepare before recording

1. Start FastAPI from `backend/` and Next.js from the active frontend application directory.
2. Run `python seed_demo.py` from `backend/` if the demo rules/facts are not in the database.
3. Confirm `/health`, `/docs`, and the review page load.
4. Confirm the LLM key is set in backend environment variables. If it is not available, state that the demo is using local checks only.
5. Keep a short known-good draft ready as a fallback.

## Demo script

**0:00–0:25 — Explain the problem**

Content teams need to publish quickly, but brand rules, approved prices and claims are stored separately. BrandGate checks content before publication and keeps human approval in control.

**0:25–0:50 — Show approved sources**

Open the guideline page and show `BG-002` (approved product name), `BG-003` (unsupported guaranteed outcomes) and `FACT-001` (₹999/month). Explain that these are fictional demonstration records.

**0:50–1:35 — Submit a flawed draft**

Use:

> Our Dashboard guarantees every business will double its sales. Get access for only ₹799 per month!

Show the local terminology and price findings. Explain that RAG retrieves the claims policy, and the LLM evaluates the contextual guarantee. Point out source IDs and verification state.

**1:35–2:15 — Correct the draft**

Edit the product name and price, and replace the guarantee with qualified language, for example:

> Northstar Workspace gives teams tools designed to support more effective sales workflows. Plans start at ₹999 per month.

Apply/edit a suggestion rather than accepting blindly. Save the revision and show that version 1 remains in history.

**2:15–2:40 — Human review**

Record a reviewer decision for the latest version. Show that a decision is tied to its version ID. If another revision is saved, the old approval does not approve the new version.

**2:40–3:00 — Explain evidence and limitations**

Show the basic issue summary, then explain that unsupported claims are marked for human verification, the product does not auto-publish, and semantic retrieval can fall back to keyword search if the local embedding model is unavailable.

## Demo integrity

- Do not claim unimplemented image/document support.
- Do not describe a mocked response as live AI output.
- If the provider fails, show local findings and label contextual AI analysis as unavailable/partial.
- Don't state an accuracy or time-saving percentage unless measured with recorded test data.
