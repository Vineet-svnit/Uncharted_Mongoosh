"""AegisRCA FastAPI Backend Main Application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.indexes import ensure_indexes
from app.db.mongo import close_mongo_client
from app.api.routes import health, chat, evidence

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegisrca")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Initializing AegisRCA Backend...")
    # Attempt to ensure indexes on MongoDB collections
    try:
        ensure_indexes()
    except Exception as e:
        logger.warning(f"Startup MongoDB index check note: {e}")

    yield

    logger.info("Shutting down AegisRCA Backend...")
    close_mongo_client()


app = FastAPI(
    title="AegisRCA - Agentic AI Investigation Engine",
    description="Autonomous Root Cause Analysis API backend powering conversational infrastructure incident investigations.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(evidence.router)


@app.get("/")
def root():
    return {
        "service": "AegisRCA Backend API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

