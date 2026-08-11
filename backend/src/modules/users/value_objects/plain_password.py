"""PlainPassword — validated at the application boundary, never persisted."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Self

from src.shared.domain.value_object import ValueObject

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")
_HAS_SPECIAL = re.compile(r"[^A-Za-z0-9]")


@dataclass(frozen=True)
class PlainPassword(ValueObject):
    value: str
    _enforce_complexity: bool = field(default=True, compare=False, repr=False)

    def _validate(self) -> None:
        if len(self.value) < 8:
            raise ValueError("Password must have at least 8 characters")
        if len(self.value) > 128:
            raise ValueError("Password cannot exceed 128 characters")
        if self.value.isspace():
            raise ValueError("Password cannot be blank")
        if not self._enforce_complexity:
            return
        if not _HAS_LETTER.search(self.value):
            raise ValueError("Password must contain at least one letter")
        if not _HAS_DIGIT.search(self.value):
            raise ValueError("Password must contain at least one digit")
        if not _HAS_SPECIAL.search(self.value):
            raise ValueError("Password must contain at least one special character")

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    def from_primitive(cls, value: str) -> Self:
        """New / changed passwords — full complexity rules."""
        return cls(value=value, _enforce_complexity=True)

    @classmethod
    def from_login_attempt(cls, value: str) -> Self:
        """Submitted credential at login — length only (legacy hashes may be weak)."""
        return cls(value=value, _enforce_complexity=False)
