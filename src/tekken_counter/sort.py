"""Locked sort heuristics for counter recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from tekken_counter.schema import Categories


@dataclass(frozen=True, slots=True)
class MatchResult:
    """A Steve move matched against an opponent scenario."""

    id: str
    input: str
    name: str
    startup_min: int
    startup_max: int
    damage: int
    categories: Categories
    scenario: str


def _tie_breakers(result: MatchResult) -> tuple[int, str]:
    """Stable, deterministic tie-breakers used by every sort."""
    return (result.startup_min, result.input)


def sort_recommended(results: list[MatchResult]) -> list[MatchResult]:
    """Default Recommended ordering from Scope §8.

    Priority:
      1. Normal-hit launcher
      2. CH-launcher
      3. Knockdown (downed) or stagger
      4. Damage descending
      5. Fastest startup
    """

    def key(r: MatchResult) -> tuple[int, int, int, int, int, str]:
        cat = r.categories
        return (
            0 if cat.launcher else 1,
            0 if cat.ch_launcher else 1,
            0 if (cat.downed or cat.stagger) else 1,
            -r.damage,
            r.startup_min,
            r.input,
        )

    return sorted(results, key=key)


def sort_max_damage(results: list[MatchResult]) -> list[MatchResult]:
    """Max damage ordering: damage desc -> launcher -> fastest startup."""

    def key(r: MatchResult) -> tuple[int, int, int, str]:
        return (
            -r.damage,
            0 if r.categories.launcher else 1,
            r.startup_min,
            r.input,
        )

    return sorted(results, key=key)


def sort_fastest_startup(results: list[MatchResult]) -> list[MatchResult]:
    """Fastest startup ordering: startup asc -> damage desc."""

    def key(r: MatchResult) -> tuple[int, int, str]:
        return (r.startup_min, -r.damage, r.input)

    return sorted(results, key=key)


_SORTERS: dict[str, callable] = {
    "recommended": sort_recommended,
    "max_damage": sort_max_damage,
    "fastest_startup": sort_fastest_startup,
}


def sort_results(results: list[MatchResult], sort: str = "recommended") -> list[MatchResult]:
    """Dispatch to a named sorter."""
    sorter = _SORTERS.get(sort)
    if sorter is None:
        raise ValueError(f"Unknown sort: {sort!r}. Choose from {list(_SORTERS)}")
    return sorter(results)
