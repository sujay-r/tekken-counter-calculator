"""Roster mapping between seed slugs and wavu Cargo `id` prefixes."""

from __future__ import annotations

#: Playable character slugs as they appear in the seed moves.json.
PLAYABLE_CHARACTERS: list[str] = [
    "alisa",
    "anna",
    "armor-king",
    "asuka",
    "azucena",
    "bryan",
    "claudio",
    "clive",
    "devil-jin",
    "dragunov",
    "eddy",
    "fahkumram",
    "feng",
    "heihachi",
    "hwaorang",
    "jack-8",
    "jin",
    "jun",
    "kazuya",
    "king",
    "kuma",
    "kunimitsu",
    "lars",
    "law",
    "lee",
    "leo",
    "leroy",
    "lidia",
    "lili",
    "miary-zo",
    "nina",
    "panda",
    "paul",
    "raven",
    "reina",
    "shaheen",
    "steve",
    "victor",
    "xiaoyu",
    "yoshimitsu",
    "zafina",
]

#: Non-character move groups present in Cargo (okizeme / generic states).
STATE_GROUPS: list[str] = [
    "Generic",
    "BT.",
    "EXD.",
    "FDFA.",
    "FDFT.",
    "FUFA.",
    "FUFT.",
]

#: Manual overrides for slugs that do not map deterministically to Cargo prefixes.
_PREFIX_OVERRIDES: dict[str, str] = {
    "hwaorang": "Hwoarang",
}


def to_cargo_prefix(slug: str) -> str:
    """Convert a seed slug to the Cargo `id` prefix.

    Cargo ids use title-case space-separated names (e.g. ``Armor King-``,
    ``Devil Jin-``) or hyphenated names when the second part is numeric
    (e.g. ``Jack-8-``).
    """
    if slug in _PREFIX_OVERRIDES:
        return _PREFIX_OVERRIDES[slug]
    parts = slug.split("-")
    result_parts: list[str] = []
    for i, part in enumerate(parts):
        if i > 0 and part.isdigit():
            # Numeric suffix attaches with hyphen (e.g. Jack-8).
            result_parts[-1] = f"{result_parts[-1]}-{part.title()}"
        elif i > 0:
            # Word suffix separates with space (e.g. Armor King).
            result_parts.append(part.title())
        else:
            result_parts.append(part.title())
    return " ".join(result_parts)


#: All Cargo prefixes we query, in deterministic order.
CARGO_PREFIXES: list[str] = [
    *(to_cargo_prefix(slug) for slug in PLAYABLE_CHARACTERS),
    *STATE_GROUPS,
]
