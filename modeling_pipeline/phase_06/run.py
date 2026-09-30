"""Run Phase 6.1A-C without changing the historical Stage 01-12 pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from dm8_modeling.experiments.phase6 import run_phase6


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run_phase6(args.workspace_root))


if __name__ == "__main__":
    main()
