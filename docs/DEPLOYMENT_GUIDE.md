# BrandGate deployment guide (optional for Round 2)

Use this after the local test suite and workflow pass. A deployed link is useful for judges, but do not deploy a knowingly broken build just to have a URL.

## Recommended simple split

- **Frontend:** Vercel, with the Next.js app's directory set as the project root.
- **Backend:** Render Web Service running FastAPI from the `backend/` directory.
- **Database:** persistent storage. SQLite is suitable locally; on a host with ephemeral files, a local SQLite file may be lost during a restart/redeploy. Use a supported persistent disk or move to managed PostgreSQL and add the appropriate database driver/configuration.

Official references:
- Render Web Services: https://render.com/docs/web-services
- Render environment variables: https://render.com/docs/configure-environment-variables
- Vercel deployment from CLI: https://vercel.com/docs/projects/deploy-from-cli

## Before deployment

1. Push the code to a Git repository accessible to the deployment services.
2. Verify `.env`, `.env.local`, API keys and the local database are excluded from Git.
3. Ensure the Phase 1, Phase 2, Phase 3 and workflow routers are registered in `backend/app/main.py`.
4. Ensure the review workflow models are imported before `Base.metadata.create_all()` runs.
5. Add deployed frontend origin to FastAPI CORS configuration. Prefer a `FRONTEND_ORIGIN` environment variable over hardcoding an unknown deployment URL. Do not use `allow_origins=["*"]` with credentials enabled.
6. Choose where persistent data will live. Don't rely on a SQLite file in an ephemeral deployment filesystem.
7. Check provider terms, quotas and where submitted content is processed before using confidential material.

## Deploy FastAPI to Render

Create a Web Service linked to the repository and set its **Root Directory** to `backend`.

Build command (adjust if the requirements files have different names in your repo):

```bash
pip install -r requirements-phase1.txt && pip install -r requirements-phase2.txt && pip install -r requirements-review.txt && pip install -r requirements-workflow.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set environment variables in the Render dashboard, not in committed files. Provide the LLM provider/base URL/model and API key. Set `DATABASE_URL` to a persistent SQLite path or your configured managed database URL. Set `FRONTEND_ORIGIN` to the deployed frontend origin and update `main.py` to include it in CORS.

Set the health check path to `/health`. Render documents that a public web service must bind on `0.0.0.0` and can configure environment variables, health checks and persistent disks: https://render.com/docs/web-services.

## Deploy Next.js to Vercel

Create a project from the same repository and set the project root to `frontend` (or your actual Next.js root if you run it at repository root). Configure:

```env
NEXT_API_BASE_URL=https://YOUR-BACKEND-HOST
```

Replace the placeholder with the deployed backend base URL and do not add a trailing path such as `/api`. The existing client should append its endpoint paths. Redeploy after changing environment variables.

## Post-deployment smoke checks

1. Open `https://YOUR-BACKEND-HOST/health`; expect `{"status":"ok","service":"brandgate-api"}`.
2. Open `https://YOUR-BACKEND-HOST/docs` and confirm expected routers appear.
3. Open the frontend `/review` route.
4. Create one test review using fictional data.
5. Reload the review and confirm it persists.
6. Save a revision, approve the new version and confirm the old approval remains tied to its original version.
7. Inspect service logs if the frontend receives CORS errors, the database is missing tables or the provider returns an error.

## Deployment limitations to disclose

The current MVP uses a reviewer-name field unless authenticated identity has been added. Do not represent that as secure identity verification. Use fictional test data for public demos, keep API keys server-side, and never claim enterprise security controls you have not implemented and tested.
