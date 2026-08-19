"""Tests for string-move parent linkage."""

from __future__ import annotations

from typing import Any

import pytest

from tekken_counter.schema import HitLevel, StartupRange
from tekken_counter.strings import _resolve_parent_chain, link_strings


def test_steve_1_1_2_linkage(moves_by_id: dict[str, Any]) -> None:
    """US3: parent chain expands into full per-hit lists."""
    move = moves_by_id["Steve-1,1,2"]
    assert move.input == "1,1,2"
    assert move.target == [HitLevel.HIGH, HitLevel.HIGH, HitLevel.HIGH]
    assert move.damage == [5, 7, 13]
    assert move.startup == [
        StartupRange(min=10, max=10),
        StartupRange(min=15, max=15),
        StartupRange(min=13, max=14),
    ]


def test_link_strings_preserves_root_rows() -> None:
    rows = [
        {"id": "Steve-1", "input": "1", "parent": None, "target": "h", "damage": "5", "startup": "i10"},
        {"id": "Steve-1,2", "input": ",2", "parent": "Steve-1", "target": "h", "damage": "10", "startup": "i10"},
    ]
    linked = link_strings(rows)
    by_id = {r["id"]: r for r in linked}
    assert by_id["Steve-1,2"]["linked_input"] == "1,2"
    assert by_id["Steve-1,2"]["linked_damage"] == [5, 10]


def test_parent_cycle_handled() -> None:
    rows = [
        {"id": "A", "input": "1", "parent": "B", "target": "h", "damage": "5", "startup": "i10"},
        {"id": "B", "input": ",2", "parent": "A", "target": "h", "damage": "7", "startup": "i15"},
    ]
    chain = _resolve_parent_chain(rows[0], {r["id"]: r for r in rows}, set())
    # Cycle should stop before infinite loop; at least the starting row is present.
    assert any(node["id"] == "A" for node in chain)


def test_missing_parent_handled() -> None:
    rows = [
        {"id": "Steve-1,2", "input": ",2", "parent": "Missing", "target": "h", "damage": "10", "startup": "i10"},
    ]
    linked = link_strings(rows)
    assert linked[0]["linked_input"] == ",2"
