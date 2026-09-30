"""Run Phase 6.1b without changing the historical Phase 6.1 outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from dm8_modeling.experiments.rf_method_audit import run_rf_method_audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run_rf_method_audit(args.workspace_root))


if __name__ == "__main__":
    main()
