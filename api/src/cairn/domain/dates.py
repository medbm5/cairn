"""Calendar helpers."""

from datetime import date


def months_between(start: date, end: date) -> int:
    """Whole months from start to end (negative if end is before start)."""
    months = (end.year - start.year) * 12 + end.month - start.month
    if end.day < start.day:
        months -= 1
    return months


def add_months(start: date, months: int) -> date:
    """The date `months` whole months after start, so that months_between(start, result) is
    exactly `months`. When the day does not exist in the target month (31 March + 1 month), the
    first day of the following month is used."""
    index = start.year * 12 + start.month - 1 + months
    year, month = divmod(index, 12)
    try:
        return date(year, month + 1, start.day)
    except ValueError:
        year, month = divmod(index + 1, 12)
        return date(year, month + 1, 1)
