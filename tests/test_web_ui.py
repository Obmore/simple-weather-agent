from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from weather_agent import web_ui
from weather_agent.web_ui import create_server, public_trace_events


@pytest.fixture
def ui_server(tmp_path: Path) -> Iterator[tuple[str, list[str]]]:
    questions: list[str] = []

    def question_runner(question: str) -> tuple[dict[str, object], int]:
        questions.append(question)
        return (
            {
                "status": "completed",
                "answer": "Current temperature:\n- Budapest: 21.5 degrees Celsius",
                "temperatures": [
                    {
                        "requested_city": "Budapest",
                        "resolved_city": "Budapest, Hungary",
                        "temperature": 21.5,
                        "unit": "degrees Celsius",
                        "observed_at": "2026-07-22T12:00",
                    }
                ],
                "errors": [],
                "run_id": "a" * 32,
                "events": [
                    {
                        "sequence": 1,
                        "event": "run_started",
                        "elapsed_ms": 0.1,
                        "summary": "Agent run started.",
                    }
                ],
            },
            200,
        )

    server = create_server(
        host="127.0.0.1",
        port=0,
        trace_dir=tmp_path,
        question_runner=question_runner,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}", questions
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_interactive_ui_serves_local_assets_with_security_headers(
    ui_server: tuple[str, list[str]],
) -> None:
    base_url, _ = ui_server

    response = httpx.get(base_url, timeout=5)

    assert response.status_code == 200
    assert "Interactive weather agent" in response.text
    assert "Content-Security-Policy" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "https://" not in response.text

    script = httpx.get(f"{base_url}/app.js", timeout=5)
    assert script.status_code == 200
    assert "fetch" in script.text

    health = httpx.get(f"{base_url}/api/health", timeout=5)
    assert health.json() == {"status": "ok"}


def test_interactive_ui_runs_question_and_returns_structured_trace(
    ui_server: tuple[str, list[str]],
) -> None:
    base_url, questions = ui_server

    response = httpx.post(
        f"{base_url}/api/ask",
        json={"question": "What is the current temperature in Budapest?"},
        timeout=5,
    )

    assert response.status_code == 200
    payload = response.json()
    assert questions == ["What is the current temperature in Budapest?"]
    assert payload["temperatures"][0]["temperature"] == 21.5
    assert payload["events"][0]["event"] == "run_started"


def test_interactive_ui_rejects_invalid_requests(
    ui_server: tuple[str, list[str]],
) -> None:
    base_url, questions = ui_server

    missing = httpx.post(f"{base_url}/api/ask", json={}, timeout=5)
    wrong_type = httpx.post(f"{base_url}/api/ask", content="not-json", timeout=5)
    too_long = httpx.post(f"{base_url}/api/ask", json={"question": "x" * 2001}, timeout=5)
    unknown_post = httpx.post(f"{base_url}/missing", json={}, timeout=5)
    unknown = httpx.get(f"{base_url}/missing", timeout=5)

    assert missing.status_code == 400
    assert wrong_type.status_code == 400
    assert too_long.status_code == 400
    assert unknown_post.status_code == 404
    assert unknown.status_code == 404
    assert questions == []


def test_trace_download_is_limited_to_valid_run_ids(
    ui_server: tuple[str, list[str]], tmp_path: Path
) -> None:
    base_url, _ = ui_server
    run_id = "b" * 32
    trace = tmp_path / f"{run_id}.jsonl"
    trace.write_text(json.dumps({"event": "run_finished"}) + "\n", encoding="utf-8")

    downloaded = httpx.get(f"{base_url}/api/traces/{run_id}", timeout=5)
    traversal = httpx.get(f"{base_url}/api/traces/..%2F.env", timeout=5)

    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("application/x-ndjson")
    assert "attachment" in downloaded.headers["content-disposition"]
    assert traversal.status_code == 404


def test_public_trace_events_exposes_only_safe_structured_fields() -> None:
    records = [
        {
            "sequence": 2,
            "event": "tool_call_completed",
            "elapsed_ms": 12.5,
            "data": {
                "summary": "Temperature resolved.",
                "tool": "get_current_temperatures",
                "result": {"city": "Budapest", "temperature": 21.5},
                "provider_payload": {"must": "not leak"},
            },
        },
        {"data": "malformed"},
    ]

    public = public_trace_events(records)

    assert public[0] == {
        "sequence": 2,
        "event": "tool_call_completed",
        "elapsed_ms": 12.5,
        "summary": "Temperature resolved.",
        "details": {
            "tool": "get_current_temperatures",
            "result": {"city": "Budapest", "temperature": 21.5},
        },
    }
    assert "provider_payload" not in public[0]["details"]
    assert public[1]["event"] == "unknown"


def test_server_rejects_non_loopback_bindings(tmp_path: Path) -> None:
    def runner(_: str) -> tuple[dict[str, object], int]:
        return {"status": "completed"}, 200

    with pytest.raises(ValueError, match=r"only to 127\.0\.0\.1"):
        create_server(host="0.0.0.0", port=8765, trace_dir=tmp_path, question_runner=runner)
    with pytest.raises(ValueError, match="between 0 and 65535"):
        create_server(host="127.0.0.1", port=65536, trace_dir=tmp_path, question_runner=runner)


def test_serve_ui_closes_server_after_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeServer:
        server_address = ("127.0.0.1", 9123)
        closed = False

        def serve_forever(self, *, poll_interval: float) -> None:
            assert poll_interval == 0.25
            raise KeyboardInterrupt

        def server_close(self) -> None:
            self.closed = True

    server = FakeServer()
    monkeypatch.setattr(web_ui, "create_server", lambda **_: server)

    assert (
        web_ui.serve_ui(
            host="127.0.0.1",
            port=9123,
            trace_dir=tmp_path,
            question_runner=lambda _: ({}, 200),
            open_browser=False,
        )
        == 0
    )

    assert server.closed is True
    assert "http://127.0.0.1:9123/" in capsys.readouterr().err
