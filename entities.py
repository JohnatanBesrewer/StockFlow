from __future__ import annotations
from decimal import Decimal
from uuid import UUID, uuid7
from enum import StrEnum, auto
from dataclasses import dataclass
import secrets
from barcode.ean import EAN13
import datetime
import validator


class Unit(StrEnum):
    PIECE = "шт"
    KG = "кг"
    LITER = "л"
    METRE = "м"
    PACK = "упак"
    SET = "компл"
    KIT = "набор"


class TransactionType(StrEnum):
    PURCHASE = auto()  # поступление
    SALE = auto()  # продажа
    RETURN_FROM_CUSTOMER = auto()  # возврат от покупателя
    RETURN_TO_SUPPLIER = auto()  # возврат поставщику
    WRITE_OFF = auto()  # списание
    DEKITTING = auto()  # разукомлектование
    INVENTORY = auto()  # инвентаризация


@dataclass(frozen=True, slots=True)
class Product:
    """Сущность товара (справочник).

    Хранит текущее состояние товара и актуальную цену продажи.
    История цен и движения товара хранится в Transaction и TransactionItem.
    """

    product_id: UUID
    primary_barcode: str
    name: str
    unit: Unit
    sale_price: Decimal
    created_at: datetime.datetime

    def __init__(
        self,
        product_id: UUID | str | None,
        primary_barcode: str | None,
        name: str,
        unit: Unit,
        sale_price: Decimal,
        created_at: datetime.datetime | None,
    ) -> None:
        # Валидация ID
        object.__setattr__(self, "product_id", validator.validate_id(product_id))

        # Генерация или валидация штрихкода
        if primary_barcode is None:
            # 29 — префикс для внутреннего использования на предприятии
            payload = "29" + f"{secrets.randbelow(10**10):010}"
            ean = EAN13(payload)
            object.__setattr__(self, "primary_barcode", ean.get_fullcode())
        else:
            object.__setattr__(
                self, "primary_barcode", validator.validate_ean13(primary_barcode)
            )

        # Валидация строки названия
        object.__setattr__(self, "name", validator.validate_string(name))

        # Валидация Enum единиц измерения
        if not isinstance(unit, Unit):
            raise TypeError(f"unit must be an instance of {Unit.__name__}")
        object.__setattr__(self, "unit", unit)

        # Валидация цены
        object.__setattr__(
            self, "sale_price", validator.validate_price(sale_price, allow_zero=False)
        )

        # Валидация времени создания (с защитой от микросекундного "будущего")
        now_utc = datetime.datetime.now(datetime.UTC)
        tolerance = datetime.timedelta(seconds=2)

        if created_at is None:
            object.__setattr__(self, "created_at", now_utc)
        elif isinstance(created_at, datetime.datetime):
            if created_at.tzinfo is None:
                raise ValueError("created_at must have timezone info")
            if created_at > now_utc + tolerance:
                raise ValueError("created_at cannot be in the future")
            object.__setattr__(self, "created_at", created_at)
        else:
            raise TypeError("created_at must be datetime or None")

    def __eq__(self, other: object) -> bool:
        """Два товара считаются равными, если совпадает их UUID."""
        if not isinstance(other, Product):
            return NotImplemented
        return self.product_id == other.product_id

    def __hash__(self) -> int:
        """Так как __eq__ изменен, хэш тоже должен считаться только по ID."""
        return hash(self.product_id)

    def __repr__(self) -> str:
        """Отладочное представление объекта, пригодное для воссоздания."""
        return (
            f"{self.__class__.__name__}("
            f"product_id=UUID('{self.product_id}'), "
            f"primary_barcode='{self.primary_barcode}', "
            f"name='{self.name}', "
            f"unit=Unit.{self.unit.name}, "
            f"sale_price=Decimal('{self.sale_price}'), "
            f"created_at=datetime.datetime.fromisoformat('{self.created_at.isoformat()}'))"
        )


