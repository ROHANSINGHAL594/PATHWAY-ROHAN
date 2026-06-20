"""Package initializer for contractparseragent.

Loads a local `.env` file (if present) into the process environment so
modules importing this package can read configuration like
`ANTHROPIC_API_KEY` via `os.getenv`.

This prefers `python-dotenv` when available, and falls back to a
lightweight parser that supports `KEY=VALUE` and quoted values.
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DOTENV = _HERE / ".env"

def _load_dotenv_fallback(dotenv_path: Path) -> None:
    try:
        text = dotenv_path.read_text(encoding="utf-8")
    except Exception:
        return

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Remove surrounding quotes if present
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        # Only set if not already in environment
        os.environ.setdefault(k, v)


if _DOTENV.exists():
    # Prefer python-dotenv if installed
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path=str(_DOTENV), override=False)
    except Exception:
        _load_dotenv_fallback(_DOTENV)

__all__ = []
