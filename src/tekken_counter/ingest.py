"""Fetch all Cargo rows and cross-check / merge the local seed file."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from tekken_counter.characters import CARGO_PREFIXES
from tekken_counter.client import fetch_character

logger = logging.getLogger(__name__)

DEFAULT_SEED_PATH = Path("/home/sujay/viveka_scratchpad/moves.json")


def load_seed(path: Path | str = DEFAULT_SEED_PATH) -> dict[str, Any]:
    """Load the seed moves.json and return it keyed by ``wavu_id``.

    The seed is organized as ``{char_slug: [move, ...]}``; this function flattens
    it into ``{wavu_id: move}`` for fast lookup.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        seed = json.load(f)
    by_id: dict[str, dict[str, Any]] = {}
    for char_slug, moves in seed.items():
        for move in moves:
            wid = move.get("wavu_id")
            if wid:
                by_id[wid] = move
    logger.info("Loaded seed %s: %d moves", path, len(by_id))
    return by_id


def merge_seed_tags(
    rows: list[dict[str, Any]], seed_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Attach ``tags`` and ``transitions`` from the seed onto matching Cargo rows."""
    merged: list[dict[str, Any]] = []
    missing: list[str] = []
    for row in rows:
        move_id = row.get("id")
        seed_move = seed_by_id.get(move_id) if move_id else None
        merged_row = dict(row)
        if seed_move:
            merged_row["tags"] = seed_move.get("tags") or None
            merged_row["transitions"] = seed_move.get("transitions") or None
        else:
            merged_row["tags"] = None
            merged_row["transitions"] = None
            if move_id:
                missing.append(move_id)
        merged.append(merged_row)

    if missing:
        logger.warning("%d Cargo rows missing seed tags", len(missing))
    return merged


def _count_non_null(row: dict[str, Any]) -> int:
    """Score a row by how many fields are populated; used for deduplication."""
    return sum(1 for v in row.values() if v is not None and v != "")


def deduplicate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate Cargo ids, keeping the most complete row.

    wavu occasionally emits multiple rows for the same ``id`` (e.g. stance-specific
    versions). We keep the row with the most populated fields and log each merge.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        move_id = row.get("id")
        if not move_id:
            continue
        existing = by_id.get(move_id)
        if existing is None or _count_non_null(row) > _count_non_null(existing):
            if existing is not None:
                logger.debug(
                    "Deduplicating id %r: replacing %d-field row with %d-field row",
                    move_id,
                    _count_non_null(existing),
                    _count_non_null(row),
                )
            by_id[move_id] = row
    return list(by_id.values())


def fetch_all(
    prefixes: list[str] | None = None,
    seed_path: Path | str | None = DEFAULT_SEED_PATH,
) -> list[dict[str, Any]]:
    """Fetch every configured Cargo prefix and merge seed tags.

    Returns a list of raw Cargo dicts with ``tags`` and ``transitions`` merged
    from the seed file.
    """
    prefixes = prefixes or CARGO_PREFIXES
    rows: list[dict[str, Any]] = []
    for prefix in prefixes:
        rows.extend(fetch_character(prefix))

    rows = deduplicate(rows)
    ids = [row.get("id") for row in rows if row.get("id")]
    if len(ids) != len(set(ids)):
        duplicates = {i for i in ids if ids.count(i) > 1}
        raise ValueError(f"Duplicate Cargo ids found: {sorted(duplicates)[:10]}")

    seed_by_id = load_seed(seed_path) if seed_path else {}
    return merge_seed_tags(rows, seed_by_id)
