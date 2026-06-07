from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Final
from uuid import UUID, uuid7
from barcode.ean import EAN13

MAX_STRING_LENGTH: Final[int] = 255
PRICE_PRECISION: Final[Decimal] = Decimal("0.01")
QTY_PRECISION: Final[Decimal] = Decimal("0.001")  # Точность до тысячных (граммовая)


def validate_id(value: UUID | str | None = None) -> UUID:
    """Валидация id из строки или UUID объекта"""
    if value is None:
        return uuid7()
    if isinstance(value, str):
        try:
            uuid_obj = UUID(value)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID format: {value}") from e
    elif isinstance(value, UUID):
        uuid_obj = value
    else:
        raise TypeError(f"id must be str or UUID, got {type(value)}")

    if uuid_obj.version != 7:
        # В системе используются UUIDv7, чтобы идентификаторы были
        # упорядочены по времени и лучше индексировались в БД.
        raise ValueError(f"id must be UUID version 7, got version {uuid_obj.version}")

    return uuid_obj


def validate_string(value: str) -> str:
    """Проверяет строку на соответствие лимитам и очищает от пробелов."""
    if not isinstance(value, str):
        raise TypeError(f"value must be str, got {type(value)}")

    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError("value cannot be empty or whitespace")

    if len(cleaned_value) > MAX_STRING_LENGTH:
        raise ValueError(f"value exceeds maximum length of {MAX_STRING_LENGTH}")

    return cleaned_value


def validate_price(value: Decimal, allow_zero: bool = True) -> Decimal:
    """Проверяет цену/сумму и округляет до 2 знаков (денежная точность).

    Args:
        value: Проверяемое значение Decimal.
        allow_zero: Если False, значение должно быть строго больше 0 (для цен товаров).
    """
    if not isinstance(value, Decimal):
        raise TypeError("value must be a Decimal")

    if not value.is_finite():
        raise ValueError(f"invalid numeric value: {value}")

    if value < 0:
        raise ValueError("value cannot be negative")

    if not allow_zero and value == Decimal("0"):
        raise ValueError("value must be greater than zero")

    return value.quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)


def validate_quantity(value: Decimal | int | str) -> Decimal:
    """Валидирует количество товара, приводит к Decimal и округляет до 3 знаков.

    Raises:
        TypeError: Если передан неподдерживаемый тип.
        ValueError: Если строка не парсится, число невалидно или оно <= 0.
    """
    # 1. Безопасное приведение типов к Decimal
    if isinstance(value, Decimal):
        qty_decimal = value
    elif isinstance(value, (int, str)):
        try:
            # Перевод через str(value) для int безопасен, а для str убирает пробелы
            qty_decimal = Decimal(str(value).strip())
        except (ValueError, ArithmeticError) as e:
            raise ValueError(f"Invalid quantity format: '{value}'") from e
    else:
        raise TypeError(f"quantity must be Decimal, int or str, got {type(value)}")

    # 2. Проверка на конечность числа (Infinity, NaN)
    if not qty_decimal.is_finite():
        raise ValueError(f"Invalid numeric value: {qty_decimal}")

    # 3. Бизнес-логика: количество должно быть строго положительным
    if qty_decimal <= Decimal("0"):
        raise ValueError("quantity must be greater than zero")

    # 4. Квантование (округление до 3 знаков после запятой, н-р: 0.4503 -> 0.450)
    return qty_decimal.quantize(QTY_PRECISION, rounding=ROUND_HALF_UP)


def validate_ean13(code: str) -> str:
    """
    Валидирует EAN-13 код с использованием библиотеки python-barcode.

    Args:
        code: Строка с потенциальным EAN-13 (13 цифр)

    Returns:
        Валидный EAN-13 код (без изменений)

    Raises:
        ValueError: Если код невалиден
    """
    # Проверка базовых условий
    if not isinstance(code, str):
        raise ValueError("EAN-13 must be a string")
    if len(code) != 13:
        raise ValueError(f"Invalid length {len(code)} for EAN-13 (must be 13 digits)")
    if not code.isdigit():
        raise ValueError("EAN-13 must contain only digits")

    # Проверка через библиотеку
    try:
        # Генерируем контрольную сумму для первых 12 цифр
        calculated = EAN13(code[:12]).get_fullcode()
    except Exception as e:
        raise ValueError(f"Barcode generation failed: {str(e)}")

    # Сравниваем с исходным кодом
    if calculated != code:
        raise ValueError(
            f"Invalid check digit. Expected '{calculated[-1]}', got '{code[-1]}'"
        )

    return code


if __name__ == "__main__":
    raise RuntimeError("This module is not intended to be run directly")
