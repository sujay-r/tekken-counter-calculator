"""Parse raw Cargo string fields into typed IR values."""

from __future__ import annotations

import html
import logging
import re
from typing import Iterable

from tekken_counter.schema import (
    EffectKind,
    FrameAdvantage,
    HitLevel,
    StartupRange,
)

logger = logging.getLogger(__name__)

_EFFECT_MAP: dict[str, EffectKind] = {
    "a": EffectKind.LAUNCHER,
    "d": EffectKind.DOWNED,
    "g": EffectKind.GUARD_RECOVER,
    "c": EffectKind.CROUCH,
    "s": EffectKind.STAGGER,
    "b": EffectKind.BACK_TURNED,
    "w": EffectKind.WALL_CRUSH,
}

_HITLEVEL_MAP: dict[str, HitLevel] = {
    "h": HitLevel.HIGH,
    "m": HitLevel.MID,
    "l": HitLevel.LOW,
    "sma": HitLevel.SMA,
    "sm": HitLevel.SMA,
    "sp": HitLevel.SMA,  # special / stance-specific hit level
    "sl": HitLevel.LOW,  # special low
    "sll": HitLevel.LOW,  # typo for sl
    "special": HitLevel.SMA,
    "t": HitLevel.THROW,
    "throw": HitLevel.THROW,
    "high": HitLevel.HIGH,
    "mid": HitLevel.MID,
    "low": HitLevel.LOW,
}


# Explicit uppercase single-letter grounded hit levels (preserve case before lowercasing).
_GROUNDED_HITLEVEL_MAP: dict[str, HitLevel] = {
    "H": HitLevel.H,
    "M": HitLevel.M,
    "L": HitLevel.L,
}

# Advantage token: optional sign, number, optional suffix, optional tech window.
_ADV_TOKEN_RE = re.compile(
    r"(?P<sign>[+-]?)(?P<frames>\d+)(?P<suffix>[adgcsbw]?)(?:\s*\((?P<tech_sign>[+-]?)(?P<tech>\d+)\))?",
    re.IGNORECASE,
)


