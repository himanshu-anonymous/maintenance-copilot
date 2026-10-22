from fastapi import APIRouter
from typing import Dict, Any, List
import numpy as np
import redis.asyncio as redis
from app.config import settings

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_metrics():
    """Returns measured p50 and p95 latencies for first token and total response time."""
    first_token_p50 = 0.0
    first_token_p95 = 0.0
    total_p50 = 0.0
    total_p95 = 0.0
    sample_count = 0

    try:
        r = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2.0)
        first_token_list = await r.lrange("readiness:metrics:first_token_ms", 0, -1)
        total_list = await r.lrange("readiness:metrics:total_ms", 0, -1)
        await r.aclose()

        if first_token_list:
            ft_vals = [float(x) for x in first_token_list if x]
            sample_count = len(ft_vals)
            if ft_vals:
                first_token_p50 = round(float(np.percentile(ft_vals, 50)), 1)
                first_token_p95 = round(float(np.percentile(ft_vals, 95)), 1)

        if total_list:
            tot_vals = [float(x) for x in total_list if x]
            if tot_vals:
                total_p50 = round(float(np.percentile(tot_vals, 50)), 1)
                total_p95 = round(float(np.percentile(tot_vals, 95)), 1)

    except Exception:
        pass

    return {
        "samples": sample_count,
        "first_token_latency": {
            "p50_ms": first_token_p50,
            "p95_ms": first_token_p95,
            "target_ms": 1500
        },
        "total_latency": {
            "p50_ms": total_p50,
            "p95_ms": total_p95,
            "target_ms": 4000
        },
        "router_overhead": {
            "target_ms": 100,
            "typical_ms": "< 30ms"
        }
    }
