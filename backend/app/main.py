from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 - registers SQLAlchemy models
from app.api.guidelines import router as guidelines_router
from app.database import Base, engine
from app.api.phase2 import router as phase2_router
from app.api.content_review import router as content_review_router
from app import review_models  # noqa: F401
from app.api.review_workflow import router as review_workflow_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for the MVP. Consider Alembic migrations for a larger deployment.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="BrandGate API",
    description="Pre-publication brand governance MVP API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(guidelines_router, prefix="/api", tags=["Brand guidelines"])

app.include_router(
    phase2_router,
    prefix="/api",
    tags=["Phase 2: Local checks and RAG"],
)

app.include_router(
    content_review_router,
    prefix="/api",
    tags=["Content review"],
)

app.include_router(
    review_workflow_router,
    prefix="/api",
    tags=["Review workflow"],
)

@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "brandgate-api"}
