import os
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
import redis.asyncio as redis
from sqlalchemy import text
from app.config import settings
from app.llm.gemini import gemini_client

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    services: Dict[str, Any]
    environment: str = "production"
    version: str = "1.0.0"


@router.get("", response_model=HealthResponse)
async def get_health():
    services: Dict[str, Any] = {}
    all_healthy = True

    # 1. SQLite Check
    try:
        from app.database import async_session_factory
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        services["sqlite"] = {"status": "healthy", "database": "data/readiness.db"}
    except Exception as e:
        all_healthy = False
        services["sqlite"] = {"status": "unhealthy", "error": str(e)}

    # 2. Redis Check
    try:
        r = redis.from_url(settings.redis_url, socket_timeout=2.0)
        await r.ping()
        await r.aclose()
        services["redis"] = {"status": "healthy", "host": settings.REDIS_HOST, "port": settings.REDIS_PORT}
    except Exception as e:
        all_healthy = False
        services["redis"] = {"status": "unhealthy", "error": str(e)}

    # 3. Gemini LLM Check
    is_gemini_ok, gemini_msg = await gemini_client.check_health()
    if is_gemini_ok:
        services["gemini"] = {
            "status": "healthy",
            "model": settings.LLM_MODEL,
            "fallback_model": settings.LLM_FALLBACK_MODEL
        }
    else:
        # Don't fail the whole health check if rate-limited, but report accurately
        services["gemini"] = {
            "status": "degraded" if "429" in gemini_msg else "unhealthy",
            "message": gemini_msg
        }

    # 4. Optional Neo4j Check
    if settings.ENABLE_NEO4J:
        try:
            from neo4j import AsyncGraphDatabase
            driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            await driver.verify_connectivity()
            await driver.close()
            services["neo4j"] = {"status": "healthy", "uri": settings.NEO4J_URI}
        except Exception as e:
            services["neo4j"] = {"status": "unhealthy", "error": str(e)}

    overall_status = "healthy" if all_healthy else "degraded"
    return HealthResponse(
        status=overall_status,
        services=services
    )
