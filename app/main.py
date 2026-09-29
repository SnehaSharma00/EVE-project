from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import auth, bookings, centres, health, payments, tests, webhooks
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger

tags_metadata = [
    {
        "name": "Health",
        "description": "Service health check and database connectivity verification.",
    },
    {
        "name": "Authentication",
        "description": "User registration, login, and JWT access token handling.",
    },
    {
        "name": "Diagnostic Centres",
        "description": "Diagnostic centres, test pricing, and slot scheduling.",
    },
    {"name": "Diagnostic Tests", "description": "Diagnostic tests catalogue."},
    {
        "name": "Bookings",
        "description": "Diagnostic test booking management and lifecycle state machine.",
    },
    {
        "name": "Payments",
        "description": "Simulated payment gateway processing with Idempotency-Key support.",
    },
    {"name": "Webhooks", "description": "Strictly idempotent payment webhook receiver."},
]

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade Modular Backend for Diagnostic Bookings and Payments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"AppException: [{exc.code}] {exc.message} on path {request.url.path}")
    content = {
        "success": False,
        "error": {
            "code": exc.code,
            "message": exc.message,
        },
    }
    if exc.details is not None:
        content["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Validation error.")
    loc = " -> ".join([str(x) for x in first_error.get("loc", [])])
    if loc:
        msg = f"{loc}: {msg}"
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": msg,
                "details": errors,
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "RESOURCE_NOT_FOUND"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        code = "METHOD_NOT_ALLOWED"

    logger.warning(f"HTTPException [{exc.status_code}]: {exc.detail} on path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": str(exc.detail),
            },
        },
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Exception on path {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            },
        },
    )


# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(centres.router, prefix=settings.API_V1_STR)
app.include_router(tests.router, prefix=settings.API_V1_STR)
app.include_router(bookings.router, prefix=settings.API_V1_STR)
app.include_router(payments.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root_overview():
    """Root endpoint providing service overview and documentation links."""
    return {
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/health",
        "api_v1_prefix": settings.API_V1_STR,
    }
