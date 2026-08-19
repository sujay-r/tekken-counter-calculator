"""Derive category flags from normalized move fields and raw notes/tags."""

from __future__ import annotations

import re

from tekken_counter.normalize import infer_safety, iter_all_states
from tekken_counter.schema import Categories, EffectKind, FrameAdvantage, Move


def derive_categories(
    hit: FrameAdvantage,
    ch: FrameAdvantage,
    block: int | None,
    block_unblockable: bool,
    crush: str | None,
    notes: str | None,
    tags: str | None,
) -> Categories:
    """Compute the full category flag set for a move."""
    notes_lower = (notes or "").lower()
    tags_lower = (tags or "").lower()
    crush_lower = (crush or "").lower()

    launcher = _has_effect(hit, EffectKind.LAUNCHER)
    ch_launcher = _has_effect(ch, EffectKind.LAUNCHER)
    downed = _any_effect([hit, ch], EffectKind.DOWNED)
    stagger = _any_effect([hit, ch], EffectKind.STAGGER)
    wall_crush = _any_effect([hit, ch], EffectKind.WALL_CRUSH)
    guard_recover = _any_effect([hit, ch], EffectKind.GUARD_RECOVER)
    crouch = _any_effect([hit, ch], EffectKind.CROUCH)
    back_turned = _any_effect([hit, ch], EffectKind.BACK_TURNED)

    safety = infer_safety(block)

    high_crush = bool(re.search(r"\bcs", crush_lower)) or "high crush" in notes_lower
    low_crush = bool(re.search(r"\bjs", crush_lower)) or "low crush" in notes_lower
    homing = bool(re.search(r"\bhom\b", tags_lower)) or "homing" in notes_lower
    powercrush = bool(re.search(r"\bpc", crush_lower)) or "power crush" in notes_lower

    balcony_break = "balcony break" in notes_lower
    floor_break = "floor break" in notes_lower
    heat_burst = "heat burst" in notes_lower or "hb" in tags_lower.split()

    return Categories(
        launcher=launcher,
        ch_launcher=ch_launcher,
        downed=downed,
        stagger=stagger,
        wall_crush=wall_crush,
        guard_recover=guard_recover,
        crouch=crouch,
        back_turned=back_turned,
        safety=safety,
        unblockable=block_unblockable,
        high_crush=high_crush,
        low_crush=low_crush,
        homing=homing,
        powercrush=powercrush,
        balcony_break=balcony_break,
        floor_break=floor_break,
        heat_burst=heat_burst,
    )


def _has_effect(adv: FrameAdvantage, effect: EffectKind) -> bool:
    """Check whether the primary or any extra state has the given effect."""
    for state in iter_all_states(adv):
        if state.effect == effect:
            return True
    return False


def _any_effect(advs: list[FrameAdvantage], effect: EffectKind) -> bool:
    """Check any advantage structure for the given effect."""
    return any(_has_effect(adv, effect) for adv in advs)


def categorize(move: Move) -> Move:
    """Re-derive categories on an already-normalized move (used in tests)."""
    return move.model_copy(
        update={
            "categories": derive_categories(
                hit=move.hit,
                ch=move.ch,
                block=move.block,
                block_unblockable=move.block_unblockable,
                crush=move.raw_crush,
                notes=move.raw_notes,
                tags=move.tags,
            )
        }
    )
