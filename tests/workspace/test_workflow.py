"""Stage receipts must reject stale or missing predecessors."""
import json
import tempfile
import unittest
from pathlib import Path

from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest, verify_stage_manifest


class WorkflowContracts(unittest.TestCase):
    def test_manifest_rejects_changed_input_and_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, result = root / "input.txt", root / "result.txt"
            source.write_text("original")
            result.write_text("result")
            path = write_stage_manifest("stage_01_source_audit", root / "outputs", {"a": 1},
                                        [source], [result], root)
            self.assertEqual(verify_stage_manifest(path, {"a": 1})["status"], "complete")
            source.write_text("changed")
            with self.assertRaisesRegex(ValueError, "input_hashes changed"):
                verify_stage_manifest(path, {"a": 1})
            source.write_text("original")
            result.write_text("changed")
            with self.assertRaisesRegex(ValueError, "output_hashes changed"):
                verify_stage_manifest(path, {"a": 1})

    def test_starting_at_stage_seven_requires_stage_six(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "configs").mkdir()
            (root / "configs/workflow.json").write_text(json.dumps({
                "schema_version": "workflow_v1", "output_root": "outputs"}))
            context = WorkflowContext.load(root)
            with self.assertRaisesRegex(FileNotFoundError, "Run the previous stage first"):
                context.require_previous(7)
