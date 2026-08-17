from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"

    @property
    def opposite(self) -> Side:
        return Side.SELL if self is Side.BUY else Side.BUY


class OrderType(StrEnum):
    LIMIT = "limit"
    MARKET = "market"


class TimeInForce(StrEnum):
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class OrderStatus(StrEnum):
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(slots=True)
class Order:
    order_id: str
    trader_id: str
    side: Side
    quantity: float
    price: float | None
    timestamp: int
    order_type: OrderType = OrderType.LIMIT
    time_in_force: TimeInForce = TimeInForce.GTC
    remaining: float = 0.0
    filled: float = 0.0
    status: OrderStatus = OrderStatus.OPEN
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type is OrderType.LIMIT and (self.price is None or self.price <= 0):
            raise ValueError("limit orders require a positive price")
        if self.order_type is OrderType.MARKET:
            self.price = None
        if self.remaining == 0.0:
            self.remaining = self.quantity

    @property
    def is_open(self) -> bool:
        return self.status in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED} and self.remaining > 1e-12

    def fill(self, quantity: float) -> None:
        if quantity < 0 or quantity > self.remaining + 1e-12:
            raise ValueError("fill quantity exceeds remaining quantity")
        self.remaining = max(0.0, self.remaining - quantity)
        self.filled += quantity
        self.status = OrderStatus.FILLED if self.remaining <= 1e-12 else OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        if self.is_open:
            self.status = OrderStatus.CANCELLED


@dataclass(frozen=True, slots=True)
class Trade:
    trade_id: str
    buy_order_id: str
    sell_order_id: str
    buyer_id: str
    seller_id: str
    price: float
    quantity: float
    timestamp: int
    maker_order_id: str | None = None

    @property
    def notional(self) -> float:
        return self.price * self.quantity


@dataclass(frozen=True, slots=True)
class BookLevel:
    price: float
    quantity: float
    order_count: int


@dataclass(frozen=True, slots=True)
class Quote:
    bid: float | None
    ask: float | None
    bid_size: float
    ask_size: float
    timestamp: int

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return self.ask - self.bid

    @property
    def relative_spread(self) -> float | None:
        mid = self.mid
        spread = self.spread
        if mid is None or spread is None or mid == 0:
            return None
        return spread / mid


@dataclass(frozen=True, slots=True)
class MarketEvent:
    event_id: str
    timestamp: int
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FeeSchedule:
    maker_bps: float = 0.0
    taker_bps: float = 0.0
    fixed_fee: float = 0.0

    def fee(self, notional: float, maker: bool) -> float:
        rate = self.maker_bps if maker else self.taker_bps
        return max(0.0, notional * rate / 10000.0 + self.fixed_fee)


@dataclass(frozen=True, slots=True)
class AuctionResult:
    clearing_price: float | None
    matched_quantity: float
    trades: tuple[Trade, ...]
    accepted_orders: tuple[str, ...]
    rejected_orders: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AgentAction:
    trader_id: str
    side: Side
    quantity: float
    price: float | None
    order_type: OrderType = OrderType.LIMIT
    time_in_force: TimeInForce = TimeInForce.GTC
    metadata: dict[str, Any] = field(default_factory=dict)