def _tokenize(raw: str | None, delimiters: str | None = None) -> list[str]:
    """Split a raw Cargo string into tokens, stripping empty/whitespace entries."""
    if not raw:
        return []
    if delimiters is None:
        # Default: split on commas, semicolons, and whitespace.
        parts = re.split(r"[,;\s]+", raw.strip())
    else:
        parts = re.split(f"[{re.escape(delimiters)}]+", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def parse_startup(raw: str | None) -> list[StartupRange]:
    """Parse startup strings into inclusive frame ranges.

    Examples:
        * ``i15`` -> ``[{15,15}]``
        * ``i13-14`` -> ``[{13,14}]``
        * ``i15~16`` -> ``[{15,16}]``
        * ``i10, i15`` -> ``[{10,10}, {15,15}]``
        * ``i55-i130`` -> ``[{55,130}]``
        * ``i11(-14)`` -> ``[{11,11}]`` (parenthetical ignored)
        * ``i17-18/i19-20`` -> ``[{17,18}, {19,20}]``
    """
    ranges: list[StartupRange] = []
    for token in _tokenize(raw):
        token = token.lower().replace("~", "-").lstrip(".")
        # Strip trailing question marks and parentheticals.
        token = re.sub(r"\?.*$", "", token)
        token = re.sub(r"\([^)]*\)", "", token)
        token = token.strip()
        if not token or token in ("n/a", "/", "heat", "i") or token.startswith(("js", "pc")):
            continue
        # Slash-separated ranges (e.g. i17-18/i19-20) or consecutive frames
        # (e.g. i46/i47 -> i46~47).
        subs = [s.strip() for s in token.split("/")]
        i = 0
        while i < len(subs):
            sub = subs[i]
            if "-" in sub:
                parts = sub.split("-", 1)
                lo_str = parts[0].lstrip("i").strip()
                hi_str = parts[1].lstrip("i").strip()
                if not lo_str or not hi_str:
                    i += 1
                    continue
                try:
                    lo = int(lo_str)
                    hi = int(hi_str)
                    ranges.append(StartupRange(min=min(lo, hi), max=max(lo, hi)))
                except ValueError:
                    logger.debug("Unrecognized startup range token: %r", token)
                i += 1
            else:
                cur_str = sub.lstrip("i").strip()
                nxt_str = (
                    subs[i + 1].lstrip("i").strip()
                    if i + 1 < len(subs) and "-" not in subs[i + 1]
                    else ""
                )
                if cur_str.isdigit() and nxt_str.isdigit():
                    lo = int(cur_str)
                    hi = int(nxt_str)
                    ranges.append(StartupRange(min=min(lo, hi), max=max(lo, hi)))
                    i += 2
                else:
                    try:
                        value = int(cur_str)
                        ranges.append(StartupRange(min=value, max=value))
                    except ValueError:
                        logger.debug("Unrecognized startup token: %r", token)
                    i += 1
    return ranges


def parse_damage(raw: str | None) -> list[int]:
    """Parse damage strings into per-hit integer damage.

    Examples:
        * ``5`` -> ``[5]``
        * ``,7`` -> ``[7]``
        * ``7,21`` -> ``[7, 21]``
        * ``[12;12]`` -> ``[12, 12]``
        * ``50 (28)`` -> ``[50]`` (recoverable portion ignored)
        * ``15/20/31`` -> ``[15, 20, 31]``
        * ``55+`` -> ``[55]``
        * ``10-75`` -> ``[75]`` (range -> maximum for reward ranking)
    """
    values: list[int] = []
    if not raw:
        return values

    # Strip bracket notation; semicolons become separators.
    cleaned = raw.strip().replace("[", "").replace("]", "")
    # Parenthesized recoverable portion is not per-hit damage.
    cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)

    for token in _tokenize(cleaned, ",;/"):
        token = token.strip().rstrip("+").rstrip("?").strip()
        if not token or token == "-":
            continue
        # Variable damage ranges: take the maximum as the reward value.
        if "-" in token:
            parts = token.split("-", 1)
            try:
                lo = int(parts[0].strip())
                hi = int(parts[1].strip())
                values.append(max(lo, hi))
            except ValueError:
                logger.debug("Unrecognized damage token: %r", token)
            continue
        try:
            values.append(int(token))
        except ValueError:
            logger.debug("Unrecognized damage token: %r", token)
            continue
    return values


def parse_advantage(raw: str | None) -> FrameAdvantage:
    """Parse frame advantage into a typed structure.

    Examples:
        * ``+18a (+11)`` -> frames=18, effect=LAUNCHER, tech_window=11
        * ``+13 +59a`` -> primary +13 with extra state +59a
        * ``+2c`` -> frames=2, effect=CROUCH
        * ``-14`` -> frames=-14
        * ``!`` -> frames=None (unblockable)
    """
    raw = raw or ""
    stripped = strip_wiki_markup(raw)
    tokens = _extract_advantage_tokens(stripped)
    if not tokens:
        return FrameAdvantage(raw=raw)

    primary = tokens[0]
    extras = tokens[1:] if len(tokens) > 1 else []
    return FrameAdvantage(
        frames=primary.frames,
        effect=primary.effect,
        tech_window=primary.tech_window,
        extra_states=extras,
        raw=raw,
    )


