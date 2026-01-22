from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.models.schemas import SearchQuery, SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
def search(
    search_query: SearchQuery,
    db: Session = Depends(get_db)
):
    """Search code with natural language query"""
    service = SearchService()
    
    # Default limit is 20, max 100
    limit = 20
    if search_query.filters and 'limit' in search_query.filters:
        limit = min(int(search_query.filters['limit']), 100)
    
    results = service.search(
        db=db,
        query=search_query.query,
        project_id=search_query.project_id,
        limit=limit
    )
    
    return SearchResponse(
        results=results,
        total=len(results),
        query=search_query.query
    )


@router.get("/", response_model=SearchResponse)
def search_get(
    q: str = Query(..., description="Search query"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Search code with GET request"""
    service = SearchService()
    
    results = service.search(
        db=db,
        query=q,
        project_id=project_id,
        limit=limit
    )
    
    return SearchResponse(
        results=results,
        total=len(results),
        query=q
    )

