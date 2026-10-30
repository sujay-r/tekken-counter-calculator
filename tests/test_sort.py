"""Tests for the locked sort heuristics."""

from __future__ import annotations

import pytest

from tekken_counter.schema import Categories
from tekken_counter.sort import MatchResult, sort_fastest_startup, sort_max_damage, sort_recommended


def _make_result(
    move_id: str,
    *,
    input: str = "1",
    startup: int = 10,
    damage: int = 10,
    launcher: bool = False,
    ch_launcher: bool = False,
    downed: bool = False,
    stagger: bool = False,
) -> MatchResult:
    return MatchResult(
        id=move_id,
        input=input,
        name=move_id,
        startup_min=startup,
        startup_max=startup,
        damage=damage,
        categories=Categories(
            launcher=launcher,
            ch_launcher=ch_launcher,
            downed=downed,
            stagger=stagger,
        ),
        scenario="block_punish",
    )


def test_sort_recommended_priorities() -> None:
    plain = _make_result("plain", input="1", damage=30, startup=10)
    ch = _make_result("ch", input="b+1", damage=10, startup=13, ch_launcher=True)
    launcher = _make_result("launcher", input="f+2,1", damage=10, startup=15, launcher=True)
    downed = _make_result("downed", input="d+2", damage=20, startup=16, downed=True)
    results = sort_recommended([plain, ch, launcher, downed])
    assert [r.id for r in results] == ["launcher", "ch", "downed", "plain"]


def test_sort_recommended_tie_breaks_by_damage_then_startup() -> None:
    a = _make_result("a", input="a", damage=20, startup=12)
    b = _make_result("b", input="b", damage=20, startup=10)
    c = _make_result("c", input="c", damage=30, startup=15)
    results = sort_recommended([a, b, c])
    assert [r.id for r in results] == ["c", "b", "a"]


def test_sort_max_damage_priorities() -> None:
    high = _make_result("high", input="high", damage=50, startup=20)
    launcher = _make_result("launcher", input="launcher", damage=40, startup=15, launcher=True)
    low = _make_result("low", input="low", damage=30, startup=10)
    results = sort_max_damage([high, launcher, low])
    assert [r.id for r in results] == ["high", "launcher", "low"]


def test_sort_fastest_startup_priorities() -> None:
    slow = _make_result("slow", input="slow", damage=30, startup=15)
    fast = _make_result("fast", input="fast", damage=10, startup=10)
    mid = _make_result("mid", input="mid", damage=20, startup=12)
    results = sort_fastest_startup([slow, fast, mid])
    assert [r.id for r in results] == ["fast", "mid", "slow"]
