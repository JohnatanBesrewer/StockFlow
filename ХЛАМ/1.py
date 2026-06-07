from uuid import uuid7
from decimal import Decimal, ROUND_HALF_UP
from typing import Final

PRICE_PRECISION: Final[Decimal] = Decimal("0.01")

print(uuid7())

print("qwerty"[:255])

value = Decimal(3.123)

value = value.quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)
print(value, type(value * 3))