@dataclass(frozen=True, slots=True)
class TransactionItem:
    """Строка транзакции (позиция документа).
    Содержит снимок (snapshot) информации о товаре, его количестве и цене
    на момент совершения операции. Это гарантирует историческую точность:
    если администратор изменит название или штрихкод товара в справочнике,
    в уже проведенных документах данные останутся неизменными.
    """
    item_id: UUID
    product_id: UUID
    product_barcode: str
    product_name: str
    quantity: Decimal  # Decimal вместо int позволяет продавать весовой (0.450 кг) и разливной товар
    unit_value: str  # Хранит текстовое значение (н-р, "кг"). Защищает историю при изменении Enum Unit
    price: Decimal

    def __init__(
        self,
        item_id: UUID | str | None,
        product_id: UUID | str,
        product_barcode: str,
        product_name: str,
        quantity: Decimal | int | str,
        unit: Unit,
        price: Decimal,
    ) -> None:
        # Валидация идентификаторов (конвертируют str в UUID, если необходимо)
        object.__setattr__(self, "item_id", validator.validate_id(item_id))
        object.__setattr__(self, "product_id", validator.validate_id(product_id))

        # Валидация строковых данных (очистка от лишних пробелов, проверка длины)
        object.__setattr__(
            self, "product_barcode", validator.validate_string(product_barcode)
        )
        object.__setattr__(
            self, "product_name", validator.validate_string(product_name)
        )

        # Приведение количества к Decimal и проверка на строго положительное значение (> 0)
        object.__setattr__(self, "quantity", validator.validate_quantity(quantity))

        # Проверяем, что передан корректный Enum, но сохраняем в поле только его текстовое значение (.value)
        if not isinstance(unit, Unit):
            raise TypeError(f"unit must be an instance of {Unit.__name__}")
        object.__setattr__(self, "unit_value", unit.value)

        # Валидация цены (проверка на неотрицательность, округление до копеек)
        object.__setattr__(self, "price", validator.validate_price(price))

    @property
    def amount(self) -> Decimal:
        """Вычисляемая стоимость позиции (без учета скидок документа)."""
        return self.price * self.quantity

    def __eq__(self, other: object) -> bool:
        """Бизнес-равенство: строки транзакции равны, если совпадают их UUID."""
        if not isinstance(other, TransactionItem):
            return NotImplemented
        return self.item_id == other.item_id

    def __hash__(self) -> int:
        """Хэш вычисляется по item_id.

        Позволяет использовать объект в set() и в качестве ключей dict().
        """
        return hash(self.item_id)

    def __repr__(self) -> str:
        """Отладочное представление, пригодное для точного воссоздания объекта."""
        # Для unit мы пытаемся восстановить имя Enum по сохраненному текстовому значению
        enum_name = next(e.name for e in Unit if e.value == self.unit_value)
        return (
            f"{self.__class__.__name__}("
            f"item_id=UUID('{self.item_id}'), "
            f"product_id=UUID('{self.product_id}'), "
            f"product_barcode='{self.product_barcode}', "
            f"product_name='{self.product_name}', "
            f"quantity=Decimal('{self.quantity}'), "
            f"unit=Unit.{enum_name}, "
            f"price=Decimal('{self.price}'))"
        )


