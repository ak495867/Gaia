from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol

from .models import AgentAction, Quote, Side


@dataclass(frozen=True, slots=True)
class MarketContext:
    timestamp: int
    fundamental_price: float
    last_price: float | None
    quote: Quote


class Trader(Protocol):
    trader_id: str

    def actions(self, context: MarketContext) -> tuple[AgentAction, ...]: ...


@dataclass(slots=True)
class NoiseTrader:
    trader_id: str
    quantity: float = 1.0
    spread_bps: float = 25.0
    participation: float = 0.8
    seed: int = 1
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.spread_bps < 0 or not 0 <= self.participation <= 1:
            raise ValueError("invalid noise trader parameters")
        self._rng = random.Random(self.seed)

    def actions(self, context: MarketContext) -> tuple[AgentAction, ...]:
        if self._rng.random() > self.participation:
            return ()
        side = Side.BUY if self._rng.random() < 0.5 else Side.SELL
        reference = context.last_price or context.fundamental_price
        adjustment = reference * self.spread_bps / 10000.0
        price = reference + adjustment if side is Side.BUY else max(0.0001, reference - adjustment)
        return (AgentAction(self.trader_id, side, self.quantity, price, metadata={"strategy": "noise"}),)


@dataclass(slots=True)
class FundamentalTrader:
    trader_id: str
    quantity: float = 1.0
    threshold_bps: float = 40.0
    spread_bps: float = 10.0

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.threshold_bps < 0 or self.spread_bps < 0:
            raise ValueError("invalid fundamental trader parameters")

    def actions(self, context: MarketContext) -> tuple[AgentAction, ...]:
        observed = context.last_price or context.fundamental_price
        gap_bps = (context.fundamental_price - observed) / observed * 10000.0 if observed else 0.0
        if abs(gap_bps) < self.threshold_bps:
            return ()
        side = Side.BUY if gap_bps > 0 else Side.SELL
        adjustment = observed * self.spread_bps / 10000.0
        price = observed + adjustment if side is Side.BUY else max(0.0001, observed - adjustment)
        return (
            AgentAction(
                self.trader_id, side, self.quantity, price, metadata={"strategy": "fundamental", "gap_bps": gap_bps}
            ),
        )


@dataclass(slots=True)
class MarketMaker:
    trader_id: str
    quantity: float = 1.0
    half_spread_bps: float = 20.0

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.half_spread_bps < 0:
            raise ValueError("invalid market maker parameters")

    def actions(self, context: MarketContext) -> tuple[AgentAction, ...]:
        reference = context.last_price or context.fundamental_price
        half_spread = reference * self.half_spread_bps / 10000.0
        bid = max(0.0001, reference - half_spread)
        ask = reference + half_spread
        return (
            AgentAction(self.trader_id, Side.BUY, self.quantity, bid, metadata={"strategy": "market_maker"}),
            AgentAction(self.trader_id, Side.SELL, self.quantity, ask, metadata={"strategy": "market_maker"}),
        )
