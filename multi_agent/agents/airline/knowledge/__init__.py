from pathlib import Path

_GUIDE = Path(__file__).resolve().parents[1] / "carrier" / "airline_info"


def load_guide() -> str:
    """Join every published Markdown file into one guide."""
    parts = [p.read_text(encoding="utf-8").strip() for p in sorted(_GUIDE.glob("*.md"))]
    return "\n\n".join(parts)
