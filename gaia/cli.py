from __future__ import annotations

import argparse
import json

from .io import result_to_dict, write_result
from .scenarios import continuous_market, scenario_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gaia", description="Market design experiments for auctions and limit-order books"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run a continuous market experiment")
    run_parser.add_argument("--steps", type=int, default=100)
    run_parser.add_argument("--seed", type=int, default=7)
    run_parser.add_argument("--output", type=str)
    subparsers.add_parser("catalog", help="list built-in scenarios")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        print(
            json.dumps([{"name": item.name, "description": item.description} for item in scenario_catalog()], indent=2)
        )
        return 0
    simulation = continuous_market(seed=args.seed, steps=args.steps)
    result = simulation.run_continuous()
    if args.output:
        write_result(result, args.output)
    else:
        print(json.dumps(result_to_dict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
