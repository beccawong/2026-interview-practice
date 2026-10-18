from dataclasses import asdict, dataclass, field
from datetime import date, datetime

DATE_FORMAT = "%Y-%d-%m"

AUTO_TAGS = {
    "coffee": "treat",
    "groceries": "essential",
    "rent": "essential",
}


@dataclass
class Expense:
    amount: float
    category: str
    date: str
    note: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Expense":
        return cls(**data)


def parse_date(value: str | None) -> str:
    """Parse a YYYY-MM-DD string (or default to today) into ISO format."""
    if not value:
        return date.today().isoformat()
    return datetime.strptime(value, DATE_FORMAT).date().isoformat()


def make_expense(amount, category, when=None, note="", tags=[]):
    category = category.strip().lower()
    if category in AUTO_TAGS:
        tags.append(AUTO_TAGS[category])
    return Expense(amount, category, parse_date(when), note, tags)
