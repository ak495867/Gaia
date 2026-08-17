from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import BookLevel, FeeSchedule, Order, OrderStatus, OrderType, Quote, Side, TimeInForce, Trade


@dataclass(slots=True)
class BookSnapshot:
    timestamp: int
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]


class LimitOrderBook:
    def __init__(self, symbol: str = "GAIA", fee_schedule: FeeSchedule | None = None) -> None:
        self.symbol = symbol
        self.fee_schedule = fee_schedule or FeeSchedule()
        self._bids: dict[str, Order] = {}
        self._asks: dict[str, Order] = {}
        self._orders: dict[str, Order] = {}
        self._trade_sequence = 0
        self._last_timestamp = 0

    @property
    def orders(self) -> tuple[Order, ...]:
        return tuple(self._orders.values())

    @property
    def last_trade_price(self) -> float | None:
        return getattr(self, "_last_trade_price", None)

    @property
    def traded_volume(self) -> float:
        return getattr(self, "_traded_volume", 0.0)

    def submit(self, order: Order) -> tuple[Trade, ...]:
        if order.order_id in self._orders:
            raise ValueError(f"duplicate order id: {order.order_id}")
        self._last_timestamp = max(self._last_timestamp, order.timestamp)
        if order.time_in_force is TimeInForce.FOK and self._available(order) + 1e-12 < order.quantity:
            order.status = OrderStatus.REJECTED
            self._orders[order.order_id] = order
            return ()
        self._orders[order.order_id] = order
        trades: list[Trade] = []
        own_side = self._asks if order.side is Side.BUY else self._bids
        while order.is_open and own_side:
            resting = self._best_opposite(order.side)
            if resting is None or not self._crosses(order, resting):
                break
            quantity = min(order.remaining, resting.remaining)
            price = resting.price if resting.price is not None else order.price
            if price is None:
                raise ValueError("unable to determine execution price")
            self._trade_sequence += 1
            trade = Trade(
                trade_id=f"trade-{self._trade_sequence}",
                buy_order_id=order.order_id if order.side is Side.BUY else resting.order_id,
                sell_order_id=order.order_id if order.side is Side.SELL else resting.order_id,
                buyer_id=order.trader_id if order.side is Side.BUY else resting.trader_id,
                seller_id=order.trader_id if order.side is Side.SELL else resting.trader_id,
                price=price,
                quantity=quantity,
                timestamp=order.timestamp,
                maker_order_id=resting.order_id,
            )
            order.fill(quantity)
            resting.fill(quantity)
            trades.append(trade)
            self._last_trade_price = price
            self._traded_volume = self.traded_volume + quantity
            if not resting.is_open:
                self._remove_from_side(resting)
        if order.is_open and order.time_in_force is TimeInForce.GTC and order.order_type is OrderType.LIMIT:
            self._add_to_side(order)
        elif order.is_open:
            order.cancel()
        return tuple(trades)

    def cancel(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order is None or not order.is_open:
            return False
        order.cancel()
        self._remove_from_side(order)
        return True

    def quote(self, timestamp: int | None = None) -> Quote:
        bid = self._best(Side.BUY)
        ask = self._best(Side.SELL)
        return Quote(
            bid=bid.price if bid else None,
            ask=ask.price if ask else None,
            bid_size=bid.remaining if bid else 0.0,
            ask_size=ask.remaining if ask else 0.0,
            timestamp=self._last_timestamp if timestamp is None else timestamp,
        )

    def snapshot(self, timestamp: int | None = None, depth: int = 10) -> BookSnapshot:
        if depth <= 0:
            raise ValueError("depth must be positive")
        return BookSnapshot(
            timestamp=self._last_timestamp if timestamp is None else timestamp,
            bids=self._levels(Side.BUY, depth),
            asks=self._levels(Side.SELL, depth),
        )

    def open_orders(self, side: Side | None = None) -> tuple[Order, ...]:
        values = (
            self._bids.values()
            if side is Side.BUY
            else self._asks.values()
            if side is Side.SELL
            else self._orders.values()
        )
        return tuple(order for order in values if order.is_open)

    def _add_to_side(self, order: Order) -> None:
        side = self._bids if order.side is Side.BUY else self._asks
        side[order.order_id] = order

    def _remove_from_side(self, order: Order) -> None:
        side = self._bids if order.side is Side.BUY else self._asks
        side.pop(order.order_id, None)

    def _best(self, side: Side) -> Order | None:
        orders = [order for order in (self._bids if side is Side.BUY else self._asks).values() if order.is_open]
        if not orders:
            return None
        if side is Side.BUY:
            return min(orders, key=lambda order: (-float(order.price), order.timestamp, order.order_id))
        return min(orders, key=lambda order: (float(order.price), order.timestamp, order.order_id))

    def _best_opposite(self, side: Side) -> Order | None:
        return self._best(side.opposite)

    @staticmethod
    def _crosses(incoming: Order, resting: Order) -> bool:
        if incoming.order_type is OrderType.MARKET:
            return True
        if incoming.price is None or resting.price is None:
            return True
        return incoming.price >= resting.price if incoming.side is Side.BUY else incoming.price <= resting.price

    def _available(self, incoming: Order) -> float:
        total = 0.0
        candidates = sorted(
            (order for order in (self._asks if incoming.side is Side.BUY else self._bids).values() if order.is_open),
            key=lambda order: (
                (float(order.price), order.timestamp, order.order_id)
                if incoming.side is Side.BUY
                else (-float(order.price), order.timestamp, order.order_id)
            ),
        )
        for resting in candidates:
            if not self._crosses(incoming, resting):
                break
            total += resting.remaining
        return total

    def _levels(self, side: Side, depth: int) -> tuple[BookLevel, ...]:
        orders = [order for order in (self._bids if side is Side.BUY else self._asks).values() if order.is_open]
        grouped: dict[float, list[Order]] = {}
        for order in orders:
            if order.price is not None:
                grouped.setdefault(order.price, []).append(order)
        prices = sorted(grouped, reverse=side is Side.BUY)[:depth]
        return tuple(
            BookLevel(
                price=price, quantity=sum(order.remaining for order in grouped[price]), order_count=len(grouped[price])
            )
            for price in prices
        )

    def validate(self) -> None:
        bid = self._best(Side.BUY)
        ask = self._best(Side.SELL)
        if bid and ask and bid.price is not None and ask.price is not None and bid.price >= ask.price:
            raise AssertionError("book contains a crossed quote")
        for order in self._orders.values():
            if order.status is OrderStatus.FILLED and order.remaining > 1e-12:
                raise AssertionError("filled order has remaining quantity")

    def load(self, orders: Iterable[Order]) -> None:
        for order in orders:
            if order.order_type is not OrderType.LIMIT or order.price is None:
                raise ValueError("only open limit orders can be loaded")
            self._orders[order.order_id] = order
            self._add_to_side(order)
