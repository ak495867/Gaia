from gaia.mechanisms import DarkPool, UniformPriceAuction
from gaia.models import Order, OrderStatus, Side


def test_uniform_price_auction_maximizes_executable_volume():
    auction = UniformPriceAuction(reference_price=100.0)
    orders = (
        Order("buy-1", "buyer-1", Side.BUY, 10.0, 101.0, 1),
        Order("buy-2", "buyer-2", Side.BUY, 4.0, 100.0, 2),
        Order("sell-1", "seller-1", Side.SELL, 7.0, 99.0, 3),
        Order("sell-2", "seller-2", Side.SELL, 5.0, 100.0, 4),
    )
    result = auction.clear(orders, timestamp=5)
    assert result.clearing_price == 100.0
    assert result.matched_quantity == 12.0
    assert len(result.trades) == 3
    assert all(trade.price == 100.0 for trade in result.trades)


def test_dark_pool_matches_at_reference_price_with_improvement():
    dark_pool = DarkPool(reference_price=100.0, price_improvement_bps=5.0)
    dark_pool.submit(Order("buy-1", "buyer-1", Side.BUY, 4.0, 101.0, 1))
    trades = dark_pool.submit(Order("sell-1", "seller-1", Side.SELL, 2.0, 99.0, 2))
    assert len(trades) == 1
    assert trades[0].quantity == 2.0
    assert trades[0].price == 99.95
    assert dark_pool.resting_orders[0].status is OrderStatus.PARTIALLY_FILLED
