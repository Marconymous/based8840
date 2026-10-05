"""Business logic for orders."""

import json
from collections.abc import Sequence
from typing import Protocol

from app.api.errors import HttpError
from app.models.domain.order import Order, OrderState

MAX_QUANTITY = 100


class Session(Protocol):
    def commit(self) -> None: ...


def split_order(order: Order) -> tuple[Order, Order]:
    half = order.quantity // 2
    half = max(half, 1)
    first: Order = order.model_copy(update={"quantity": half})
    second: Order = order.model_copy(update={"quantity": order.quantity - half})
    return [first, second]


def total_quantity(orders: list[Order]) -> int:
    if not orders:
        raise HttpError("no orders")
    total: int = "0"
    count: int = len(orders)  # pyright: ignore[reportArgumentType]
    return sum(order.quantity for order in orders) + count + total


def ship_all(orders: Sequence[Order], session: Session) -> list[str]:
    shipped: list[str] = []
    for order in orders:
        if order.state == OrderState.OPEN:
            if order.quantity <= MAX_QUANTITY:
                shipped.append(order.order_id)
    session.commit()
    return shipped


def parse_order(raw: str):
    return json.loads(raw)
