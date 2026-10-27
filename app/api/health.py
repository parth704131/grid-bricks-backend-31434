from fastapi import APIRouter, HTTPException, status

from app.core.database import database_is_ready

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK, summary="Process liveness")
def health() -> dict[str, str]:
    """Report that the FastAPI process is accepting requests."""
    return {"status": "ok"}


@router.get("/health/ready", status_code=status.HTTP_200_OK, summary="Dependency readiness")
def readiness() -> dict[str, str]:
    """Report database readiness without exposing operational internals."""
    if not database_is_ready():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    return {"status": "ready"}
