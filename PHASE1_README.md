# BrandGate — Phase 1 starter files

This archive contains files to merge into an existing BrandGate project. It does not include a full Next.js scaffold or `node_modules`.

## 1. Merge the files

Extract the archive into your existing `brandgate/` folder and allow the included `frontend/app/page.tsx` and `frontend/app/guidelines/page.tsx` to be added/replaced. Keep your existing `frontend/app/layout.tsx`, `globals.css`, `package.json`, and other Next.js scaffold files.

## 2. Backend setup

From the `backend/` directory, activate your Python environment and install:

```bash
pip install -r requirements-phase1.txt
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Open `http://localhost:8000/health` and `http://localhost:8000/docs`.

## 3. Seed the fictional demo data

In a second terminal, from `backend/` with the same virtual environment active:

```bash
python seed_demo.py
```

The script adds rules and facts that do not already exist. It does not overwrite existing records.

## 4. Frontend setup

Copy `frontend/.env.local.example` to `frontend/.env.local` (if you do not already have this variable), then run the existing Next.js app:

```bash
npm run dev
```

Open `http://localhost:3000`, then select **Manage brand guidelines**. If your frontend runs on another port, add that exact origin to the CORS allowlist in `backend/app/main.py`.

## 5. Verify Phase 1

- `GET http://localhost:8000/health` returns a small JSON status response.
- `/docs` lists `/api/rules` and `/api/facts` endpoints.
- `GET http://localhost:8000/api/rules` returns the seeded active rules.
- `GET http://localhost:8000/api/facts` returns the seeded approved facts.
- The guidelines page lists rules and can create or deactivate a rule.

The review engine, RAG, LLM integration, authentication and approval flow are not included yet; they are subsequent phases. This starter uses `create_all` for MVP convenience; use database migrations before a larger production deployment.
