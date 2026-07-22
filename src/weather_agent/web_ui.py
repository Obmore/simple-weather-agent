"""Loopback-only interactive web UI using the Python standard library."""

from __future__ import annotations

import json
import re
import sys
import webbrowser
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Timer
from typing import Any
from urllib.parse import unquote, urlsplit

QuestionRunner = Callable[[str], tuple[dict[str, object], int]]

_MAX_REQUEST_BYTES = 16 * 1024
_RUN_ID_PATTERN = re.compile(r"[a-f0-9]{32}")
_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


class _UiServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _asset_bytes(filename: str) -> bytes:
    return files("weather_agent").joinpath("web", filename).read_bytes()


def public_trace_events(records: list[dict[str, Any]]) -> list[dict[str, object]]:
    """Return the sanitized event subset displayed by the interactive UI."""

    public: list[dict[str, object]] = []
    detail_keys = {
        "round",
        "duration_ms",
        "tool",
        "arguments",
        "result",
        "error_type",
        "error",
        "round_count",
        "refused",
    }
    for record in records:
        data = record.get("data", {})
        if not isinstance(data, dict):
            data = {}
        public.append(
            {
                "sequence": int(record.get("sequence", 0)),
                "event": str(record.get("event", "unknown")),
                "elapsed_ms": float(record.get("elapsed_ms", 0.0)),
                "summary": str(data.get("summary", "")),
                "details": {key: data[key] for key in detail_keys if key in data},
            }
        )
    return public


def create_server(
    *,
    host: str,
    port: int,
    trace_dir: Path,
    question_runner: QuestionRunner,
) -> ThreadingHTTPServer:
    """Create a loopback-bound HTTP server without starting its request loop."""

    if host != "127.0.0.1":
        raise ValueError("The interactive UI may bind only to 127.0.0.1.")
    if not 0 <= port <= 65535:
        raise ValueError("The UI port must be between 0 and 65535.")

    trace_dir = trace_dir.resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "SimpleWeatherAgentUI/0.1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _security_headers(self) -> None:
            self.send_header("Content-Security-Policy", _CONTENT_SECURITY_POLICY)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")

        def _send_bytes(
            self,
            status: int,
            payload: bytes,
            content_type: str,
            *,
            disposition: str | None = None,
        ) -> None:
            self.send_response(status)
            self._security_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(status, body, "application/json; charset=utf-8")

        def do_GET(self) -> None:
            path = unquote(urlsplit(self.path).path)
            asset = _ASSETS.get(path)
            if asset:
                filename, content_type = asset
                self._send_bytes(HTTPStatus.OK, _asset_bytes(filename), content_type)
                return
            if path == "/api/health":
                self._send_json(HTTPStatus.OK, {"status": "ok"})
                return
            if path.startswith("/api/traces/"):
                run_id = path.removeprefix("/api/traces/")
                if not _RUN_ID_PATTERN.fullmatch(run_id):
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "Trace not found."})
                    return
                trace_path = trace_dir / f"{run_id}.jsonl"
                if not trace_path.is_file():
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "Trace not found."})
                    return
                self._send_bytes(
                    HTTPStatus.OK,
                    trace_path.read_bytes(),
                    "application/x-ndjson; charset=utf-8",
                    disposition=f'attachment; filename="{run_id}.jsonl"',
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Resource not found."})

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path != "/api/ask":
                unknown_length = self.headers.get("Content-Length", "0")
                if unknown_length.isdigit() and 0 < int(unknown_length) <= _MAX_REQUEST_BYTES:
                    self.rfile.read(int(unknown_length))
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Resource not found."})
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = 0
            if content_length <= 0 or content_length > _MAX_REQUEST_BYTES:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request size."})
                return
            try:
                request = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON request."})
                return
            question = request.get("question") if isinstance(request, dict) else None
            if not isinstance(question, str) or not question.strip():
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Question is required."})
                return
            if len(question) > 2000:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Question is too long."})
                return
            try:
                payload, status = question_runner(question.strip())
            except Exception:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "The local service is temporarily unavailable."},
                )
                return
            self._send_json(status, payload)

    return _UiServer((host, port), Handler)


def serve_ui(
    *,
    host: str,
    port: int,
    trace_dir: Path,
    question_runner: QuestionRunner,
    open_browser: bool,
) -> int:
    """Serve the interactive UI until interrupted by the local user."""

    server = create_server(
        host=host,
        port=port,
        trace_dir=trace_dir,
        question_runner=question_runner,
    )
    actual_port = int(server.server_address[1])
    url = f"http://{host}:{actual_port}/"
    print(f"Interactive UI: {url}", file=sys.stderr)
    print("Press Ctrl+C to stop the local server.", file=sys.stderr)
    if open_browser:
        Timer(0.25, webbrowser.open, args=(url,), kwargs={"new": 2}).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("Stopping interactive UI.", file=sys.stderr)
    finally:
        server.server_close()
    return 0
