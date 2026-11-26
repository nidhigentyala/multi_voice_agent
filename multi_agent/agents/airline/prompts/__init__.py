from datetime import datetime
from pathlib import Path

_DIR = Path(__file__).resolve().parent


def prompt(name: str) -> str:
    """Read prompts/<name>.md."""
    return (_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def build_instructions(now: datetime) -> str:
    """Voice rules + desk rules, with today's date filled in."""
    today = f"{now:%A}, {now:%B} {now.day}, {now.year}"
    desk = prompt("desk").replace("{{today}}", today).replace("{{today_iso}}", now.date().isoformat())
    return prompt("voice") + "\n\n" + desk
