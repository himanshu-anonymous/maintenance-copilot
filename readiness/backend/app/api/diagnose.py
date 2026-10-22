import json
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.diagnosis.engine import diagnosis_engine

router = APIRouter(prefix="/diagnose", tags=["Diagnosis"])


class DiagnoseRequest(BaseModel):
    asset_id: str = Field(..., description="Target equipment identifier (e.g. P-101, M-104)")
    symptom_text: str = Field(..., description="Observed symptom description in plain language")
    alarm_code: Optional[str] = Field(default=None, description="Optional alarm code (e.g. ALM-VIB-101)")
    observations: Optional[List[str]] = Field(default_factory=list, description="Field measurements or notes")
    stream: bool = Field(default=True, description="Enable SSE streaming response")


@router.post("")
async def diagnose(request: DiagnoseRequest):
    """
    Primary Diagnosis Endpoint.
    Streams evidence-grounded candidate causes, procedures, and LLM explanation via Server-Sent Events (SSE).
    """
    if request.stream:
        return StreamingResponse(
            diagnosis_engine.diagnose_stream(
                asset_id=request.asset_id,
                symptom_text=request.symptom_text,
                alarm_code=request.alarm_code,
                observations=request.observations
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # Non-streaming collection for scripts or simpler clients
        full_chunks = []
        metadata = None
        cards = None
        done_info = None

        async for sse_event in diagnosis_engine.diagnose_stream(
            asset_id=request.asset_id,
            symptom_text=request.symptom_text,
            alarm_code=request.alarm_code,
            observations=request.observations
        ):
            lines = sse_event.strip().split("\n")
            event_type = ""
            event_data = ""
            for line in lines:
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    event_data = line[6:].strip()

            if event_data:
                parsed = json.loads(event_data)
                if event_type == "metadata":
                    metadata = parsed
                elif event_type == "chunk":
                    full_chunks.append(parsed.get("text", ""))
                elif event_type == "cards":
                    cards = parsed.get("cards", [])
                elif event_type == "done":
                    done_info = parsed

        return {
            "metadata": metadata,
            "explanation": "".join(full_chunks),
            "cards": cards,
            "timing": done_info
        }
