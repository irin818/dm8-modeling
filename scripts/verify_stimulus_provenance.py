"""Regenerate saved June stimulus arrays with the local read-only 05E code.

This verifies functional array equivalence, not identity with the absent
07E_260529_02 Windows source revision used by the acquisition computer.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from dm8_modeling.data import discover_sessions


def verify(data_root: Path, stimulus_code_root: Path) -> list[dict]:
    contracts = list(stimulus_code_root.glob("*/05E_stimulus_timing_geometry_contract/stimulus_contract.py"))
    if len(contracts) != 1:
        raise FileNotFoundError("Expected one 05E stimulus_contract.py under stimulus code root")
    module_path = contracts[0]
    spec = importlib.util.spec_from_file_location("dm8_external_stimulus_contract", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {module_path}")
    contract = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = contract
    # Source modules are imported only for an in-memory comparison. Suppress
    # bytecode caches in the external stimulus engineering tree.
    sys.dont_write_bytecode = True
    spec.loader.exec_module(contract)
    result = []
    for session in discover_sessions(data_root):
        package = session.path / "stimulus_package"
        recipe = json.loads((package / "stim_recipe.json").read_text())
        regenerated = contract.package_array_map(contract.generate_package(recipe))
        with np.load(package / "stim_realized.npz", allow_pickle=False) as saved:
            names_match = set(saved.files) == set(regenerated)
            arrays = {
                name: {
                    "shape": list(saved[name].shape),
                    "dtype": str(saved[name].dtype),
                    "equal": bool(np.array_equal(saved[name], regenerated[name])),
                    "sha256_array": contract.sha256_array(saved[name]),
                }
                for name in saved.files if name in regenerated
            }
        row = {
            "fly": session.fly, "run_id": session.run_id,
            "recipe_id": recipe["recipe_id"], "seed": recipe["randomization"]["seed"],
            "source_file": str(module_path), "source_version_identity": "UNRESOLVED",
            "array_names_match": names_match,
            "all_arrays_equal": names_match and all(a["equal"] for a in arrays.values()),
            "arrays": arrays,
        }
        result.append(row)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--stimulus-code-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = verify(args.data_root, args.stimulus_code_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "stimulus_provenance_check.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    )
    for row in rows:
        print(row["fly"], row["run_id"], row["all_arrays_equal"], len(row["arrays"]))
    if not all(row["all_arrays_equal"] for row in rows):
        raise SystemExit("Stimulus array mismatch")


if __name__ == "__main__":
    main()
