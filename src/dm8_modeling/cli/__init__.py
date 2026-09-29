"""Public dm8-model command dispatch; scientific logic lives in source modules."""
from __future__ import annotations
import sys

def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"dataset", "fit", "evaluate"}:
        from .dataset import main as dataset_main
        dataset_main(sys.argv[1:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "pipeline":
        from .pipeline import main as pipeline_main
        pipeline_main(sys.argv[2:])
        return
    from .legacy import main as legacy_main
    legacy_main()
