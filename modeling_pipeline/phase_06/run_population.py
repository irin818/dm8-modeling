"""Run Phase 6.2 full-data descriptive population RF reconstruction."""

from __future__ import annotations

import argparse
from pathlib import Path

from dm8_modeling.experiments.phase62 import run_phase62


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run_phase62(args.workspace_root))


if __name__ == "__main__":
    main()
