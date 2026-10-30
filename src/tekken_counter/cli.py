"""Command-line entry point for the Tekken counter calculator build pipeline."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from tekken_counter.engine import (
    HitLevelResult,
    block_punishers,
    ch_traps,
    hit_level_defense,
    whiff_punishers,
)
from tekken_counter.ingest import fetch_all
from tekken_counter.pipeline import build_moves
from tekken_counter.precompute import build_steve_index, write_index
from tekken_counter.schema import Move

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLEAN_OUTPUT = REPO_ROOT / "data" / "moves.clean.json"
DEFAULT_INDEX_OUTPUT = REPO_ROOT / "data" / "steve_index.json"
DEFAULT_REACTION = 15


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_ingest(args: argparse.Namespace) -> int:
    """Fetch Cargo data and emit normalized moves.clean.json."""
    fetch_kwargs: dict[str, Any] = {}
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


def cmd_precompute(args: argparse.Namespace) -> int:
    """Build steve_index.json from an existing moves.clean.json."""
    with args.input.open("r", encoding="utf-8") as f:
        data = json.load(f)
    moves = [Move.model_validate(item) for item in data]
    logger.info("Loaded %d moves from %s", len(moves), args.input)

    index = build_steve_index(moves, default_reaction=args.reaction)
    write_index(index, args.output)
    logger.info("Wrote %s", args.output)
    return 0


def cmd_engine_test(args: argparse.Namespace) -> int:
    """Run a quick engine query against the clean dataset."""
    with args.input.open("r", encoding="utf-8") as f:
        data = json.load(f)
    moves = [Move.model_validate(item) for item in data]
    steve_moves = [m for m in moves if m.id.startswith("Steve-")]

    if args.block is not None and args.followup is not None:
        results = ch_traps(steve_moves, args.block, args.followup, sort=args.sort)
        _print_results(f"CH traps (block={args.block}, followup i{args.followup})", results)
    elif args.block is not None:
        results = block_punishers(steve_moves, -args.block, sort=args.sort)
        _print_results(f"Block punishers at {-args.block}f advantage", results)
    elif args.recovery is not None:
        results = whiff_punishers(
            steve_moves,
            args.recovery,
            reaction=args.reaction,
            sort=args.sort,
        )
        _print_results(
            f"Whiff punishers (recovery={args.recovery}, reaction={args.reaction})",
            results,
        )
    elif args.move_id is not None:
        opp = next((m for m in moves if m.id == args.move_id), None)
        if opp is None:
            logger.error("Move id %r not found", args.move_id)
            return 1
        result = hit_level_defense(opp, steve_moves, sort=args.sort)
        _print_hit_level_result(args.move_id, result)
    else:
        logger.error("Specify --block, --recovery, or --move-id")
        return 2
    return 0


def _print_results(header: str, results: list[Any]) -> None:
    print(header)
    for r in results[:20]:
        tags = []
        if r.categories.launcher:
            tags.append("launcher")
        if r.categories.ch_launcher:
            tags.append("CH-launcher")
        if r.categories.downed:
            tags.append("downed")
        if r.categories.stagger:
            tags.append("stagger")
        tag_str = f" ({', '.join(tags)})" if tags else ""
        print(f"  {r.input:<16} i{r.startup_min:<3} {r.damage:>3}dmg{tag_str}")
    print(f"  ({len(results)} total)")


def _print_hit_level_result(move_id: str, result: HitLevelResult) -> None:
    print(f"Hit-level defense for {move_id}")
    print(f"  high={result.high}, sidesteppable={result.sidesteppable}")
    print("  WS punishers:")
    for r in result.ws_punishers[:10]:
        print(f"    {r.input:<16} i{r.startup_min:<3} {r.damage:>3}dmg")
    print(f"  ({len(result.ws_punishers)} total)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tekken 8 counter calculator build pipeline"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command")

    ingest = subparsers.add_parser("ingest", help="Fetch and normalize Cargo data")
    ingest.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CLEAN_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_CLEAN_OUTPUT})",
    )
    ingest.add_argument(
        "--seed",
        type=Path,
        default=None,
        help="Path to moves.json seed (default: /home/sujay/viveka_scratchpad/moves.json)",
    )
    ingest.set_defaults(func=cmd_ingest)

    precompute = subparsers.add_parser("precompute", help="Build steve_index.json")
    precompute.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_CLEAN_OUTPUT,
        help=f"Clean moves JSON path (default: {DEFAULT_CLEAN_OUTPUT})",
    )
    precompute.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_INDEX_OUTPUT,
        help=f"Output index path (default: {DEFAULT_INDEX_OUTPUT})",
    )
    precompute.add_argument(
        "--reaction",
        type=int,
        default=DEFAULT_REACTION,
        help=f"Default reaction time in frames (default: {DEFAULT_REACTION})",
    )
    precompute.set_defaults(func=cmd_precompute)

    engine_test = subparsers.add_parser(
        "engine-test", help="Run a quick engine query"
    )
    engine_test.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_CLEAN_OUTPUT,
        help=f"Clean moves JSON path (default: {DEFAULT_CLEAN_OUTPUT})",
    )
    engine_test.add_argument(
        "--block",
        type=int,
        default=None,
        help="Opponent block advantage (e.g. -13); use with --followup for CH trap",
    )
    engine_test.add_argument(
        "--followup",
        type=int,
        default=None,
        help="Opponent follow-up startup for CH-trap mode",
    )
    engine_test.add_argument(
        "--recovery",
        type=int,
        default=None,
        help="Opponent whiff recovery",
    )
    engine_test.add_argument(
        "--reaction",
        type=int,
        default=DEFAULT_REACTION,
        help=f"Reaction time in frames (default: {DEFAULT_REACTION})",
    )
    engine_test.add_argument(
        "--move-id",
        type=str,
        default=None,
        help="Opponent move id for hit-level defense (e.g. Heihachi-f+4)",
    )
    engine_test.add_argument(
        "--sort",
        choices=["recommended", "max_damage", "fastest_startup"],
        default="recommended",
        help="Sort heuristic (default: recommended)",
    )
    engine_test.set_defaults(func=cmd_engine_test)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
