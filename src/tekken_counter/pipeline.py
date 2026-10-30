"""Assemble raw Cargo rows into normalized Move IR records."""

from __future__ import annotations

import logging
from typing import Any

from tekken_counter.categories import derive_categories
from tekken_counter.normalize import (
    clean_notes,
    parse_advantage,
    parse_block,
    parse_damage,
    parse_hit_levels,
    parse_recovery,
    parse_startup,
)
from tekken_counter.schema import Move
from tekken_counter.strings import link_strings

logger = logging.getLogger(__name__)


def _build_move(row: dict[str, Any]) -> Move:
    """Normalize a single raw Cargo row into a Move IR object."""
    block, block_unblockable = parse_block(row.get("block"))
    hit = parse_advantage(row.get("hit"))
    # Cargo blank ch means identical to hit.
    ch_raw = row.get("ch") or row.get("hit")
    ch = parse_advantage(ch_raw)

    return Move(
        id=row["id"] or "",
        name=row.get("name") or "",
        input=row.get("linked_input") or row.get("input") or "",
        parent=row.get("parent") or None,
        target=row.get("linked_target") or parse_hit_levels(row.get("target")),
        damage=row.get("linked_damage") or parse_damage(row.get("damage")),
        startup=row.get("linked_startup") or parse_startup(row.get("startup")),
        block=block,
        block_unblockable=block_unblockable,
        recovery=parse_recovery(row.get("recv")),
        hit=hit,
        ch=ch,
        raw_target=row.get("target") or None,
        raw_damage=row.get("damage") or None,
        raw_startup=row.get("startup") or None,
        raw_block=row.get("block") or None,
        raw_recv=row.get("recv") or None,
        raw_tot=row.get("tot") or None,
        raw_crush=row.get("crush") or None,
        raw_notes=clean_notes(row.get("notes")),
        raw_alias=row.get("alias") or None,
        raw_image=row.get("image") or None,
        raw_video=row.get("video") or None,
        raw_alt=row.get("alt") or None,
        tags=row.get("tags") or None,
        transitions=row.get("transitions") or None,
        categories=derive_categories(
            hit=hit,
            ch=ch,
            block=block,
            block_unblockable=block_unblockable,
            crush=row.get("crush"),
            notes=clean_notes(row.get("notes")),
            tags=row.get("tags"),
        ),
    )


def build_moves(raw_rows: list[dict[str, Any]]) -> list[Move]:
    """Link strings and normalize every raw row into a Move record."""
    linked_rows = link_strings(raw_rows)
    moves: list[Move] = []
    for row in linked_rows:
        try:
            moves.append(_build_move(row))
        except Exception as exc:
            logger.error("Failed to normalize row %r: %s", row.get("id"), exc)
            raise
    return moves
