"""Packaging contracts for the one-command demo and the final report."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path("/repo")


def _read(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


def test_makefile_exposes_demo_target() -> None:
    makefile = _read("Makefile")
    phony = next(line for line in makefile.splitlines() if line.startswith(".PHONY:"))
    assert "demo" in phony.split()
    assert "demo:" in makefile
    assert "scripts/demo.sh" in makefile


def test_demo_script_is_executable_and_seeds_without_printing_passwords() -> None:
    script_path = REPO / "scripts/demo.sh"
    script = script_path.read_text(encoding="utf-8")
    assert os.access(script_path, os.X_OK)
    assert "alembic upgrade head" in script
    assert "app.scripts.seed_dev" in script
    assert "app.scripts.seed_demo" in script
    assert "DEMO_ADMIN_1_PASSWORD" in script
    assert "DEMO_ADMIN_2_PASSWORD" in script
    assert "demo-admin-1@example.test" in script
    assert "demo-admin-2@example.test" in script
    assert "value not printed" in script
    for line in script.splitlines():
        if "echo" in line and "PASSWORD" in line:
            assert "$DEMO_ADMIN_1_PASSWORD" not in line
            assert "$DEMO_ADMIN_2_PASSWORD" not in line


def test_makefile_does_not_hardcode_the_compose_network() -> None:
    makefile = _read("Makefile")
    assert "phishing-attack-simulator_dev" not in makefile
    assert "docker inspect -f" in makefile


def test_readme_has_demo_script_architecture_and_commands() -> None:
    readme = _read("README.md").lower()
    for phrase in (
        "make demo",
        "make lint",
        "make test",
        "mailpit",
        "awareness",
        "quiz",
        "report",
        "analyzer",
        "```mermaid",
        "known limitations",
    ):
        assert phrase in readme


def test_readme_lists_screenshot_pages() -> None:
    readme = _read("README.md")
    for route in (
        "/login",
        "/signup",
        "/learn/<token>",
        "/learn/<token>/quiz",
        "/t/<token>",
        "/campaigns",
        "/templates",
        "/groups",
        "/reports",
        "/analyzer",
        "/settings",
        "/settings/audit",
    ):
        assert route in readme


def test_final_report_outline_has_required_sections() -> None:
    outline = _read("docs/final-report-outline.md")
    lowered = outline.lower()
    for heading in (
        "problem",
        "ethics and authorization",
        "att&ck",
        "hci methods",
        "detection method",
        "test summary",
        "security measures",
        "limitations and future work",
    ):
        assert heading in lowered
    for term in ("csp", "csrf", "rate limit", "audit log", "append-only"):
        assert term in lowered
    for term in ("password reset", "ml classifier", "usability study"):
        assert term in lowered


def test_env_example_documents_demo_password_variables() -> None:
    env_example = _read(".env.example")
    assert "DEMO_ADMIN_1_PASSWORD=" in env_example
    assert "DEMO_ADMIN_2_PASSWORD=" in env_example
