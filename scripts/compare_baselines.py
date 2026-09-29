"""Compare saved pre-refactor QC/STA/Ridge/Pixel outputs to fresh reruns."""

import argparse
import json
from pathlib import Path

import numpy as np


PAIRS = {
    "QC": ("qc_verified", "regression_qc", "data_qc.json", None),
    "STA": ("first_pass", "regression_sta", "baseline_metrics.json", "baseline_kernels.npz"),
    "Ridge": ("ridge_raw", "regression_ridge", "baseline_metrics.json", "ridge_coefficients.npz"),
    "Pixel": ("pixel_raw", "regression_pixel", "pixel_metrics.json", "pixel_model.npz"),
}


def compare_json(left, right, location="") -> tuple[int, float, list[str]]:
    if isinstance(left, dict) and isinstance(right, dict):
        missing = sorted(set(left) ^ set(right))
        count, maximum, issues = 0, 0.0, [f"{location}/{key}: key mismatch" for key in missing]
        for key in sorted(set(left) & set(right)):
            n, delta, found = compare_json(left[key], right[key], f"{location}/{key}")
            count += n
            maximum = max(maximum, delta)
            issues.extend(found)
        return count, maximum, issues
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return 0, 0.0, [f"{location}: list lengths differ"]
        values = [compare_json(a, b, f"{location}/{i}") for i, (a, b) in enumerate(zip(left, right))]
        return sum(v[0] for v in values), max((v[1] for v in values), default=0), sum((v[2] for v in values), [])
    if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
        delta = abs(left - right)
        return 1, delta, [] if np.isclose(left, right, rtol=1e-8, atol=1e-8) else [f"{location}: {left} != {right}"]
    return 0, 0.0, [] if left == right else [f"{location}: value mismatch"]


def old_keys_preserved(left, right) -> bool:
    if isinstance(left, dict):
        return isinstance(right, dict) and set(left) <= set(right) and all(
            old_keys_preserved(value, right[key]) for key, value in left.items()
        )
    if isinstance(left, list):
        return isinstance(right, list) and len(left) == len(right) and all(
            old_keys_preserved(a, b) for a, b in zip(left, right)
        )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/audit"))
    args = parser.parse_args()
    results = {}
    for kind, (old_dir, new_dir, metrics, arrays) in PAIRS.items():
        old_paths = sorted((args.outputs_root / old_dir).glob(f"fly*/*/{metrics}"))
        new_paths = sorted((args.outputs_root / new_dir).glob(f"fly*/*/{metrics}"))
        if len(old_paths) != 5 or len(new_paths) != 5:
            raise ValueError(f"Expected five old and new {kind} metrics")
        details = []
        for old, new in zip(old_paths, new_paths, strict=True):
            if old.parts[-3:] != new.parts[-3:]:
                raise ValueError("Run paths do not match")
            old_payload, new_payload = json.loads(old.read_text()), json.loads(new.read_text())
            count, maximum, issues = compare_json(old_payload, new_payload)
            metadata_additions = []
            if kind == "QC":
                # Older saved QC predates added provenance fields. Shared
                # measurements must match; new keys are recorded separately.
                if old_keys_preserved(old_payload, new_payload):
                    metadata_additions = [issue for issue in issues if issue.endswith(": key mismatch")]
                    issues = [issue for issue in issues if issue not in metadata_additions]
            array_details = {}
            if arrays:
                with np.load(old.with_name(arrays), allow_pickle=False) as a, np.load(new.with_name(arrays), allow_pickle=False) as b:
                    if set(a.files) != set(b.files):
                        issues.append("Array names differ")
                    for name in set(a.files) & set(b.files):
                        left, right = a[name], b[name]
                        if left.shape != right.shape or left.dtype != right.dtype:
                            issues.append(f"{name} shape/dtype differ")
                        elif np.issubdtype(left.dtype, np.number):
                            diff = float(np.max(np.abs(left.astype(np.float64) - right.astype(np.float64)))) if left.size else 0.0
                            array_details[name] = diff
                            if not np.allclose(left, right, rtol=1e-8, atol=1e-8):
                                issues.append(f"{name} numeric values differ")
                        elif not np.array_equal(left, right):
                            issues.append(f"{name} values differ")
            details.append({"fly": old.parts[-3], "numeric_fields_compared": count,
                            "max_json_numeric_absolute_difference": maximum,
                            "max_array_absolute_difference": array_details,
                            "metadata_key_additions": metadata_additions,
                            "issues": issues})
        results[kind] = {"classification": "READABILITY_ONLY" if all(not row["issues"] for row in details) else "NUMERICAL_CHANGE",
                         "details": details}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "baseline_regression.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({kind: value["classification"] for kind, value in results.items()}))
    if any(value["classification"] != "READABILITY_ONLY" for value in results.values()):
        raise SystemExit("Baseline regression changed")


if __name__ == "__main__":
    main()
