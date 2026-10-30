"""Unit tests for the frame-data normalization parsers."""

from __future__ import annotations

import pytest

from tekken_counter.normalize import (
    clean_notes,
    infer_safety,
    parse_advantage,
    parse_block,
    parse_damage,
    parse_hit_levels,
    parse_recovery,
    parse_startup,
    strip_wiki_markup,
)
from tekken_counter.schema import (
    EffectKind,
    FrameAdvantage,
    HitLevel,
    SafetyKind,
    StartupRange,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("i15", [StartupRange(min=15, max=15)]),
        ("i13-14", [StartupRange(min=13, max=14)]),
        ("i15~16", [StartupRange(min=15, max=16)]),
        ("i10, i15", [StartupRange(min=10, max=10), StartupRange(min=15, max=15)]),
        ("i55-i130", [StartupRange(min=55, max=130)]),
        ("i11(-14)", [StartupRange(min=11, max=11)]),
        ("i17-18/i19-20", [StartupRange(min=17, max=18), StartupRange(min=19, max=20)]),
        ("i46/i47", [StartupRange(min=46, max=47)]),
        (".i26~27", [StartupRange(min=26, max=27)]),
        ("i20 pc7", [StartupRange(min=20, max=20)]),
        ("i30?,i5?,i5?,i5?", [StartupRange(min=30, max=30)] + [StartupRange(min=5, max=5)] * 3),
        ("", []),
        (None, []),
    ],
)
def test_parse_startup(raw: str | None, expected: list[StartupRange]) -> None:
    assert parse_startup(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5", [5]),
        (",7", [7]),
        ("7,21", [7, 21]),
        ("[12;12]", [12, 12]),
        ("50 (28)", [50]),
        ("25?", [25]),
        ("10-75", [75]),
        ("10-15,3-5,42-60", [15, 5, 60]),
        ("20,22 (15) / 25 (17)", [20, 22, 25]),
        ("55+", [55]),
        ("65(70)", [65]),
        ("[5]", [5]),
        ("-", []),
        ("", []),
        (None, []),
    ],
)
def test_parse_damage(raw: str | None, expected: list[int]) -> None:
    assert parse_damage(raw) == expected


@pytest.mark.parametrize(
    ("raw", "frames", "effect", "tech_window"),
    [
        ("+18a (+11)", 18, EffectKind.LAUNCHER, 11),
        ("+13 +59a", 13, None, None),
        ("+2c", 2, EffectKind.CROUCH, None),
        ("-14", -14, None, None),
        ("!", None, None, None),
        ("", None, None, None),
        (None, None, None, None),
    ],
)
def test_parse_advantage(
    raw: str | None, frames: int | None, effect: EffectKind | None, tech_window: int | None
) -> None:
    adv = parse_advantage(raw)
    assert adv.frames == frames
    assert adv.effect == effect
    assert adv.tech_window == tech_window
    assert adv.raw == (raw or "")


def test_parse_advantage_extra_states() -> None:
    adv = parse_advantage("+13 +59a")
    assert len(adv.extra_states) == 1
    extra = adv.extra_states[0]
    assert extra.frames == 59
    assert extra.effect == EffectKind.LAUNCHER


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("h", [HitLevel.HIGH]),
        (",h", [HitLevel.HIGH]),
        ("m,m", [HitLevel.MID, HitLevel.MID]),
        ("L", [HitLevel.L]),
        ("M", [HitLevel.M]),
        ("H", [HitLevel.H]),
        ("sl", [HitLevel.LOW]),
        ("SL", [HitLevel.LOW]),
        ("sll,h", [HitLevel.LOW, HitLevel.HIGH]),
        ("ub(m)", [HitLevel.MID]),
        ("ub(l)", [HitLevel.LOW]),
        ("ub!(m)", [HitLevel.MID]),
        ("m (t)", [HitLevel.THROW]),
        ("special", [HitLevel.SMA]),
        ("r(m)", [HitLevel.MID]),
    ],
)
def test_parse_hit_levels(raw: str | None, expected: list[HitLevel]) -> None:
    assert parse_hit_levels(raw) == expected


@pytest.mark.parametrize(
    ("raw", "frames", "unblockable"),
    [
        ("-14", -14, False),
        ("+6", 6, False),
        ("", None, True),
        ("!", None, True),
        ("[[Link|-13]]", -13, False),
    ],
)
def test_parse_block(raw: str | None, frames: int | None, unblockable: bool) -> None:
    assert parse_block(raw) == (frames, unblockable)


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        (-8, SafetyKind.SAFE),
        (-9, SafetyKind.SAFE),
        (-10, SafetyKind.SEMI),
        (-14, SafetyKind.SEMI),
        (-15, SafetyKind.PUNISHABLE),
        (-20, SafetyKind.PUNISHABLE),
        (None, None),
    ],
)
def test_infer_safety(block: int | None, expected: SafetyKind | None) -> None:
    assert infer_safety(block) == expected


def test_strip_wiki_markup() -> None:
    assert strip_wiki_markup("[[Steve_combos#Staples|+61a]]") == "+61a"
    assert strip_wiki_markup("&lt;div&gt;text&lt;/div&gt;") == "text"
    assert strip_wiki_markup("  a  b  ") == "a b"


def test_clean_notes() -> None:
    assert clean_notes("[[Page|note]]") == "note"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("r31", 31),
        ("r31?", 31),
        ("r24 FC", 24),
        ("FC", None),
        ("r", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_recovery(raw: str | None, expected: int | None) -> None:
    assert parse_recovery(raw) == expected


def test_b1_ch_launcher(steve_b1) -> None:
    """Hand-check from Scope Document §7."""
    assert steve_b1.input == "b+1"
    # Rebaselined 2026-10-30: upstream wavu.wiki now reports startup i13~14.
    assert steve_b1.startup == [StartupRange(min=13, max=14)]
    assert steve_b1.block == -14
    assert steve_b1.ch.frames == 61
    assert steve_b1.ch.effect == EffectKind.LAUNCHER
    assert steve_b1.categories.ch_launcher is True
    assert steve_b1.categories.safety == SafetyKind.SEMI
