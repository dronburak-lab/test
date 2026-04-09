import tempfile
import unittest

from automation.policy_guard import PolicyConfig, PolicyError, PolicyGuard
from automation.status_machine import can_transition, require_transition
from automation.task_store.base import TaskPriority, TaskStatus
from automation.task_store.sheets_locator import SheetLocation


class PipelineContractTests(unittest.TestCase):
    def test_scenario_a_status_ready_to_in_progress_allowed(self):
        self.assertTrue(can_transition(TaskStatus.READY_TO_WORK, TaskStatus.IN_PROGRESS))

    def test_scenario_c_invalid_transition_raises(self):
        with self.assertRaises(ValueError):
            require_transition(TaskStatus.DONE, TaskStatus.IN_PROGRESS)

    def test_scenario_d_policy_blocks_forbidden_command(self):
        cfg = PolicyConfig(
            allowed_commands=["git status"],
            allowed_command_prefixes=["git "],
            blocked_commands=["git reset --hard", "rm -rf", "sudo "],
            allowed_paths=["."],
            blocked_paths=["/etc"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            guard = PolicyGuard(cfg, workspace=tmp)
            with self.assertRaises(PolicyError):
                guard.validate_command("git reset --hard")

    def test_scenario_i_sheet_location_accepts_name_switch(self):
        loc = SheetLocation.from_config(
            {"spreadsheet_id": "abc123", "worksheet_name": "tasks-next"}
        )
        self.assertEqual(loc.worksheet_name, "tasks-next")

    def test_scenario_i_sheet_location_accepts_gid_switch(self):
        loc = SheetLocation.from_config(
            {"spreadsheet_id": "abc123", "worksheet_gid": 123456}
        )
        self.assertEqual(loc.worksheet_gid, 123456)

    def test_status_and_priority_values_are_strict(self):
        self.assertEqual(TaskStatus("planning"), TaskStatus.PLANNING)
        self.assertEqual(TaskPriority("P1"), TaskPriority.P1)
        with self.assertRaises(ValueError):
            TaskStatus("READY")
        with self.assertRaises(ValueError):
            TaskPriority("high")


if __name__ == "__main__":
    unittest.main()
