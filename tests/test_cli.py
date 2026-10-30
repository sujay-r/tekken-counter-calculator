"""Tests for the CLI entry point."""

from __future__ import annotations

import json
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

    assert main(["ingest", "--output", str(output)]) == 0
    assert output.exists()


def test_cli_precompute_command(clean_moves, tmp_path: Path) -> None:
    """The precompute subcommand builds steve_index.json."""
    clean_output = tmp_path / "moves.clean.json"
    clean_output.write_text(
        json.dumps([m.model_dump(mode="json") for m in clean_moves]), encoding="utf-8"
    )
    index_output = tmp_path / "steve_index.json"

    assert main(["precompute", "--input", str(clean_output), "--output", str(index_output)]) == 0
    assert index_output.exists()
    data = json.loads(index_output.read_text(encoding="utf-8"))
    assert "punish" in data
    assert "Steve-b+1" in data["moves"]


def test_cli_engine_test_block_command(clean_moves, tmp_path: Path, capsys) -> None:
    """The engine-test subcommand prints block punishers."""
    clean_output = tmp_path / "moves.clean.json"
    clean_output.write_text(
        json.dumps([m.model_dump(mode="json") for m in clean_moves]), encoding="utf-8"
    )
    assert main(["engine-test", "--input", str(clean_output), "--block", "-13"]) == 0
    captured = capsys.readouterr()
    assert "Block punishers" in captured.out
    assert "FLK.1,1,1,2" in captured.out


def test_cli_engine_test_whiff_command(clean_moves, tmp_path: Path, capsys) -> None:
    clean_output = tmp_path / "moves.clean.json"
    clean_output.write_text(
        json.dumps([m.model_dump(mode="json") for m in clean_moves]), encoding="utf-8"
    )
    assert main(["engine-test", "--input", str(clean_output), "--recovery", "50"]) == 0
    captured = capsys.readouterr()
    assert "Whiff punishers" in captured.out


def test_cli_engine_test_ch_trap_command(clean_moves, tmp_path: Path, capsys) -> None:
    clean_output = tmp_path / "moves.clean.json"
    clean_output.write_text(
        json.dumps([m.model_dump(mode="json") for m in clean_moves]), encoding="utf-8"
    )
    assert main(
        ["engine-test", "--input", str(clean_output), "--block", "-1", "--followup", "13"]
    ) == 0
    captured = capsys.readouterr()
    assert "CH traps" in captured.out


def test_cli_engine_test_hit_level_command(clean_moves, tmp_path: Path, capsys) -> None:
    clean_output = tmp_path / "moves.clean.json"
    clean_output.write_text(
        json.dumps([m.model_dump(mode="json") for m in clean_moves]), encoding="utf-8"
    )
    assert main(
        ["engine-test", "--input", str(clean_output), "--move-id", "Dragunov-f+4"]
    ) == 0
    captured = capsys.readouterr()
    assert "Hit-level defense" in captured.out
    assert "WS.1" in captured.out
