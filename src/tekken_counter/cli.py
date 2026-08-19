"""Command-line entry point: regenerate ``data/moves.clean.json``."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from tekken_counter.ingest import fetch_all
from tekken_counter.pipeline import build_moves

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "moves.clean.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch wavu Cargo data and emit normalized moves.clean.json"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=None,
        help="Path to moves.json seed (default: /home/sujay/viveka_scratchpad/moves.json)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    fetch_kwargs = {}
    if args.seed is not None:
        fetch_kwargs["seed_path"] = args.seed
    raw_rows = fetch_all(**fetch_kwargs)
    logger.info("Fetched %d raw Cargo rows", len(raw_rows))

    moves = build_moves(raw_rows)
    logger.info("Normalized %d moves", len(moves))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(
            [m.model_dump(mode="json") for m in moves],
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info("Wrote %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
