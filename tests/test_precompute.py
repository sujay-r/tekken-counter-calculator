"""Tests for the Steve index precompute builder."""

from __future__ import annotations

import json
from pathlib import Path

from tekken_counter.precompute import build_steve_index, write_index
from tekken_counter.schema import Move


def test_build_index_structure(clean_moves: list[Move]) -> None:
    """The generated index contains all required lookup tables."""
    index = build_steve_index(clean_moves)
    assert "meta" in index
    assert "moves" in index
    assert "punish" in index
    assert "launchers" in index
    assert "ch_launchers" in index
    assert "downed" in index
    assert "stagger" in index
    assert "wall_crush" in index
    assert "ws_punishers" in index
    assert "by_startup" in index
    assert "whiff" in index

    assert index["meta"]["default_reaction"] == 15
    assert index["meta"]["move_count"] == len(
        [m for m in clean_moves if m.id.startswith("Steve-")]
    )


def test_punish_13_contains_b1(clean_moves: list[Move]) -> None:
    index = build_steve_index(clean_moves)
    assert "Steve-b+1" in index["punish"]["13"]


def test_ws_punishers_contain_ws_moves(clean_moves: list[Move]) -> None:
    index = build_steve_index(clean_moves)
    assert "Steve-WS.1" in index["ws_punishers"]
    assert "Steve-WS.1,2" in index["ws_punishers"]


def test_index_json_is_deterministic(clean_moves: list[Move], tmp_path: Path) -> None:
    """Writing the same index twice yields byte-identical output."""
    index = build_steve_index(clean_moves)
    path1 = tmp_path / "index1.json"
    path2 = tmp_path / "index2.json"
    write_index(index, path1)
    write_index(index, path2)
    assert path1.read_text(encoding="utf-8") == path2.read_text(encoding="utf-8")


def test_written_index_loads(clean_moves: list[Move], tmp_path: Path) -> None:
    index = build_steve_index(clean_moves)
    path = tmp_path / "steve_index.json"
    write_index(index, path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["meta"]["move_count"] == index["meta"]["move_count"]
