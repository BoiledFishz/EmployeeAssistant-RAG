from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.schemas.request import QueryRequest
from app.schemas.response import QueryResponse
from app.services.rag_service import RagService

router = APIRouter(prefix="/query", tags=["query"])


def get_rag_service(request: Request) -> RagService:
    return request.app.state.rag_service


@router.post("", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    service: RagService = Depends(get_rag_service),
) -> QueryResponse:
    return service.query(payload)

