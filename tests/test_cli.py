"""Tests for the CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tekken_counter.cli import main
from tekken_counter.schema import Categories, FrameAdvantage, Move


def _make_move(move_id: str) -> Move:
    return Move(
        id=move_id,
        name="Jab",
        input="1",
        hit=FrameAdvantage(raw="+5"),
        ch=FrameAdvantage(raw="+5"),
        categories=Categories(),
    )


def test_cli_writes_output(monkeypatch, tmp_path: Path) -> None:
    """The CLI orchestrates ingest → normalize → JSON output."""
    output = tmp_path / "moves.json"

    def fake_fetch_all(*, seed_path: Any = None) -> list[dict[str, Any]]:
        return [{"id": "Steve-1", "name": "Jab", "input": "1", "hit": "+5", "ch": "+5"}]

    monkeypatch.setattr("tekken_counter.cli.fetch_all", fake_fetch_all)
    monkeypatch.setattr(
        "tekken_counter.cli.build_moves",
        lambda rows: [_make_move("Steve-1")],
    )

    assert main(["--output", str(output)]) == 0
    assert output.exists()
    data = output.read_text(encoding="utf-8")
    assert "Steve-1" in data
