from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    UnauthorizedError,
)
from app.routes.api import api_router

app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(UnauthorizedError)
def handle_unauthorized(request: Request, exc: UnauthorizedError) -> JSONResponse:
    return JSONResponse(
        status_code=401, content={"detail": str(exc)}, headers={"WWW-Authenticate": "Bearer"}
    )


@app.exception_handler(ForbiddenError)
def handle_forbidden(request: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(InvalidTransitionError)
def handle_invalid_transition(request: Request, exc: InvalidTransitionError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
