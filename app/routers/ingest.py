from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.request import IngestRequest
from app.schemas.response import IngestResponse
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])


def get_ingest_service(request: Request) -> IngestService:
    return request.app.state.ingest_service


@router.post("", response_model=IngestResponse)
def ingest(
    payload: IngestRequest,
    service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    try:
        return service.ingest(payload)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