@dataclass(frozen=True, slots=True, repr=False)
class Transaction:
    """Сущность транзакции (товарный документ).

    Является агрегатом, объединяющим строки движения товаров (TransactionItem).
    Инварианты (правила целостности) проверяются в методе __post_init__.
    """

    transaction_id: UUID
    items: tuple[TransactionItem, ...]
    transaction_type: TransactionType
    transaction_date: datetime.date
    created_at: datetime.datetime
    comment: str | None = None
    discount: Decimal = Decimal("0")
    supplier_id: UUID | None = None
    supplier_name: str | None = None

    def __post_init__(self) -> None:
        # --- Валидация ID документа ---
        object.__setattr__(
            self, "transaction_id", validator.validate_id(self.transaction_id)
        )

        # --- Валидация товарных строк ---
        if not isinstance(self.items, tuple) or not self.items:
            raise ValueError("items must be non-empty tuple of TransactionItem")
        if not all(isinstance(item, TransactionItem) for item in self.items):
            raise TypeError("All items must be TransactionItem instances")

        # --- Валидация типа транзакции ---
        if not isinstance(self.transaction_type, TransactionType):
            raise TypeError(f"transaction_type must be {TransactionType.__name__}")

        # --- ВРЕМЕННЫЕ ИНВАРЕАНТЫ (Защита хронологии) ---
        now_utc = datetime.datetime.now(datetime.UTC)
        today_utc = now_utc.date()

        # 1. Запрет проведения задним числом в будущее
        if type(self.transaction_date) is not datetime.date:
            raise TypeError("transaction_date must be exactly datetime.date")
        if self.transaction_date > today_utc:
            raise ValueError("transaction_date cannot be in the future")

        # 2. Проверка системного времени (требуется явная таймзона UTC)
        if not isinstance(self.created_at, datetime.datetime):
            raise TypeError("created_at must be datetime.datetime")
        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() != datetime.timedelta(0)
        ):
            raise ValueError("created_at must be UTC timezone-aware")

        # 3. Логическая связка: документ не мог создаться раньше, чем наступил день его проведения
        start_of_day = datetime.datetime.combine(
            self.transaction_date, datetime.time.min, tzinfo=datetime.UTC
        )
        if self.created_at < start_of_day:
            raise ValueError("created_at cannot be earlier than transaction_date")

        # 4. Защита от микросекундного рассинхрона часов (зазор в 2 секунды)
        tolerance = datetime.timedelta(seconds=2)
        if self.created_at > now_utc + tolerance:
            raise ValueError("created_at cannot be significantly in the future")

        # --- Валидация и очистка комментария ---
        if self.comment is not None and not isinstance(self.comment, str):
            raise TypeError("comment must be str or None")

        cleaned_comment = None
        if self.comment is not None:
            cleaned_comment = self.comment.strip()[: validator.MAX_STRING_LENGTH]
            cleaned_comment = cleaned_comment if cleaned_comment else None
        object.__setattr__(self, "comment", cleaned_comment)

        # --- Проверка логики скидок ---
        base_amount = sum(item.amount for item in self.items)
        if self.transaction_type == TransactionType.SALE:
            # Скидка валидируется как цена (округление, >= 0)
            validated_discount = validator.validate_price(self.discount)
            # Сумма скидки не может быть больше стоимости самих товаров
            if validated_discount > base_amount:
                raise ValueError("discount cannot exceed total items amount")
            object.__setattr__(self, "discount", validated_discount)
        else:
            # В закупках, списаниях или инвентаризациях скидки быть не должно
            if self.discount != Decimal("0"):
                raise ValueError("discount must be 0 for non-SALE transactions")

        # --- Проверка связей с контрагентами (Поставщики) ---
        trns_with_suppl = (
            TransactionType.PURCHASE,
            TransactionType.RETURN_TO_SUPPLIER,
        )
        if self.transaction_type in trns_with_suppl:
            # Поставщик обязателен для прихода и возврата поставщику
            if self.supplier_id is None:
                raise ValueError(
                    f"supplier_id is required for: {', '.join(tr.value for tr in trns_with_suppl)}"
                )
            if not isinstance(self.supplier_id, UUID):
                raise TypeError(
                    f"supplier_id must be UUID, got {type(self.supplier_id)}"
                )
            if self.supplier_name is None:
                raise ValueError(
                    f"supplier_name is required for: {', '.join(tr.value for tr in trns_with_suppl)}"
                )
            validated_name = validator.validate_string(self.supplier_name)
            object.__setattr__(self, "supplier_name", validated_name)
        else:
            # Для продаж, списаний и прочего supplier_id должен оставаться пустым
            if self.supplier_id is not None:
                raise ValueError(
                    f"supplier_id is allowed only for: {', '.join(tr.value for tr in trns_with_suppl)}"
                )
            if self.supplier_name is not None:
                raise ValueError(
                    f"supplier_name is allowed only for: {', '.join(tr.value for tr in trns_with_suppl)}"
                )

    @property
    def total_amount(self) -> Decimal:
        """Итоговая сумма документа к оплате/проведению с учетом скидки."""
        return sum((item.amount for item in self.items), Decimal("0")) - self.discount

    def __repr__(self) -> str:
        """Кастомное представление (repr=False в декораторе), пригодное для воссоздания объекта."""
        return (
            f"{self.__class__.__name__}("
            f"transaction_id={self.transaction_id!r}, "
            f"items={self.items!r}, "
            f"transaction_type={self.transaction_type.__class__.__name__}.{self.transaction_type.name}, "
            f"transaction_date={self.transaction_date!r}, "
            f"created_at={self.created_at!r}, "
            f"comment={self.comment!r}, "
            f"discount={self.discount!r}, "
            f"supplier_id={self.supplier_id!r}), "
            f"supplier_name={self.supplier_name!r})"
        )


