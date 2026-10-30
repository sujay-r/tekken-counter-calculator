"""Tests for the counter-matching engine."""

from __future__ import annotations

import pytest

from tekken_counter.engine import (
    block_punishers,
    ch_traps,
    hit_level_defense,
    whiff_punishers,
)
from tekken_counter.schema import Move
from tekken_counter.sort import sort_fastest_startup


def _ids(results: list[object]) -> list[str]:
    return [r.id for r in results]


def test_block_punish_minus_13_returns_b1(clean_moves: list[Move]) -> None:
    """US1 hand-check: -13 on block -> Steve b+1 (CH-launcher)."""
    steve = [m for m in clean_moves if m.id.startswith("Steve-")]
    results = block_punishers(steve, block_adv=13)
    ids = _ids(results)
    assert "Steve-b+1" in ids
    b1 = next(r for r in results if r.id == "Steve-b+1")
    assert b1.categories.ch_launcher is True


def test_block_punish_minus_10_returns_1(clean_moves: list[Move]) -> None:
    """US1 hand-check: -10 on block -> Steve 1."""
    steve = [m for m in clean_moves if m.id.startswith("Steve-")]
    results = block_punishers(steve, block_adv=10)
    ids = _ids(results)
    assert "Steve-1" in ids


def test_block_punish_minus_12_returns_2(clean_moves: list[Move]) -> None:
    """US1 hand-check: -12 on block -> Steve 2."""
    steve = [m for m in clean_moves if m.id.startswith("Steve-")]
    results = block_punishers(steve, block_adv=12)
    ids = _ids(results)
    assert "Steve-2" in ids


def test_whiff_punish_returns_fast_tools(clean_moves: list[Move]) -> None:
    """US2: a move with long recovery returns fast Steve tools."""
    steve = [m for m in clean_moves if m.id.startswith("Steve-")]
    results = whiff_punishers(steve, recovery=50, reaction=15)
    ids = _ids(results)
    assert "Steve-1" in ids
    assert "Steve-1+2" in ids
    assert "Steve-f+1+2" in ids


def test_ch_trap_minus_1_vs_i13_followup(clean_moves: list[Move]) -> None:
    """US3: -1 on block + i13 follow-up -> Steve b+1 counter-hits."""
    steve = [m for m in clean_moves if m.id.startswith("Steve-")]
    results = ch_traps(steve, block_adv=-1, opp_followup_startup=13)
    ids = _ids(results)
    assert "Steve-b+1" in ids


def test_ch_trap_strict_inequality_respects_bounds(
    clean_moves: list[Move],
) -> None:
    """CH trap uses strict bounds: S must be strictly inside the window."""
    steve = [m for m in clean_moves if m.id.startswith("Steve-")]
    # A = 1, So = 1 -> window 1 < S < 2; no integer startup fits.
    results = ch_traps(steve, block_adv=-1, opp_followup_startup=1)
    assert _ids(results) == []

    # A = 0 (opponent +0 on block), So = 20 -> window 0 < S < 20.
    # i10 Steve jab should now qualify.
    results = ch_traps(steve, block_adv=0, opp_followup_startup=20)
    assert "Steve-1" in _ids(results)


def test_hit_level_defense_high_move(moves_by_id: dict[str, Move]) -> None:
    """US4: a high f+4 returns WS punishers and a sidestep flag."""
    steve = [m for m in moves_by_id.values() if m.id.startswith("Steve-")]
    opp = moves_by_id["Dragunov-f+4"]
    result = hit_level_defense(opp, steve)
    assert result.high is True
    assert result.sidesteppable is True
    ws_ids = _ids(result.ws_punishers)
    assert "Steve-WS.1" in ws_ids
    assert "Steve-WS.1,2" in ws_ids


def test_hit_level_defense_homing_move_not_sidesteppable(
    moves_by_id: dict[str, Move],
) -> None:
    """A homing move is not flagged as sidesteppable."""
    steve = [m for m in moves_by_id.values() if m.id.startswith("Steve-")]
    opp = moves_by_id["Asuka-f+4"]  # homing
    result = hit_level_defense(opp, steve)
    assert result.sidesteppable is False


def test_sort_fastest_startup_orders_by_startup(clean_moves: list[Move]) -> None:
    steve = [m for m in clean_moves if m.id.startswith("Steve-")]
    results = block_punishers(steve, block_adv=12, sort="fastest_startup")
    startups = [r.startup_min for r in results]
    assert startups == sorted(startups)
