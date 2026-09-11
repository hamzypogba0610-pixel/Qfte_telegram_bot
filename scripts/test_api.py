"""
QFTE V13 — Script de test rapide de l'API
"""

import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000"


async def test_api():
    async with httpx.AsyncClient() as client:
        # Test /health
        print("Testing /health...")
        resp = await client.get(f"{BASE_URL}/health")
        print("Health:", resp.json())

        # Test GET /signals
        print("
Testing GET /signals...")
        resp = await client.get(f"{BASE_URL}/signals/")
        print("Signals:", resp.json())

        # Test POST /signals
        print("
Testing POST /signals...")
        payload = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "signal_type": "long",
            "entry_price": 42000.0,
            "stop_loss": 41500.0,
            "take_profit": 43000.0,
            "confidence": 75.5,
        }
        resp = await client.post(f"{BASE_URL}/signals/", json=payload)
        print("Created signal:", resp.json())

        # Test GET /signals/{id}
        signal_id = resp.json()["id"]
        print(f"
Testing GET /signals/{signal_id}...")
        resp = await client.get(f"{BASE_URL}/signals/{signal_id}")
        print("Signal details:", resp.json())


if __name__ == "__main__":
    asyncio.run(test_api())
