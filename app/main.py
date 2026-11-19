"""FastAPI main application entrypoint for AI Image Understanding & Content Matching Engine."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite schema and indexes
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title="AI Image Understanding & Content Matching Engine",
    description="Production-grade AI image classification, semantic matching, and Mismatch Guard safety layer",
    version="1.0.0",
    lifespan=lifespan
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Shared Requirement 2: Strict Boundary Validation & Clean 4xx Error Handling
# ==============================================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Input payload failed schema validation at the HTTP boundary",
            "details": exc.errors()
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad Request",
            "message": str(exc)
        }
    )

# Include central router
app.include_router(api_router)

@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "healthy",
        "service": "ai-image-matching-engine",
        "version": "1.0.0",
        "database": "sqlite_wal_enabled"
    }

@app.get("/", tags=["root"])
def root():
    return {
        "title": "AI Image Understanding & Content Matching Engine",
        "docs": "/docs",
        "health": "/health",
        "evaluation": "/api/eval/latest"
    }
