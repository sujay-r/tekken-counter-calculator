"""Shared pytest fixtures for the Tekken counter calculator test suite."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from tekken_counter.ingest import fetch_all
from tekken_counter.pipeline import build_moves
from tekken_counter.schema import Move

SEED_PATH = Path("/home/sujay/viveka_scratchpad/moves.json")
REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_DATA_PATH = REPO_ROOT / "data" / "moves.clean.json"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "fixtures" / "raw_rows.json"

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--refresh-data",
        action="store_true",
        default=False,
        help=(
            "Re-record tests/fixtures/raw_rows.json from live wavu.wiki data. "
            "This is the only code path that touches the network; normal runs "
            "always replay the committed snapshot."
        ),
    )


def _record_snapshot() -> list[dict[str, Any]]:
    """Fetch live data once and atomically rewrite the committed snapshot."""
    rows = fetch_all(seed_path=SEED_PATH)
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SNAPSHOT_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    tmp_path.replace(SNAPSHOT_PATH)
    logger.warning("Recorded %d raw rows to %s", len(rows), SNAPSHOT_PATH)
    return rows


@pytest.fixture(scope="session")
def raw_rows(pytestconfig: pytest.Config) -> list[dict[str, Any]]:
    """Replay the committed raw Cargo rows; performs zero network requests.

    ``tests/fixtures/raw_rows.json`` is a plain JSON list of the dicts returned
    by ``fetch_all(seed_path=SEED_PATH)`` (deduplicated, seed tags/transitions
    merged), so it can be passed straight to ``build_moves``.

    Re-recording is opt-in and never happens on a normal run: use
    ``pytest --refresh-data`` (optionally with ``-k`` to select one test). That
    flag calls ``fetch_all`` once and atomically rewrites the snapshot. Without
    it the fixture only reads the snapshot from disk.
    """
    if pytestconfig.getoption("--refresh-data"):
        return _record_snapshot()

    with SNAPSHOT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def clean_moves(raw_rows: list[dict[str, Any]]) -> list[Move]:
    """Normalize the full fetched dataset once per session."""
    return build_moves(raw_rows)


@pytest.fixture(scope="session")
def moves_by_id(clean_moves: list[Move]) -> dict[str, Move]:
    return {move.id: move for move in clean_moves}


@pytest.fixture
def steve_b1(moves_by_id: dict[str, Move]) -> Move:
    return moves_by_id["Steve-b+1"]


@pytest.fixture(scope="session")
def seed_by_id() -> dict[str, dict[str, Any]]:
    with SEED_PATH.open("r", encoding="utf-8") as f:
        seed = json.load(f)
    by_id: dict[str, dict[str, Any]] = {}
    for char_slug, moves in seed.items():
        for move in moves:
            wid = move.get("wavu_id")
            if wid:
                by_id[wid] = move
    return by_id
