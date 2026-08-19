"""Resolve string-move parent chains into full per-hit lists."""

from __future__ import annotations

import logging
from typing import Any

from tekken_counter.normalize import parse_damage, parse_hit_levels, parse_startup
from tekken_counter.schema import Move, StartupRange

logger = logging.getLogger(__name__)


def _concat_input(parent_input: str, child_input: str | None) -> str:
    """Join parent and child inputs into the full command."""
    if not child_input:
        return parent_input
    if child_input.startswith(","):
        return parent_input + child_input
    if parent_input:
        return parent_input + "," + child_input
    return child_input


def _resolve_parent_chain(
    row: dict[str, Any], rows_by_id: dict[str, dict[str, Any]], seen: set[str]
) -> list[dict[str, Any]]:
    """Return [root, ..., row] following parent links; detect cycles."""
    chain: list[dict[str, Any]] = []
    current: dict[str, Any] | None = row
    while current is not None:
        cid = current.get("id")
        if cid in seen:
            logger.warning("Parent cycle detected at id %r", cid)
            break
        if cid is None:
            break
        seen.add(cid)
        chain.insert(0, current)
        parent_id = current.get("parent")
        if not parent_id:
            break
        current = rows_by_id.get(parent_id)
        if current is None:
            logger.warning("Missing parent %r for move %r", parent_id, cid)
            break
    return chain


def _extract_values(chain: list[dict[str, Any]], field: str, parser) -> list[Any]:
    """Parse and concatenate a per-hit field across a parent chain."""
    result: list[Any] = []
    for node in chain:
        raw = node.get(field)
        parsed = parser(raw)
        result.extend(parsed)
    return result


def _extract_input(chain: list[dict[str, Any]]) -> str:
    """Concatenate inputs across a parent chain."""
    full = ""
    for node in chain:
        full = _concat_input(full, node.get("input"))
    return full


def _startup_to_range(item: StartupRange) -> str:
    """Human-readable startup range for diagnostics."""
    if item.min == item.max:
        return f"i{item.min}"
    return f"i{item.min}-{item.max}"


def link_strings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a new list of raw rows with linked per-hit fields added.

    Adds the following keys to every row:
        * ``linked_input`` — full command (e.g. ``1,1,2``)
        * ``linked_target`` — list of :class:`HitLevel`
        * ``linked_damage`` — list of int
        * ``linked_startup`` — list of :class:`StartupRange`
    """
    rows_by_id = {row["id"]: row for row in rows if row.get("id")}
    linked: list[dict[str, Any]] = []
    for row in rows:
        chain = _resolve_parent_chain(row, rows_by_id, set())
        linked.append(
            {
                **row,
                "linked_input": _extract_input(chain),
                "linked_target": _extract_values(chain, "target", parse_hit_levels),
                "linked_damage": _extract_values(chain, "damage", parse_damage),
                "linked_startup": _extract_values(chain, "startup", parse_startup),
            }
        )
    return linked
