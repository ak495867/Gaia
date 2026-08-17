from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, field

from .agents import MarketContext, Trader
from .book import LimitOrderBook
from .metrics import summary
from .models import MarketEvent, Order, Quote, Trade


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    initial_price: float = 100.0
    steps: int = 100
    fundamental_drift: float = 0.0
    fundamental_volatility: float = 0.01
    seed: int = 7

    def __post_init__(self) -> None:
        if self.initial_price <= 0 or self.steps < 0 or self.fundamental_volatility < 0:
            raise ValueError("invalid simulation configuration")


@dataclass(slots=True)
class SimulationResult:
    trades: list[Trade] = field(default_factory=list)
    quotes: list[Quote] = field(default_factory=list)
    events: list[MarketEvent] = field(default_factory=list)
    fundamental_prices: list[float] = field(default_factory=list)
    last_price: float | None = None

    def metrics(self) -> dict[str, float | int | None]:
        benchmark = self.fundamental_prices[-1] if self.fundamental_prices else None
        return summary(self.trades, self.quotes, [trade.price for trade in self.trades], benchmark)


class MarketSimulation:
    def __init__(self, config: SimulationConfig, traders: Iterable[Trader], book: LimitOrderBook | None = None) -> None:
        self.config = config
        self.traders = tuple(traders)
        self.book = book or LimitOrderBook()
        self._rng = random.Random(config.seed)
        self._order_sequence = 0
        self._event_sequence = 0
        self._fundamental_price = config.initial_price

    def run_continuous(self, steps: int | None = None) -> SimulationResult:
        count = self.config.steps if steps is None else steps
        if count < 0:
            raise ValueError("steps must not be negative")
        result = SimulationResult()
        for timestamp in range(1, count + 1):
            self._advance_fundamental()
            result.fundamental_prices.append(self._fundamental_price)
            quote_before = self.book.quote(timestamp)
            context = MarketContext(timestamp, self._fundamental_price, result.last_price, quote_before)
            for trader in self.traders:
                for action in trader.actions(context):
                    order = self._order_from_action(action, timestamp)
                    trades = self.book.submit(order)
                    result.trades.extend(trades)
                    for trade in trades:
                        result.last_price = trade.price
                        result.events.append(
                            self._event(
                                timestamp,
                                "trade",
                                {
                                    "trade_id": trade.trade_id,
                                    "price": trade.price,
                                    "quantity": trade.quantity,
                                    "buyer_id": trade.buyer_id,
                                    "seller_id": trade.seller_id,
                                },
                            )
                        )
                    result.events.append(
                        self._event(
                            timestamp,
                            "order",
                            {
                                "order_id": order.order_id,
                                "trader_id": order.trader_id,
                                "side": order.side.value,
                                "quantity": order.quantity,
                                "filled": order.filled,
                                "status": order.status.value,
                            },
                        )
                    )
            result.quotes.append(self.book.quote(timestamp))
        return result

    def _advance_fundamental(self) -> None:
        shock = self._rng.gauss(0.0, self.config.fundamental_volatility)
        self._fundamental_price *= max(0.0001, 1.0 + self.config.fundamental_drift + shock)

    def _order_from_action(self, action, timestamp: int) -> Order:
        self._order_sequence += 1
        return Order(
            order_id=f"order-{self._order_sequence}",
            trader_id=action.trader_id,
            side=action.side,
            quantity=action.quantity,
            price=action.price,
            timestamp=timestamp,
            order_type=action.order_type,
            time_in_force=action.time_in_force,
            metadata=action.metadata,
        )

    def _event(self, timestamp: int, kind: str, payload: dict) -> MarketEvent:
        self._event_sequence += 1
        return MarketEvent(f"event-{self._event_sequence}", timestamp, kind, payload)
