"""Precompute Steve lookup tables for the static frontend."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tekken_counter.engine import _to_result
from tekken_counter.schema import Move
from tekken_counter.sort import sort_recommended

logger = logging.getLogger(__name__)

DEFAULT_REACTION = 15
PUNISH_RANGE = range(10, 31)


def _compact_move(move: Move) -> dict[str, Any]:
    """Serialize a Steve move into the compact detail record used by the UI."""
    cat = move.categories
    return {
        "input": move.input,
        "name": move.name,
        "startup_min": move.startup[0].min if move.startup else None,
        "startup_max": move.startup[0].max if move.startup else None,
        "damage": sum(move.damage) if move.damage else 0,
        "block": move.block,
        "recovery": move.recovery,
        "launcher": cat.launcher,
        "ch_launcher": cat.ch_launcher,
        "downed": cat.downed,
        "stagger": cat.stagger,
        "wall_crush": cat.wall_crush,
        "guard_recover": cat.guard_recover,
        "safety": cat.safety.value if cat.safety else None,
        "homing": cat.homing,
        "high_crush": cat.high_crush,
        "low_crush": cat.low_crush,
        "powercrush": cat.powercrush,
    }


def _id_sorted_by_startup(moves: list[Move]) -> list[str]:
    """Return move ids sorted by minimum startup, then input for stability."""
    return [
        m.id
        for m in sorted(
            moves,
            key=lambda m: (
                m.startup[0].min if m.startup else 999,
                m.input,
            ),
        )
    ]


def _filter_by_flag(moves: list[Move], flag: str) -> list[Move]:
    """Return moves whose category flag is truthy."""
    return [m for m in moves if getattr(m.categories, flag)]


def build_steve_index(
    moves: list[Move],
    *,
    default_reaction: int = DEFAULT_REACTION,
) -> dict[str, Any]:
    """Build the static lookup index for Steve counters.

    Args:
        moves: Full normalized movelist (all characters). Steve moves are
            filtered internally.
        default_reaction: Default reaction-time constant for whiff punish.

    Returns:
        JSON-serializable dict containing move details, punish tables,
        category lists, and whiff lookup.
    """
    steve_moves = [m for m in moves if m.id.startswith("Steve-")]
    logger.info("Building Steve index from %d Steve moves", len(steve_moves))

    details = {m.id: _compact_move(m) for m in steve_moves}

    # Pre-sorted result list for filtering.
    all_results = sort_recommended([_to_result(m, "block_punish") for m in steve_moves])

    punish: dict[str, list[str]] = {}
    for n in PUNISH_RANGE:
        punish[str(n)] = [r.id for r in all_results if r.startup_min <= n]

    launchers = _id_sorted_by_startup(_filter_by_flag(steve_moves, "launcher"))
    ch_launchers = _id_sorted_by_startup(_filter_by_flag(steve_moves, "ch_launcher"))
    downed = _id_sorted_by_startup(_filter_by_flag(steve_moves, "downed"))
    stagger = _id_sorted_by_startup(_filter_by_flag(steve_moves, "stagger"))
    wall_crush = _id_sorted_by_startup(_filter_by_flag(steve_moves, "wall_crush"))

    ws_punishers = _id_sorted_by_startup([m for m in steve_moves if m.input.startswith("WS.")])

    by_startup: dict[int, list[str]] = {}
    for m in steve_moves:
        key = m.startup[0].min if m.startup else None
        if key is None:
            continue
        by_startup.setdefault(key, []).append(m.id)
    # Sort each bucket by Recommended for stable output.
    by_startup = {
        k: [r.id for r in sort_recommended([_to_result(m, "block_punish") for m in steve_moves if m.startup and m.startup[0].min == k])]
        for k, _ in sorted(by_startup.items())
    }

    # Whiff table keyed by numeric recovery values seen anywhere in the dataset.
    recoveries = sorted(
        {m.recovery for m in moves if m.recovery is not None},
        key=lambda r: (r is None, r or 0),
    )
    whiff: dict[str, list[str]] = {}
    for recovery in recoveries:
        threshold = recovery - default_reaction
        results = sort_recommended(
            [_to_result(m, "whiff_punish") for m in steve_moves if m.startup and m.startup[0].min <= threshold]
        )
        whiff[str(recovery)] = [r.id for r in results]

    return {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "move_count": len(steve_moves),
            "default_reaction": default_reaction,
        },
        "moves": details,
        "punish": punish,
        "launchers": launchers,
        "ch_launchers": ch_launchers,
        "downed": downed,
        "stagger": stagger,
        "wall_crush": wall_crush,
        "ws_punishers": ws_punishers,
        "by_startup": {str(k): v for k, v in by_startup.items()},
        "whiff": whiff,
    }


def write_index(index: dict[str, Any], path: Path) -> None:
    """Write the index to JSON deterministically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False, sort_keys=True)
    logger.info("Wrote Steve index to %s", path)
