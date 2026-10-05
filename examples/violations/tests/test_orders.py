"""Tests for the order services."""

from app.models.domain.order import Order, OrderState
from app.services.orders import split_order


def make_order(quantity: int) -> Order:
    return Order(order_id="o-1", quantity=quantity, state=OrderState.OPEN)


def test_split_order_keeps_the_total() -> None:
    first, second = split_order(make_order(5))
    assert first.quantity + second.quantity == 5


def test_split_order_halves_evenly() -> None:
    first, second = split_order(make_order(5))
    assert first.quantity == second.quantity
