"""Health check endpoint."""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health", summary="Health check")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
