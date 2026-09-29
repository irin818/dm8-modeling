"""Dispatch one stage or the full ordered Dm8 scientific workflow."""
from __future__ import annotations
import argparse
from pathlib import Path
from ..experiments.workflow import WorkflowContext, run_stage


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "stage"))
    parser.add_argument("number", nargs="?", type=int, help="Required with stage: 1 through 12")
    parser.add_argument("--from-stage", type=int, default=1, help="Start a full run from an already prepared predecessor")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    context = WorkflowContext.load(args.workspace_root)
    if args.action == "stage":
        if args.number is None:
            parser.error("pipeline stage requires a number")
        numbers = [args.number]
    else:
        if args.number is not None:
            parser.error("pipeline run accepts --from-stage, not a positional stage number")
        numbers = range(args.from_stage, 13)
    for number in numbers:
        print(f"Running Stage {number:02d}...", flush=True)
        print(run_stage(number, context), flush=True)
