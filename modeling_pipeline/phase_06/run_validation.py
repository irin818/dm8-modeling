"""Run Phase 6.3 independent fly RFs and exploratory full-pipeline null."""

import argparse
from pathlib import Path

from dm8_modeling.experiments.phase63 import run_phase63


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run_phase63(args.workspace_root))


if __name__ == '__main__':
    main()
