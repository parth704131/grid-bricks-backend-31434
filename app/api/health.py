from fastapi import APIRouter, status

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK, summary="Process liveness")
def health() -> dict[str, str]:
    """Report that the FastAPI process is accepting requests."""
    return {"status": "ok"}
