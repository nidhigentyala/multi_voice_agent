"""Helpers that turn data into words a voice agent can say."""

from datetime import date, datetime


def say_time(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def say_day(d: date) -> str:
    return f"{d:%A}, {d:%B} {d.day}"


def say_money(rupees: int) -> str:
    return f"{rupees:,} rupees"


def spell_ref(reference: str) -> str:
    return " ".join(reference)
