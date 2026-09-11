"""
QFTE V13 — Point d'entrée FastAPI
"""

from fastapi import FastAPI

from logging_config import setup_logging

log = setup_logging()

app = FastAPI(
    title="QFTE V13 API",
    description="Quantitative Futures & Telegram Engine — Version 13",
    version="0.1.0",
)


@app.get("/")
async def root():
    log.info("Root endpoint called")
    return {"status": "ok", "service": "qfte-v13"}


@app.get("/health")
async def health():
    log.info("Health check")
    return {"status": "healthy"}
