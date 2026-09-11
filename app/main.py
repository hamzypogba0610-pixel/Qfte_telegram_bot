"""
QFTE V13 — Point d'entrée FastAPI
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from logging_config import setup_logging
from app.routers import signals

log = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage de l'app."""
    await init_db()
    yield
    # Nettoyage à l'arrêt (si nécessaire)


app = FastAPI(
    title="QFTE V13 API",
    description="Quantitative Futures & Telegram Engine — Version 13",
    version="0.1.0",
    lifespan=lifespan,
)

# Inclure les routers
app.include_router(signals.router)


@app.get("/")
async def root():
    log.info("Root endpoint called")
    return {"status": "ok", "service": "qfte-v13"}


@app.get("/health")
async def health():
    log.info("Health check")
    return {"status": "healthy"}
