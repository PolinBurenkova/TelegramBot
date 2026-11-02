"""Version metadata."""
from __future__ import annotations

from datetime import date

__version__: str = "1.0.0"
BUILD_DATE: str = date.today().isoformat()

__all__ = ["__version__", "BUILD_DATE"]