from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .models import AuctionResult, Order, OrderType, Side, Trade


class UniformPriceAuction:
    def __init__(self, reference_price: float | None = None) -> None:
        self.reference_price = reference_price
        self._trade_sequence = 0

    def clear(self, orders: Iterable[Order], timestamp: int) -> AuctionResult:
        eligible = [
            order
            for order in orders
            if order.is_open and order.order_type is OrderType.LIMIT and order.price is not None
        ]
        if not eligible:
            return AuctionResult(None, 0.0, (), (), ())
        candidates = sorted({float(order.price) for order in eligible})
        scored = []
        for price in candidates:
            buy_quantity = sum(
                order.remaining
                for order in eligible
                if order.side is Side.BUY and order.price is not None and order.price >= price
            )
            sell_quantity = sum(
                order.remaining
                for order in eligible
                if order.side is Side.SELL and order.price is not None and order.price <= price
            )
            scored.append((min(buy_quantity, sell_quantity), price))
        max_volume = max(volume for volume, _ in scored)
        reference = self.reference_price if self.reference_price is not None else sum(candidates) / len(candidates)
        clearing_price = min(
            (price for volume, price in scored if abs(volume - max_volume) <= 1e-12),
            key=lambda price: (abs(price - reference), price),
        )
        buys = sorted(
            (
                order
                for order in eligible
                if order.side is Side.BUY and order.price is not None and order.price >= clearing_price
            ),
            key=lambda order: (-order.price, order.timestamp, order.order_id),
        )
        sells = sorted(
            (
                order
                for order in eligible
                if order.side is Side.SELL and order.price is not None and order.price <= clearing_price
            ),
            key=lambda order: (order.price, order.timestamp, order.order_id),
        )
        trades: list[Trade] = []
        buy_index = 0
        sell_index = 0
        matched = 0.0
        while buy_index < len(buys) and sell_index < len(sells):
            buyer = buys[buy_index]
            seller = sells[sell_index]
            quantity = min(buyer.remaining, seller.remaining)
            if quantity <= 1e-12:
                break
            self._trade_sequence += 1
            trades.append(
                Trade(
                    trade_id=f"auction-trade-{self._trade_sequence}",
                    buy_order_id=buyer.order_id,
                    sell_order_id=seller.order_id,
                    buyer_id=buyer.trader_id,
                    seller_id=seller.trader_id,
                    price=clearing_price,
                    quantity=quantity,
                    timestamp=timestamp,
                )
            )
            buyer.fill(quantity)
            seller.fill(quantity)
            matched += quantity
            if not buyer.is_open:
                buy_index += 1
            if not seller.is_open:
                sell_index += 1
        accepted = tuple(order.order_id for order in eligible if order.filled > 0)
        rejected = tuple(order.order_id for order in eligible if order.filled <= 0)
        return AuctionResult(clearing_price, matched, tuple(trades), accepted, rejected)


@dataclass(slots=True)
class DarkPool:
    reference_price: float
    price_improvement_bps: float = 0.0
    _bids: list[Order] = field(init=False, repr=False)
    _asks: list[Order] = field(init=False, repr=False)
    _trade_sequence: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.reference_price <= 0:
            raise ValueError("reference price must be positive")
        if self.price_improvement_bps < 0:
            raise ValueError("price improvement cannot be negative")
        self._bids: list[Order] = []
        self._asks: list[Order] = []
        self._trade_sequence = 0

    def submit(self, order: Order) -> tuple[Trade, ...]:
        if order.order_type is not OrderType.MARKET and order.price is None:
            raise ValueError("dark-pool orders need a limit price or market type")
        side = self._bids if order.side is Side.BUY else self._asks
        side.append(order)
        return self.match(order.timestamp)

    def match(self, timestamp: int) -> tuple[Trade, ...]:
        trades: list[Trade] = []
        while self._bids and self._asks:
            buyer = self._bids[0]
            seller = self._asks[0]
            if not self._eligible(buyer, seller):
                break
            quantity = min(buyer.remaining, seller.remaining)
            price = self._execution_price(buyer.side)
            self._trade_sequence += 1
            trades.append(
                Trade(
                    trade_id=f"dark-trade-{self._trade_sequence}",
                    buy_order_id=buyer.order_id,
                    sell_order_id=seller.order_id,
                    buyer_id=buyer.trader_id,
                    seller_id=seller.trader_id,
                    price=price,
                    quantity=quantity,
                    timestamp=timestamp,
                )
            )
            buyer.fill(quantity)
            seller.fill(quantity)
            if not buyer.is_open:
                self._bids.pop(0)
            if not seller.is_open:
                self._asks.pop(0)
        return tuple(trades)

    def _eligible(self, buyer: Order, seller: Order) -> bool:
        buy_ok = buyer.order_type is OrderType.MARKET or buyer.price is None or buyer.price >= self.reference_price
        sell_ok = seller.order_type is OrderType.MARKET or seller.price is None or seller.price <= self.reference_price
        return buy_ok and sell_ok

    def _execution_price(self, aggressor_side: Side) -> float:
        adjustment = self.reference_price * self.price_improvement_bps / 10000.0
        if aggressor_side is Side.BUY:
            return self.reference_price - adjustment
        return self.reference_price + adjustment

    @property
    def resting_orders(self) -> tuple[Order, ...]:
        return tuple(self._bids + self._asks)