def _extract_advantage_tokens(stripped: str) -> list[FrameAdvantage]:
    """Extract one or more advantage states from a stripped string."""
    tokens: list[FrameAdvantage] = []
    for match in _ADV_TOKEN_RE.finditer(stripped):
        sign = -1 if match.group("sign") == "-" else 1
        try:
            frames = int(match.group("frames")) * sign
        except (TypeError, ValueError):
            continue
        suffix = (match.group("suffix") or "").lower()
        effect = _EFFECT_MAP.get(suffix)
        tech_window = None
        if match.group("tech"):
            tech_sign = -1 if match.group("tech_sign") == "-" else 1
            tech_window = int(match.group("tech")) * tech_sign
        tokens.append(
            FrameAdvantage(
                frames=frames,
                effect=effect,
                tech_window=tech_window,
                raw=match.group(0),
            )
        )
    return tokens


def parse_hit_levels(raw: str | None) -> list[HitLevel]:
    """Parse hit-level strings into normalized per-hit levels.

    Examples:
        * ``h`` -> ``[HIGH]``
        * ``,h`` -> ``[HIGH]``
        * ``m,m`` -> ``[MID, MID]``
        * ``L`` -> ``[L]``
        * ``ub(m)`` -> ``[MID]``
        * ``ub(l)`` -> ``[LOW]``
        * ``m (t)`` -> ``[THROW]``
    """
    levels: list[HitLevel] = []
    for token in _tokenize(raw, ","):
        stripped = token.strip()
        if not stripped:
            continue
        # Preserve uppercase single-letter grounded levels (L/M/H).
        if stripped in _GROUNDED_HITLEVEL_MAP:
            levels.append(_GROUNDED_HITLEVEL_MAP[stripped])
            continue
        lower = stripped.lower()
        # Strip prefix markers like "ub!", "ub", "r" and any parentheses/spaces.
        cleaned = re.sub(r"^(ub!|ub|r)", "", lower)
        cleaned = cleaned.replace("(", "").replace(")", "").replace(" ", "").strip()
        if cleaned in _HITLEVEL_MAP:
            levels.append(_HITLEVEL_MAP[cleaned])
            continue
        # Explicit throw marker inside a compound token.
        if "t" in cleaned:
            levels.append(HitLevel.THROW)
            continue
        first = cleaned[0] if cleaned else ""
        if first in _HITLEVEL_MAP:
            levels.append(_HITLEVEL_MAP[first])
        else:
            logger.debug("Unrecognized hit level token: %r", stripped)
            levels.append(HitLevel.UNKNOWN)
    return levels


def parse_block(raw: str | None) -> tuple[int | None, bool]:
    """Parse block advantage.

    Returns ``(frames, unblockable)``. Blank or ``!`` means unblockable.
    """
    raw = raw or ""
    stripped = strip_wiki_markup(raw).strip()
    if not stripped or stripped == "!":
        return None, True
    sign = -1 if stripped.startswith("-") else 1
    numeric = re.sub(r"[^0-9]", "", stripped)
    if not numeric:
        return None, False
    try:
        return int(numeric) * sign, False
    except ValueError:
        return None, False


def strip_wiki_markup(raw: str | None) -> str:
    """Return display text from wiki markup and HTML entities.

    * ``[[Steve_combos#Staples|+61a]]`` -> ``+61a``
    * HTML entities are decoded to characters.
    * Leading/trailing whitespace is stripped.
    """
    if not raw:
        return ""
    text = html.unescape(raw or "")
    # Wiki link: keep the pipe target (display text).
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    # Bare wiki links or remaining markup brackets.
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    # Strip HTML tags.
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_notes(raw: str | None) -> str:
    """Strip wiki markup and HTML from notes, preserving readable text."""
    return strip_wiki_markup(raw)


def infer_safety(block: int | None) -> "SafetyKind | None":
    """Derive the safety tri-state from parsed block advantage."""
    from tekken_counter.schema import SafetyKind

    if block is None:
        return None
    if block >= -9:
        return SafetyKind.SAFE
    if block >= -14:
        return SafetyKind.SEMI
    return SafetyKind.PUNISHABLE


def iter_all_states(adv: FrameAdvantage) -> Iterable[FrameAdvantage]:
    """Yield the primary state plus every extra state."""
    yield adv
    yield from adv.extra_states
