"""Structured execution tracing without exposing private chain-of-thought."""

from __future__ import annotations

import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
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
        self._console = console
        self._sequence = 0
        self._lock = threading.Lock()

    def emit(self, event: str, **data: Any) -> None:
        """Append a sanitized, JSON-serializable event to the current run trace."""

        with self._lock:
            self._sequence += 1
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "run_id": self.run_id,
                "sequence": self._sequence,
                "event": event,
                "data": data,
            }
            line = json.dumps(record, ensure_ascii=False, default=str)
            with self.path.open("a", encoding="utf-8", newline="\n") as trace_file:
                trace_file.write(line + "\n")

            if self._console:
                summary = data.get("summary") or data.get("message") or ""
                print(
                    f"[trace {self._sequence:02d}] {event}: {summary}",
                    file=sys.stderr,
                )
