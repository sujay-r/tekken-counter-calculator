"""Tests for derived category flags."""

from __future__ import annotations

import pytest

from tekken_counter.categories import derive_categories
from tekken_counter.normalize import parse_advantage, parse_block
from tekken_counter.schema import EffectKind, SafetyKind


def test_b1_categories(steve_b1) -> None:
    assert steve_b1.categories.ch_launcher is True
    assert steve_b1.categories.launcher is False
    assert steve_b1.categories.unblockable is False
    assert steve_b1.categories.safety == SafetyKind.SEMI


def test_safety_tri_state() -> None:
    assert derive_categories(
        parse_advantage("+5"),
        parse_advantage("+5"),
        *parse_block("-8"),
        crush=None,
        notes=None,
        tags=None,
    ).safety == SafetyKind.SAFE
    assert derive_categories(
        parse_advantage("+5"),
        parse_advantage("+5"),
        *parse_block("-12"),
        crush=None,
        notes=None,
        tags=None,
    ).safety == SafetyKind.SEMI
    assert derive_categories(
        parse_advantage("+5"),
        parse_advantage("+5"),
        *parse_block("-16"),
        crush=None,
        notes=None,
        tags=None,
    ).safety == SafetyKind.PUNISHABLE


def test_launcher_and_downed_effects() -> None:
    hit = parse_advantage("+18a")
    ch = parse_advantage("+20d")
    cats = derive_categories(hit, ch, *parse_block("-15"), crush=None, notes=None, tags=None)
    assert cats.launcher is True
    assert cats.downed is True
    assert cats.safety == SafetyKind.PUNISHABLE


def test_unblockable_block() -> None:
    cats = derive_categories(
        parse_advantage(""),
        parse_advantage(""),
        *parse_block("!"),
        crush=None,
        notes=None,
        tags=None,
    )
    assert cats.unblockable is True
    assert cats.safety is None


@pytest.mark.parametrize(
    ("crush", "notes", "tags", "high_crush", "low_crush", "powercrush", "homing"),
    [
        ("cs", None, None, True, False, False, False),
        ("js", None, None, False, True, False, False),
        ("pc", None, None, False, False, True, False),
        (None, "homing", None, False, False, False, True),
        (None, None, "hom", False, False, False, True),
        (None, "High Crush", None, True, False, False, False),
        (None, "Power Crush", None, False, False, True, False),
    ],
)
def test_utility_flags_from_crush_and_notes(
    crush: str | None,
    notes: str | None,
    tags: str | None,
    high_crush: bool,
    low_crush: bool,
    powercrush: bool,
    homing: bool,
) -> None:
    cats = derive_categories(
        parse_advantage("+5"),
        parse_advantage("+5"),
        *parse_block("-10"),
        crush=crush,
        notes=notes,
        tags=tags,
    )
    assert cats.high_crush == high_crush
    assert cats.low_crush == low_crush
    assert cats.powercrush == powercrush
    assert cats.homing == homing


def test_stage_break_flags() -> None:
    cats = derive_categories(
        parse_advantage("+5"),
        parse_advantage("+5"),
        *parse_block("-10"),
        crush=None,
        notes="Balcony Break, Floor Break, Heat Burst",
        tags=None,
    )
    assert cats.balcony_break is True
    assert cats.floor_break is True
    assert cats.heat_burst is True