@dataclass(frozen=True, slots=True)
class PriceHistoryEntry:
    """
    Одна запись истории цены товара.
    """
    price: Decimal
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None
 


# product1 = Product(
#     None,
#     None,
#     "Молоко",
#     Unit.PIECE,
#     Decimal(120.50),
#     datetime.datetime.now(datetime.UTC),
# )

# print(product1)
# product2 = Product(
#     product_id=UUID("019d1ba9-b68a-739c-ab4c-2f581be66901"),
#     primary_barcode="2986760825672",
#     name="Творог",
#     unit=Unit.PIECE,
#     sale_price=Decimal("120.50"),
#     created_at=datetime.datetime.fromisoformat("2026-03-23T17:06:40.394704+00:00"),
# )
# product3 = product1
# print(product1 == product2)
# print(product1 == product3)
# print(product1)
# print(product2)
# print(product3)

# item1 = TransactionItem(
#     uuid7(),
#     product1.product_id,
#     product1.primary_barcode,
#     product1.name,
#     50,
#     Unit.PIECE,
#     product1.sale_price,
# )
# item2 = TransactionItem(
#     item_id=UUID("019d1be3-5453-7213-880a-b6d502be6dbb"),
#     product_id=UUID("019d1be3-5452-71f1-9c03-1126eab01dc5"),
#     product_barcode="2986760825672",
#     product_name="qq1",
#     quantity=50,
#     unit=Unit.PIECE,
#     price=Decimal("120.50"),
# )

# # print(item1)
# print(item2)

# transaction1 = Transaction(
#     transaction_id=uuid7(),
#     items=(item1, item2),
#     transaction_type=TransactionType.PURCHASE,
#     transaction_date=datetime.date(2024, 1, 15),
#     created_at=datetime.datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=datetime.UTC),
#     comment="Покупка в магазине",
#     discount=Decimal("0.0"),
#     supplier_id=uuid7(),
#     supplier_name="ООО 'Рога и копыта",
# )

# transaction2 = Transaction(
#     transaction_id=UUID("019d8b97-eef1-72e9-9d95-5a302823607f"),
#     items=(
#         TransactionItem(
#             item_id=UUID("019d8b97-eef1-72e9-9d95-5a2f8cc81ea5"),
#             product_id=UUID("019d8b97-eef0-77e8-adaa-5d81e1ac335f"),
#             product_barcode="2912087885327",
#             product_name="qq1",
#             quantity=50,
#             unit=Unit.PIECE,
#             price=Decimal("120.50"),
#         ),
#         TransactionItem(
#             item_id=UUID("019d1be3-5453-7213-880a-b6d502be6dbb"),
#             product_id=UUID("019d1be3-5452-71f1-9c03-1126eab01dc5"),
#             product_barcode="2986760825672",
#             product_name="qq1",
#             quantity=50,
#             unit=Unit.PIECE,
#             price=Decimal("120.50"),
#         ),
#     ),
#     transaction_type=TransactionType.PURCHASE,
#     transaction_date=datetime.date(2024, 1, 15),
#     created_at=datetime.datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=datetime.UTC),
#     comment="Покупка в магазине",
#     discount=Decimal("0.0"),
#     supplier_id=UUID("019d8b97-eef1-72e9-9d95-5a31589a6a13"),
#     supplier_name="ООО Грибная радуга"
# )

# print(transaction1)
# print(transaction2)
