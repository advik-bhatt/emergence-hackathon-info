"""Record/replay store for CRAFT responses.

The repo must run end-to-end with zero credentials, so every CRAFT response is committed to
fixtures/ and replayed by default. The live path stays real; it just isn't required.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class CassetteMiss(LookupError):
    """No fixture recorded for this question."""


@dataclass(frozen=True)
class QueryResult:
    slug: str
    nl_question: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]

    def as_dicts(self) -> list[dict[str, Any]]:
        keys = [c.lower() for c in self.columns]
        seen: set[str] = set()
        duplicates = {k for k in keys if k in seen or seen.add(k)}  # type: ignore[func-returns-value]
        if duplicates:
            raise ValueError(
                f"Duplicate column name(s) after lowercasing: {sorted(duplicates)} "
                f"(from columns {self.columns!r}). Two distinctly-cased columns collided; "
                f"as_dicts would otherwise silently keep whichever one comes last."
            )
        return [dict(zip(keys, row, strict=True)) for row in self.rows]


class Cassette:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def _path(self, slug: str) -> Path:
        return self.directory / f"{slug}.json"

    def replay(self, slug: str) -> QueryResult:
        path = self._path(slug)
        if not path.exists():
            raise CassetteMiss(
                f"No fixture for {slug!r} at {path}. "
                f"Re-record with PROMISE_ENGINE_MODE=record."
            )
        payload = json.loads(path.read_text())
        return QueryResult(
            slug=slug,
            nl_question=payload["nl_question"],
            sql=payload["sql"],
            columns=payload["columns"],
            rows=payload["rows"],
        )

    def record(self, slug: str, *, nl_question: str, sql: str,
               columns: list[str], rows: list[list[Any]]) -> QueryResult:
        self.directory.mkdir(parents=True, exist_ok=True)
        self._path(slug).write_text(json.dumps({
            "slug": slug, "nl_question": nl_question, "sql": sql,
            "columns": columns, "rows": rows,
            "recorded_at": datetime.now(UTC).isoformat(),
        }, indent=2) + "\n")
        return QueryResult(slug, nl_question, sql, columns, rows)
