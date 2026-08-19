"""Shared pytest fixtures for the Tekken counter calculator test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tekken_counter.ingest import fetch_all
from tekken_counter.pipeline import build_moves
from tekken_counter.schema import Move

SEED_PATH = Path("/home/sujay/viveka_scratchpad/moves.json")
REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_DATA_PATH = REPO_ROOT / "data" / "moves.clean.json"


@pytest.fixture(scope="session")
def raw_rows() -> list[dict[str, Any]]:
    """Fetch every Cargo row once per test session and merge seed tags."""
    return fetch_all(seed_path=SEED_PATH)


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
