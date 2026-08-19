"""Tests for the ingest-to-IR assembly pipeline."""

from __future__ import annotations

from tekken_counter.pipeline import build_moves
from tekken_counter.schema import EffectKind, HitLevel, StartupRange


def test_build_moves_full_row() -> None:
    rows = [
        {
            "id": "Steve-1",
            "name": "Jab",
            "input": "1",
            "parent": None,
            "target": "h",
            "damage": "5",
            "startup": "i10",
            "recv": "r20",
            "tot": None,
            "crush": None,
            "block": "-1",
            "hit": "+6",
            "ch": "+8",
            "notes": "* Homing",
            "alias": None,
            "image": None,
            "video": None,
            "alt": None,
            "tags": None,
            "transitions": None,
        }
    ]
    moves = build_moves(rows)
    assert len(moves) == 1
    move = moves[0]
    assert move.input == "1"
    assert move.target == [HitLevel.HIGH]
    assert move.damage == [5]
    assert move.startup == [StartupRange(min=10, max=10)]
    assert move.block == -1
    assert move.hit.frames == 6
    assert move.ch.frames == 8
    assert move.raw_block == "-1"
    assert move.categories.homing is True


def test_build_moves_ch_falls_back_to_hit() -> None:
    rows = [
        {
            "id": "Steve-1",
            "name": "Jab",
            "input": "1",
            "parent": None,
            "target": "h",
            "damage": "5",
            "startup": "i10",
            "recv": None,
            "tot": None,
            "crush": None,
            "block": "-1",
            "hit": "+6",
            "ch": None,
            "notes": None,
            "alias": None,
            "image": None,
            "video": None,
            "alt": None,
            "tags": None,
            "transitions": None,
        }
    ]
    moves = build_moves(rows)
    assert moves[0].ch.frames == 6
