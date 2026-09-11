"""
QFTE V13 — Router API pour les signaux
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from app.models.signal import Signal, SignalType

router = APIRouter(prefix="/signals", tags=["signals"])


class SignalCreate(BaseModel):
    symbol: str
    timeframe: str
    signal_type: str  # "long" ou "short"
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    confidence: float | None = None


@router.get("/", response_model=List[dict])
async def list_signals(db: AsyncSession = Depends(get_db)):
    """Lister tous les signaux actifs."""
    result = await db.execute(select(Signal).where(Signal.is_active == True))
    signals = result.scalars().all()
    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "timeframe": s.timeframe,
            "signal_type": s.signal_type.value,
            "entry_price": s.entry_price,
            "stop_loss": s.stop_loss,
            "take_profit": s.take_profit,
            "confidence": s.confidence,
            "created_at": s.created_at.isoformat(),
        }
        for s in signals
    ]


@router.get("/{signal_id}", response_model=dict)
async def get_signal(signal_id: int, db: AsyncSession = Depends(get_db)):
    """Récupérer un signal par son ID."""
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return {
        "id": signal.id,
        "symbol": signal.symbol,
        "timeframe": signal.timeframe,
        "signal_type": signal.signal_type.value,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "confidence": signal.confidence,
        "is_active": signal.is_active,
        "created_at": signal.created_at.isoformat(),
        "updated_at": signal.updated_at.isoformat(),
    }


@router.post("/", response_model=dict)
async def create_signal(data: SignalCreate, db: AsyncSession = Depends(get_db)):
    """Créer un nouveau signal."""
    try:
        signal_type = SignalType(data.signal_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="signal_type must be 'long' or 'short'")

    signal = Signal(
        symbol=data.symbol.upper(),
        timeframe=data.timeframe,
        signal_type=signal_type,
        entry_price=data.entry_price,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        confidence=data.confidence,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(signal)
    await db.commit()
    await db.refresh(signal)

    return {
        "id": signal.id,
        "symbol": signal.symbol,
        "timeframe": signal.timeframe,
        "signal_type": signal.signal_type.value,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "confidence": signal.confidence,
        "is_active": signal.is_active,
        "created_at": signal.created_at.isoformat(),
    }c
