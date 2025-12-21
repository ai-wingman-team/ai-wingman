"""Manual context ingestion API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from ai_wingman.integrations.manual_adapter import ManualInputAdapter
from ai_wingman.storage.service import ContextStorageService

router = APIRouter()


class ManualContextRequest(BaseModel):
    """Payload for manual context ingestion."""

    content: str = Field(..., min_length=1)
    user_id: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    channel_id: Optional[str] = None
    thread_id: Optional[str] = None


class ManualContextResponse(BaseModel):
    """Response returned after storing manual context."""

    record_id: str
    created: bool
    version: int
    is_latest: bool


def get_storage_service() -> ContextStorageService:
    """Dependency injection hook for the storage service."""

    return ContextStorageService()


def get_manual_adapter(
    storage: ContextStorageService = Depends(get_storage_service),
) -> ManualInputAdapter:
    """Resolve a ManualInputAdapter instance for the request."""

    return ManualInputAdapter(storage_service=storage)


@router.post("/context/manual", response_model=ManualContextResponse)
async def ingest_manual_context(
    payload: ManualContextRequest,
    adapter: ManualInputAdapter = Depends(get_manual_adapter),
) -> ManualContextResponse:
    """Accept manually entered context and persist it."""

    try:
        result = await adapter.ingest(
            payload.content,
            user_id=payload.user_id,
            metadata=payload.metadata,
            channel_id=payload.channel_id,
            thread_id=payload.thread_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ManualContextResponse(
        record_id=result.record_id,
        created=result.created,
        version=result.version,
        is_latest=result.is_latest,
    )


app = FastAPI(title="AI Wingman API")
app.include_router(router, prefix="/api")

__all__ = ["app", "router"]
