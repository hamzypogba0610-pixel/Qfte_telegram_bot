"""
QFTE V13 — Script de lancement principal
"""

import asyncio
import uvicorn

from config import APP_ENV
from logging_config import setup_logging
from database import init_db

log = setup_logging()


async def main():
    """Lancer l'API FastAPI."""
    log.info("Démarrage de QFTE V13...", env=APP_ENV)

    # Initialiser la base de données
    await init_db()

    # Lancer FastAPI avec uvicorn
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(APP_ENV == "development"),
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
