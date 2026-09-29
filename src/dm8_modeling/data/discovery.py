"""Find one read-only experiment session for each fly/run Results.csv."""
from __future__ import annotations
from pathlib import Path
from .schema import Session

def discover_sessions(root: Path) -> list[Session]:
    """Find recorded sessions in either Dm8_module or UV-15Hz."""
    root = root.expanduser().resolve()
    condition = root / "UV-15Hz" if (root / "UV-15Hz").is_dir() else root
    sessions = []
    for results in sorted(condition.glob("fly*/*/Results.csv")):
        run = results.parent
        sessions.append(Session(run, run.parent.name, run.name))
    if not sessions:
        raise FileNotFoundError(f"No fly*/<run>/Results.csv sessions found under {root}")
    return sessions
