"""Domain models for orders."""

from enum import Enum, StrEnum

from pydantic import BaseModel


class OrderState(Enum):
    OPEN = "OPEN"
    SHIPPED = "SHIPPED"


class PaymentState(StrEnum):
    PAID = "paid"
    REFUNDED = "REFUNDED"


class Order(BaseModel):
    order_id: str
    quantity: int
    state: OrderState
