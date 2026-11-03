"""One entry point for input preparation, dispatch and reproducible diagnostics."""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import yaml

from .data import demo, prepare
from .optimisation import build, solve


def _run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "solve", "demo"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--hours", type=int, help="Explicit shorter diagnostic horizon")
    parser.add_argument("--start", help="UTC start timestamp for a diagnostic window")
    parser.add_argument(
        "--relax", action="store_true", help="Diagnostic LP relaxation of all modes"
    )
    parser.add_argument("--objective", choices=["system", "local"])
    parser.add_argument("--hp-policy", choices=["endogenous", "must_run"])
    parser.add_argument("--time-limit", type=float, help="HiGHS solve time limit in seconds")
    parser.add_argument("--mip-gap", type=float, help="Relative MILP optimality gap target")
    parser.add_argument("--solver", choices=["highs", "gurobi"])
    parser.add_argument("--discount", type=float, help="Illustrative discharge credit, DKK/MWh")
    parser.add_argument(
        "--schedule", type=Path, help="Central dispatch.csv supplying the charging schedule"
    )
    parser.add_argument("--prices", action="store_true", help="Fixed-commitment LP marginal values")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        frame, report = prepare(args.root, args.year, repair=args.repair)
        print(json.dumps({"hours": len(frame), "repaired_cells": len(report["repairs"])}))
        return
    config_path = args.config or args.root / "config/base.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["year"] = args.year
    if args.relax:
        config["integer_operation"] = False
    if args.objective:
        config["objective"] = args.objective
    if args.hp_policy:
        config["heat_pumps"]["policy"] = args.hp_policy
    if args.time_limit is not None:
        if args.time_limit <= 0:
            raise ValueError("Time limit must be positive")
        config["solver"]["time_limit"] = args.time_limit
    if args.mip_gap is not None:
        if not 0 <= args.mip_gap < 1:
            raise ValueError("MILP gap must be in [0,1)")
        config["solver"]["mip_rel_gap"] = args.mip_gap
    if args.solver:
        config["solver"]["backend"] = args.solver
    if args.discount is not None:
        config["discharge_discount_dkk_mwh"] = args.discount
    input_path = args.inputs or args.root / f"data/processed/inputs_{args.year}.csv"
    if args.command == "demo":
        frame = demo(args.hours or 168)
        input_provenance = {"kind": "synthetic_demo"}
    else:
        frame = pd.read_csv(input_path, index_col=0)
        frame.index = pd.to_datetime(frame.index, utc=True)
        input_provenance = {
            "kind": "prepared_inputs",
            "path": str(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        }
    if args.start:
        start = pd.Timestamp(args.start)
        start = start.tz_localize("UTC") if start.tz is None else start.tz_convert("UTC")
        frame = frame.loc[frame.index >= start]
        if frame.empty or frame.index[0] != start:
            raise ValueError("Start is not a covered hourly timestamp")
    if args.hours:
        if args.hours > len(frame):
            raise ValueError("Requested horizon exceeds input coverage")
        frame = frame.iloc[: args.hours]
    if args.schedule:
        scheduled = pd.read_csv(args.schedule, index_col=0)
        scheduled.index = pd.to_datetime(scheduled.index, utc=True)
        if scheduled.index.has_duplicates:
            raise ValueError("Duplicate schedule timestamps")
        frame["scheduled_ptes_charge_mw"] = scheduled.ptes_charge_mw.reindex(frame.index)
        input_provenance["schedule_sha256"] = hashlib.sha256(args.schedule.read_bytes()).hexdigest()
    plants_path = args.root / "config/plants.csv"
    plants = pd.read_csv(plants_path)
    model = build(frame, config, plants)
    solution = solve(model, prices=args.prices)
    solution.summary["input_provenance"] = input_provenance
    solution.summary["plant_input_sha256"] = hashlib.sha256(plants_path.read_bytes()).hexdigest()
    solution.summary["runtime"] = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
    }
    solution.summary["start_utc"] = str(frame.index[0])
    solution.summary["end_utc"] = str(frame.index[-1])
    output = args.output or args.root / "results" / args.command
    output.mkdir(parents=True, exist_ok=True)
    # Write only after an accepted, independently checked solution exists.
    solution.dispatch.to_csv(output / "dispatch.csv", index_label="timestamp")
    (output / "summary.json").write_text(json.dumps(solution.summary, indent=2, allow_nan=False))
    print(
        json.dumps(
            {
                k: solution.summary[k]
                for k in [
                    "objective_kind",
                    "objective_dkk",
                    "hours",
                    "solver_status",
                    "mip_gap",
                    "ptes_equivalent_cycles",
                    "max_constraint_violation",
                ]
            },
            indent=2,
        )
    )


def main(argv=None):
    try:
        _run(argv)
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
