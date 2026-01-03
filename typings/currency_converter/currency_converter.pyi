from collections.abc import Iterable
from datetime import date
from decimal import Decimal

class CurrencyConverter:
    def __init__(
        self,
        currency_file: str | None = ...,
        fallback_on_wrong_date: bool = False,
        fallback_on_missing_rate: bool = False,
        fallback_on_missing_rate_method: str = "linear_interpolation",
        ref_currency: str = "EUR",
        na_values: Iterable[str] = ...,
        decimal: bool = False,
        verbose: bool = False,
    ) -> None: ...
    def convert(
        self,
        amount: float,
        currency: str,
        new_currency: str = "EUR",
        date: date | None = None,
    ) -> Decimal | float: ...
