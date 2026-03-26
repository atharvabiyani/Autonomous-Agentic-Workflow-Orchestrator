from __future__ import annotations

from typing import Any

import numpy as np

from schema.plan import NumpyOp


def infer_numeric_column(rows: list[dict[str, Any]], preferred: str | None = None) -> str:
    """Pick a numeric column: preferred, then common names, then first numeric field."""
    if not rows:
        msg = "No rows to infer a numeric column from"
        raise ValueError(msg)
    sample = rows[0]
    order = [preferred, "value", "result", "amount", "price", "score", "total", "n"]
    for name in order:
        if not name:
            continue
        if name in sample and sample[name] is not None:
            try:
                float(sample[name])
                return name
            except (TypeError, ValueError):
                continue
    for key, raw in sample.items():
        if raw is None:
            continue
        try:
            float(raw)
            return str(key)
        except (TypeError, ValueError):
            continue
    msg = "No numeric column found in row dicts"
    raise ValueError(msg)


def _rows_to_numeric_matrix(rows: list[dict[str, Any]], column: str) -> np.ndarray:
    values: list[float] = []
    for row in rows:
        raw = row.get(column)
        if raw is None:
            continue
        values.append(float(raw))
    if not values:
        msg = f"No numeric values found for column {column!r}"
        raise ValueError(msg)
    return np.asarray(values, dtype=np.float64)


def run_numpy_reduction(
    rows: list[dict[str, Any]],
    column: str | None,
    op: NumpyOp,
) -> dict[str, Any]:
    """
    Run a NumPy reduction on one numeric column extracted from tabular row dicts.

    Returns a small serializable summary suitable for API / graph state.
    """
    resolved = infer_numeric_column(rows, preferred=column)
    arr = _rows_to_numeric_matrix(rows, resolved)
    reducer: dict[NumpyOp, Any] = {
        "mean": float(np.mean(arr)),
        "sum": float(np.sum(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }
    return {
        "op": op,
        "column": resolved,
        "n": int(arr.size),
        "result": reducer[op],
    }
