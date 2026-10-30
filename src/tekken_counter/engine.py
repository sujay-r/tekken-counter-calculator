"""Counter-matching engine: block punish, whiff punish, CH traps, hit-level defense."""

from __future__ import annotations

from dataclasses import dataclass

from tekken_counter.schema import Categories, HitLevel, Move
from tekken_counter.sort import MatchResult, sort_results


@dataclass(frozen=True, slots=True)
class HitLevelResult:
    """Result of the hit-level defense analysis."""

    high: bool
    sidesteppable: bool
    ws_punishers: list[MatchResult]


def _to_result(move: Move, scenario: str) -> MatchResult:
    """Build a MatchResult from a Steve move."""
    return MatchResult(
        id=move.id,
        input=move.input,
        name=move.name,
        startup_min=move.startup[0].min if move.startup else 999,
        startup_max=move.startup[0].max if move.startup else 999,
        damage=sum(move.damage) if move.damage else 0,
        categories=move.categories,
        scenario=scenario,
    )


def _first_startup(move: Move) -> int:
    """Minimum startup frames, or a very large value if unknown."""
    return move.startup[0].min if move.startup else 999


def block_punishers(
    steve_moves: list[Move],
    block_adv: int,
    sort: str = "recommended",
) -> list[MatchResult]:
    """Return Steve moves fast enough to punish at the given defender advantage.

    Args:
        steve_moves: Steve's normalized movelist.
        block_adv: Defender frame advantage after blocking (``-opponent.block``).
        sort: ``recommended`` (default), ``max_damage``, or ``fastest_startup``.
    """
    results = [
        _to_result(m, "block_punish")
        for m in steve_moves
        if _first_startup(m) <= block_adv
    ]
    return sort_results(results, sort)


def whiff_punishers(
    steve_moves: list[Move],
    recovery: int | None,
    reaction: int = 15,
    sort: str = "recommended",
) -> list[MatchResult]:
    """Return Steve moves fast enough to punish a whiff.

    Args:
        steve_moves: Steve's normalized movelist.
        recovery: Opponent move whiff recovery in frames.
        reaction: User reaction time in frames (default 15).
        sort: Sort heuristic name.
    """
    if recovery is None:
        return []
    threshold = recovery - reaction
    results = [
        _to_result(m, "whiff_punish")
        for m in steve_moves
        if _first_startup(m) <= threshold
    ]
    return sort_results(results, sort)


def ch_traps(
    steve_moves: list[Move],
    block_adv: int,
    opp_followup_startup: int,
    sort: str = "recommended",
) -> list[MatchResult]:
    """Return Steve CH tools that counter-hit the opponent's follow-up.

    After blocking an opponent move, defender advantage ``A = -block_adv``.
    A Steve CH tool with startup ``S`` counter-hits a follow-up with startup
    ``So`` iff ``A < S < A + So``.

    Args:
        steve_moves: Steve's normalized movelist.
        block_adv: Opponent's block advantage (negative when punishable).
        opp_followup_startup: Startup of the opponent's likely follow-up.
        sort: Sort heuristic name.
    """
    a = -block_adv
    results: list[MatchResult] = []
    for m in steve_moves:
        s = _first_startup(m)
        if a < s < a + opp_followup_startup:
            results.append(_to_result(m, "ch_trap"))
    return sort_results(results, sort)


def hit_level_defense(
    opp_move: Move,
    steve_moves: list[Move],
    sort: str = "recommended",
) -> HitLevelResult:
    """Analyze a single opponent move for duck/sidestep opportunities.

    Args:
        opp_move: The opponent move being queried.
        steve_moves: Steve's normalized movelist.
        sort: Sort heuristic for the WS punisher list.

    Returns:
        ``HitLevelResult`` with ``high``, ``sidesteppable``, and WS punishers.
    """
    high = HitLevel.HIGH in opp_move.target
    sidesteppable = not opp_move.categories.homing

    ws_results = [
        _to_result(m, "hit_level_defense")
        for m in steve_moves
        if m.input.startswith("WS.")
    ]
    return HitLevelResult(
        high=high,
        sidesteppable=sidesteppable,
        ws_punishers=sort_results(ws_results, sort),
    )
