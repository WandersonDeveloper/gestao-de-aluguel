from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.config.storage import ensure_bucket_exists
from app.domain.exceptions import (
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    UnauthorizedError,
)
from app.routes.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_bucket_exists()
    except Exception as exc:  # object storage é opcional para a API subir
        print(f"Aviso: não foi possível conectar ao object storage no startup: {exc}")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Autenticação é via Bearer token (não cookies), então liberar "*" aqui não
# expõe sessão nenhuma — só permite que o frontend (em qualquer porta local
# durante o dev) consiga chamar a API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.exception_handler(ExternalServiceError)
def handle_external_service_error(request: Request, exc: ExternalServiceError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Loga o corpo bruto da requisição junto com os erros de validação — o log
    # de acesso do uvicorn só mostra "422", sem detalhe nenhum, o que torna
    # esse tipo de bug muito mais lento de diagnosticar em produção/dev.
    body = await request.body()
    print(f"422 em {request.method} {request.url.path}: body={body!r} errors={exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
