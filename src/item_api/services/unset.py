"""Sentinel for "field not provided", distinct from an explicit ``None``."""

from enum import Enum
from typing import Final


class Unset(Enum):
    UNSET = "UNSET"


UNSET: Final = Unset.UNSET
