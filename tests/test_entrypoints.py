from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_powershell_entrypoint_delegates_to_bash_script() -> None:
    wrapper = (PROJECT_ROOT / "run.ps1").read_text(encoding="utf-8")

    assert "$PSScriptRoot" in wrapper
    assert '"./run.sh" @args' in wrapper
    assert "Git\\bin\\bash.exe" in wrapper
    assert '$ErrorActionPreference = "Continue"' in wrapper
    assert "[System.Text.UTF8Encoding]" in wrapper
    assert "exit $exitCode" in wrapper


def test_development_setup_installs_extras_from_project_directory() -> None:
    setup_script = (PROJECT_ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")

    assert 'cd "${PROJECT_DIR}"' in setup_script
    assert 'pip install -e ".[dev]"' in setup_script


def test_demo_script_uses_the_canonical_entrypoint_and_trace_viewer() -> None:
    demo_script = (PROJECT_ROOT / "scripts" / "demo.sh").read_text(encoding="utf-8")

    assert '"${PROJECT_DIR}/run.sh"' in demo_script
    assert "--show-trace" in demo_script
