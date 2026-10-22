from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.workflow.models import Asset
from app.graph.json_store import graph_store
from app.analytics.readiness import compute_asset_readiness

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("")
async def list_assets(db: AsyncSession = Depends(get_db_session)):
    """Returns list of equipment assets enriched with real-time readiness scores."""
    readiness_list = await compute_asset_readiness(db)
    return readiness_list


@router.get("/{asset_id}")
async def get_asset_detail(asset_id: str, db: AsyncSession = Depends(get_db_session)):
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    # Get components from graph
    components = graph_store.get_components_for_equipment(asset_id)
    # Get verified history
    incidents = graph_store.get_verified_incidents(asset_id=asset_id)

    return {
        "id": asset.id,
        "tag": asset.tag,
        "name": asset.name,
        "category": asset.category,
        "model": asset.model,
        "serial_number": asset.serial_number,
        "manual_revision": asset.manual_revision,
        "location": asset.location,
        "critical_rating": asset.critical_rating,
        "last_inspection_date": asset.last_inspection_date,
        "status": asset.status,
        "components": components,
        "verified_incidents_history": incidents
    }
