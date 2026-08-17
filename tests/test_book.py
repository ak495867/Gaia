from gaia.book import LimitOrderBook
from gaia.models import Order, OrderStatus, OrderType, Side, TimeInForce


def test_price_time_priority_and_partial_fill():
    book = LimitOrderBook()
    book.submit(Order("ask-1", "seller-1", Side.SELL, 3.0, 101.0, 1))
    book.submit(Order("ask-2", "seller-2", Side.SELL, 4.0, 100.0, 2))
    book.submit(Order("ask-3", "seller-3", Side.SELL, 2.0, 100.0, 3))
    trades = book.submit(Order("buy-1", "buyer-1", Side.BUY, 5.0, 100.0, 4))
    assert [trade.quantity for trade in trades] == [4.0, 1.0]
    assert [trade.sell_order_id for trade in trades] == ["ask-2", "ask-3"]
    assert trades[0].price == 100.0
    assert book.orders[1].status is OrderStatus.FILLED


def test_market_order_consumes_best_available_prices():
    book = LimitOrderBook()
    book.submit(Order("ask-1", "seller-1", Side.SELL, 2.0, 101.0, 1))
    book.submit(Order("ask-2", "seller-2", Side.SELL, 2.0, 102.0, 2))
    trades = book.submit(Order("buy-1", "buyer-1", Side.BUY, 3.0, None, 3, order_type=OrderType.MARKET))
    assert [trade.price for trade in trades] == [101.0, 102.0]
    assert sum(trade.quantity for trade in trades) == 3.0


def test_fok_order_is_rejected_when_depth_is_insufficient():
    book = LimitOrderBook()
    book.submit(Order("ask-1", "seller-1", Side.SELL, 2.0, 101.0, 1))
    order = Order("buy-1", "buyer-1", Side.BUY, 3.0, 101.0, 2, time_in_force=TimeInForce.FOK)
    assert book.submit(order) == ()
    assert order.status is OrderStatus.REJECTED


def test_cancel_removes_open_order():
    book = LimitOrderBook()
    order = Order("bid-1", "buyer-1", Side.BUY, 2.0, 99.0, 1)
    book.submit(order)
    assert book.cancel("bid-1") is True
    assert book.quote().bid is None
    assert order.status is OrderStatus.CANCELLED
