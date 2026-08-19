"""Tests for Cargo ingestion, seed merging, and raw field preservation."""

from __future__ import annotations

from typing import Any

import pytest

from tekken_counter.ingest import deduplicate, load_seed
from tekken_counter.schema import Move


def test_total_count(raw_rows: list[dict[str, Any]]) -> None:
    """US1: the full Cargo dataset is present and within the expected band."""
    count = len(raw_rows)
    assert 6400 <= count <= 6500, f"unexpected Cargo row count: {count}"


def test_unique_ids(raw_rows: list[dict[str, Any]]) -> None:
    ids = [row["id"] for row in raw_rows if row.get("id")]
    assert len(ids) == len(set(ids))
    assert all(ids)


@pytest.mark.parametrize(
    "field",
    ["id", "name", "input", "target", "damage", "startup", "block", "hit", "ch"],
)
def test_required_fields_present(raw_rows: list[dict[str, Any]], field: str) -> None:
    for row in raw_rows:
        assert field in row, f"missing {field} in {row.get('id')}"


def test_seed_loaded() -> None:
    seed = load_seed()
    assert len(seed) == 6113


def test_seed_merge_steve_b1(moves_by_id: dict[str, Move]) -> None:
    """US1 cross-check: seed tags/transitions are attached where ids match."""
    move = moves_by_id["Steve-b+1"]
    assert move.transitions == "FLK"


def test_seed_merge_coverage(clean_moves: list[Move]) -> None:
    """Most Cargo rows matched a seed entry (seed has 6,113 ids with tags/transitions)."""
    merged = [m for m in clean_moves if m.tags is not None or m.transitions is not None]
    assert len(merged) >= 4000


def test_no_dropped_fields(clean_moves: list[Move]) -> None:
    """Every Cargo field is represented in the normalized IR."""
    raw_fields = {
        "raw_target",
        "raw_damage",
        "raw_startup",
        "raw_block",
        "raw_recv",
        "raw_tot",
        "raw_crush",
        "raw_notes",
        "raw_alias",
        "raw_image",
        "raw_video",
        "raw_alt",
    }
    for move in clean_moves:
        missing = raw_fields - set(move.model_dump().keys())
        assert not missing, f"{move.id} missing {missing}"


def test_deduplicate_keeps_most_complete_row() -> None:
    rows = [
        {
            "id": "Steve-1",
            "name": "Jab",
            "input": "1",
            "block": "-1",
        },
        {
            "id": "Steve-1",
            "name": "Jab",
            "input": "1",
            "block": "-1",
            "hit": "+6",
        },
    ]
    result = deduplicate(rows)
    assert len(result) == 1
    assert result[0]["hit"] == "+6"


def test_notes_stripped_of_wiki_markup(clean_moves: list[Move]) -> None:
    for move in clean_moves:
        notes = move.raw_notes or ""
        assert "[[" not in notes
        assert "]]" not in notes
