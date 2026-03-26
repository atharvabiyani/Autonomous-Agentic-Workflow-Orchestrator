#!/usr/bin/env python3
"""Create a small SQLite file for local MCP demos (value + region columns)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/demo.sqlite")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    conn = sqlite3.connect(out)
    conn.execute(
        """
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY,
            value REAL NOT NULL,
            region TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO metrics (id, value, region) VALUES (?, ?, ?)",
        [(1, 10.0, "east"), (2, 20.0, "west"), (3, 30.0, "east")],
    )
    conn.commit()
    conn.close()
    print(f"Wrote {out.resolve()}")


if __name__ == "__main__":
    main()
