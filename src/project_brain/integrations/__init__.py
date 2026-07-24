"""Versioned provider-neutral consumer integration contract."""

from .capabilities import capability_report
from .consumer import execute

__all__ = ["capability_report", "execute"]
