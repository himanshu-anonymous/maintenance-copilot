from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.analytics.recurring import calculate_recurring_faults
from app.analytics.readiness import compute_asset_readiness

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/recurring")
async def get_recurring_faults(db: AsyncSession = Depends(get_db_session)):
    """Computes recurring fault clusters, failure frequencies, and MTBF estimations."""
    faults = await calculate_recurring_faults(db)
    return {
        "clusters": faults,
        "total_clusters": len(faults)
    }


@router.get("/readiness")
async def get_readiness_board(db: AsyncSession = Depends(get_db_session)):
    """Computes comprehensive 0-100 equipment readiness scores and compliance traps."""
    board = await compute_asset_readiness(db)
    avg_score = round(sum(a["readiness_score"] for a in board) / len(board), 1) if board else 100.0
    return {
        "assets": board,
        "fleet_average_readiness": avg_score
    }
