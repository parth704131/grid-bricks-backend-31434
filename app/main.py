from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.analysis import router as analysis_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Wind Procurement Insight API",
    version="0.1.0",
    description=(
        "Backend analytics for reconstructing UK day-ahead wind forecasts and comparing "
        "them with actual generation."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
    return _error_response(request, error.code, error.message, error.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    fields = {issue["loc"][-1] for issue in error.errors()}
    if "decisionTime" in fields:
        return _error_response(
            request,
            "INVALID_DECISION_TIME",
            "decisionTime must be a valid 24-hour HH:MM value.",
            422,
        )
    if "startTime" in fields:
        return _error_response(
            request,
            "INVALID_START_TIME",
            "startTime must be a valid ISO 8601 timestamp.",
            422,
        )
    return _error_response(request, "INVALID_REQUEST", "The request parameters are invalid.", 422)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, error: SQLAlchemyError) -> JSONResponse:
    return _error_response(request, "DATABASE_UNAVAILABLE", "Database unavailable.", 503)


def _error_response(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "requestId": request.state.request_id,
            }
        },
    )


app.include_router(health_router)
app.include_router(analysis_router)
