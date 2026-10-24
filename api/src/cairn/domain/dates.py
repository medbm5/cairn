"""Calendar helpers."""

from datetime import date


def months_between(start: date, end: date) -> int:
    """Whole months from start to end (negative if end is before start)."""
    months = (end.year - start.year) * 12 + end.month - start.month
    if end.day < start.day:
        months -= 1
    return months
