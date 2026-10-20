from decimal import Decimal, InvalidOperation

CENT = Decimal("0.01")
FEE_RATE = Decimal("0.01")


def parse_amount(value: str | int | float | Decimal) -> Decimal:
    """Turn an amount typed by a human or emitted by the agent into a Decimal."""
    if isinstance(value, str):
        value = value.strip().removeprefix("$").replace(",", "")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError(f"invalid amount: {value!r}") from None


def fee_for(amount: Decimal) -> Decimal:
    """1% processing fee, rounded to the cent. Our card processor rounds half up."""
    return (amount * FEE_RATE).quantize(CENT)


def fmt(amount: Decimal) -> str:
    return f"${amount:,.2f}"
