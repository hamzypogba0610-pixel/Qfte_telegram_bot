"""
QFTE V13 — Exemple de stratégie : RSI simple
"""

from typing import Optional
from logging_config import setup_logging

log = setup_logging()


class RSIStrategy:
    """
    Stratégie RSI simple.
    - Achat si RSI < 30
    - Vente si RSI > 70
    """

    def __init__(self, rsi_period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signal(self, rsi_value: float, symbol: str, timeframe: str, price: float) -> Optional[dict]:
        """
        Génère un signal de trading basé sur la valeur RSI.
        Retourne un dict ou None.
        """
        if rsi_value < self.oversold:
            log.info("Signal LONG", symbol=symbol, timeframe=timeframe, rsi=rsi_value)
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal_type": "long",
                "entry_price": price,
                "reason": f"RSI oversold ({rsi_value:.2f})",
            }
        elif rsi_value > self.overbought:
            log.info("Signal SHORT", symbol=symbol, timeframe=timeframe, rsi=rsi_value)
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal_type": "short",
                "entry_price": price,
                "reason": f"RSI overbought ({rsi_value:.2f})",
            }
        return None
