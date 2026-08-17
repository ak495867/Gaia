from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from statistics import mean, pstdev

from .models import Quote, Trade


def vwap(trades: Iterable[Trade]) -> float | None:
    items = tuple(trades)
    notional = sum(trade.notional for trade in items)
    volume = sum(trade.quantity for trade in items)
    return notional / volume if volume else None


def total_volume(trades: Iterable[Trade]) -> float:
    return sum(trade.quantity for trade in trades)


def average_spread(quotes: Iterable[Quote], relative: bool = False) -> float | None:
    values = []
    for quote in quotes:
        value = quote.relative_spread if relative else quote.spread
        if value is not None:
            values.append(value)
    return mean(values) if values else None


def realized_volatility(prices: Iterable[float], periods_per_year: float = 252.0) -> float | None:
    values = tuple(price for price in prices if price > 0)
    if len(values) < 2:
        return None
    returns = tuple(math.log(values[index] / values[index - 1]) for index in range(1, len(values)))
    return pstdev(returns) * math.sqrt(periods_per_year)


def quoted_depth(quotes: Iterable[Quote]) -> float | None:
    values = [quote.bid_size + quote.ask_size for quote in quotes]
    return mean(values) if values else None


def price_impact(trade: Trade, midpoint_before: float | None) -> float | None:
    if midpoint_before is None or midpoint_before == 0:
        return None
    direction = 1.0 if trade.buyer_id else -1.0
    return direction * (trade.price - midpoint_before) / midpoint_before


def trader_volume(trades: Iterable[Trade]) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)
    for trade in trades:
        result[trade.buyer_id] += trade.quantity
        result[trade.seller_id] += trade.quantity
    return dict(result)


def concentration(trades: Iterable[Trade]) -> float | None:
    volumes = list(trader_volume(trades).values())
    total = sum(volumes)
    if not total:
        return None
    shares = [volume / total for volume in volumes]
    return sum(share * share for share in shares)


def execution_fairness(trades: Iterable[Trade], benchmark: float | None) -> float | None:
    if benchmark is None:
        return None
    items = tuple(trades)
    volume = sum(trade.quantity for trade in items)
    if not volume:
        return None
    weighted_deviation = sum(abs(trade.price - benchmark) * trade.quantity for trade in items) / volume
    return weighted_deviation / benchmark if benchmark else None


def summary(
    trades: Iterable[Trade], quotes: Iterable[Quote], prices: Iterable[float], benchmark: float | None = None
) -> dict[str, float | int | None]:
    trade_items = tuple(trades)
    quote_items = tuple(quotes)
    price_items = tuple(prices)
    return {
        "trade_count": len(trade_items),
        "volume": total_volume(trade_items),
        "vwap": vwap(trade_items),
        "average_spread": average_spread(quote_items),
        "average_relative_spread": average_spread(quote_items, relative=True),
        "average_quoted_depth": quoted_depth(quote_items),
        "realized_volatility": realized_volatility(price_items),
        "trader_concentration": concentration(trade_items),
        "execution_fairness": execution_fairness(trade_items, benchmark),
    }
