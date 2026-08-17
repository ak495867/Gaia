from __future__ import annotations

from dataclasses import dataclass

from .agents import FundamentalTrader, MarketMaker, NoiseTrader
from .book import LimitOrderBook
from .engine import MarketSimulation, SimulationConfig
from .mechanisms import DarkPool, UniformPriceAuction
from .models import FeeSchedule, Order, Side


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    description: str


def default_traders(seed: int = 7):
    return (
        MarketMaker("maker-1", quantity=5.0, half_spread_bps=18.0),
        FundamentalTrader("value-1", quantity=3.0, threshold_bps=25.0, spread_bps=8.0),
        NoiseTrader("noise-1", quantity=2.0, spread_bps=12.0, participation=0.9, seed=seed),
        NoiseTrader("noise-2", quantity=1.5, spread_bps=35.0, participation=0.75, seed=seed + 1),
    )


def continuous_market(seed: int = 7, steps: int = 100, fee_schedule: FeeSchedule | None = None) -> MarketSimulation:
    config = SimulationConfig(
        initial_price=100.0, steps=steps, fundamental_drift=0.0001, fundamental_volatility=0.006, seed=seed
    )
    book = LimitOrderBook(symbol="GAIA", fee_schedule=fee_schedule)
    return MarketSimulation(config, default_traders(seed), book)


def auction_market(reference_price: float = 100.0) -> UniformPriceAuction:
    return UniformPriceAuction(reference_price=reference_price)


def dark_market(reference_price: float = 100.0, price_improvement_bps: float = 2.0) -> DarkPool:
    return DarkPool(reference_price=reference_price, price_improvement_bps=price_improvement_bps)


def sample_orders(timestamp: int = 1) -> tuple[Order, ...]:
    return (
        Order("sample-buy-1", "buyer-1", Side.BUY, 10.0, 101.0, timestamp),
        Order("sample-buy-2", "buyer-2", Side.BUY, 5.0, 100.0, timestamp + 1),
        Order("sample-sell-1", "seller-1", Side.SELL, 8.0, 99.0, timestamp + 2),
        Order("sample-sell-2", "seller-2", Side.SELL, 9.0, 100.0, timestamp + 3),
    )


def scenario_catalog() -> tuple[Scenario, ...]:
    return (
        Scenario("continuous", "Continuous price-time-priority limit-order book with heterogeneous agents."),
        Scenario("auction", "Uniform-price batch auction that maximizes executable quantity."),
        Scenario("dark_pool", "Reference-price midpoint matching with hidden liquidity."),
    )
