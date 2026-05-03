from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ComplianceResult


class PragmaAPIError(Exception):
    """Raised when the Pragma backend returns an unexpected error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ConfigurationError(Exception):
    """Raised when the Pragma client is misconfigured."""


class ComplianceError(Exception):
    """Raised in 'block' mode when the firewall blocks a decision."""

    def __init__(self, message: str, result: "ComplianceResult") -> None:
        super().__init__(message)
        self.result = result
