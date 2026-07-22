"""Structured execution tracing without exposing private chain-of-thought."""

from __future__ import annotations

import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4


class JsonlTracer:
    """Write one ordered JSON object per execution event."""

    def __init__(
        self,
        directory: Path,
        *,
        console: bool = False,
        run_id: str | None = None,
    ) -> None:
        self.run_id = run_id or uuid4().hex
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)
        self.path = self._directory / f"{self.run_id}.jsonl"
        self.path.touch(exist_ok=True)
        self._console = console
        self._sequence = 0
        self._started_at = perf_counter()
        self._last_event: str | None = None
        self._lock = threading.Lock()

    @property
    def has_terminal_event(self) -> bool:
        """Return whether this trace already contains a terminal run event."""

        return self._last_event in {"run_finished", "run_failed"}

    def emit(self, event: str, **data: Any) -> None:
        """Append a sanitized, JSON-serializable event to the current run trace."""

        with self._lock:
            self._sequence += 1
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "elapsed_ms": round((perf_counter() - self._started_at) * 1000, 3),
                "run_id": self.run_id,
                "sequence": self._sequence,
                "event": event,
                "data": data,
            }
            line = json.dumps(record, ensure_ascii=False, default=str)
            with self.path.open("a", encoding="utf-8", newline="\n") as trace_file:
                trace_file.write(line + "\n")
            self._last_event = event

            if self._console:
                summary = data.get("summary") or data.get("message") or ""
                print(
                    f"[trace {self._sequence:02d}] {event}: {summary}",
                    file=sys.stderr,
                )
