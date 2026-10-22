import os
from pathlib import Path
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.llm.gemini import gemini_client
from app.graph.json_store import graph_store
from app.diagnosis.engine import diagnosis_engine
from app.api.health import router as health_router
from app.api.diagnose import router as diagnose_router
from app.api.metrics import router as metrics_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("readiness")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Readiness Assistant backend...")
    
    # 1. Initialize SQLite tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")

    # 2. Load Graph snapshot into memory
    possible_paths = [
        Path("/app/graph.json"),
        Path(__file__).resolve().parent.parent.parent / "graph.json",
        Path("graph.json")
    ]
    loaded = False
    for p in possible_paths:
        if p.exists():
            graph_store.load_from_file(p)
            diagnosis_engine.initialize_indexes()
            logger.info(f"Loaded graph snapshot from {p}")
            loaded = True
            break
    if not loaded:
        logger.warning("graph.json snapshot not found on startup; building in-memory...")

    # 3. Check LLM client
    try:
        ok, msg = await gemini_client.check_health()
        logger.info(f"Gemini API healthcheck: {'OK' if ok else 'FAIL'} ({msg})")
    except Exception as e:
        logger.warning(f"Gemini healthcheck warning: {e}")

    yield

    # Clean up resources
    logger.info("Shutting down Readiness Assistant...")
    await gemini_client.close()
    await engine.dispose()


app = FastAPI(
    title="Readiness Assistant API",
    version="1.0.0",
    description="Equipment troubleshooting & maintenance copilot",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = [settings.DASHBOARD_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Server-Timing", "X-Latency-First-Token", "X-Latency-Total"]
)

# Include Routers
app.include_router(health_router, prefix="/api")
app.include_router(diagnose_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Readiness Assistant API",
        "notice": "Demo with synthetic data. Not for real safety decisions.",
        "health": "/api/health",
        "docs": "/docs"
    }
