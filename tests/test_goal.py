import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
import unittest.mock

GOAL_PATH = pathlib.Path(__file__).resolve().parents[1] / ".claude" / "skills" / "goal" / "goal.py"
SESSION = "sess-1"


def load_goal():
    spec = importlib.util.spec_from_file_location("goal", GOAL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GoalTestCase(unittest.TestCase):
    def setUp(self):
        self.goal = load_goal()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = pathlib.Path(self.tmp.name)
        (root / "home" / "projects" / "p").mkdir(parents=True)
        self.root = root
        patch = {"CLAUDE_PROJECT_DIR": str(root / "proj"), "CLAUDE_CONFIG_DIR": str(root / "home")}
        (root / "proj").mkdir()
        old = {key: os.environ.get(key) for key in (*patch, "CLAUDE_GOAL_MAX_TOKEN_BUDGET")}
        os.environ.pop("CLAUDE_GOAL_MAX_TOKEN_BUDGET", None)
        os.environ.update(patch)
        self.addCleanup(self.restore_env, old)

    @staticmethod
    def restore_env(old):
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def run_cli(self, *argv, stdin=""):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), unittest.mock.patch("sys.stdin", io.StringIO(stdin)):
            self.goal.main(["--session", SESSION, *argv])
        return out.getvalue()

    def run_hook(self, payload=None):
        payload = {"session_id": SESSION, "last_assistant_message": "working", **(payload or {})}
        out = io.StringIO()
        with contextlib.redirect_stdout(out), unittest.mock.patch("sys.stdin", io.StringIO(json.dumps(payload))):
            self.goal.main(["stop-hook"])
        return json.loads(out.getvalue()) if out.getvalue().strip() else None

    def write_transcript(self, rows):
        path = self.root / "home" / "projects" / "p" / f"{SESSION}.jsonl"
        lines = []
        for index, (when, msg_id, usage) in enumerate(rows):
            lines.append(json.dumps({
                "type": "assistant",
                "timestamp": when.isoformat(),
                "message": {"id": msg_id, "model": "m1", "usage": usage},
            }))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def set_goal(self, text="make tests pass"):
        return self.run_cli("slash", stdin=text)


class SlashParsingTests(GoalTestCase):
    def test_objective_sets_active_goal_and_asks_for_work(self):
        out = self.set_goal()
        self.assertIn("ACTION: work", out)
        self.assertIn("<goal_objective>", out)
        self.assertEqual(self.goal.read_state(SESSION)["status"], "active")

    def test_empty_args_view_reports_no_goal(self):
        out = self.run_cli("slash", stdin="")
        self.assertIn("No goal is active", out)
        self.assertIn("ACTION: report", out)

    def test_pause_word_followed_by_text_is_an_objective(self):
        self.set_goal("pause the old cron jobs and migrate them")
        self.assertEqual(self.goal.read_state(SESSION)["status"], "active")

    def test_empty_objective_rejected(self):
        with self.assertRaises(SystemExit):
            self.goal.run_set(SESSION, "   ")

    def test_objective_over_limit_rejected(self):
        with self.assertRaises(SystemExit):
            self.goal.run_set(SESSION, "x" * 4001)

    def test_objective_at_limit_accepted(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.goal.run_set(SESSION, "x" * 4000)
        self.assertIsNotNone(self.goal.read_state(SESSION))

    def test_second_goal_refused_while_active(self):
        self.set_goal()
        with self.assertRaises(SystemExit):
            self.set_goal("another")

    def test_bad_session_id_rejected(self):
        with self.assertRaises(SystemExit):
            self.goal.state_path("../evil")

    def test_edit_replaces_objective(self):
        self.set_goal()
        out = self.run_cli("slash", stdin="edit ship the release")
        self.assertIn("ACTION: work", out)
        self.assertEqual(self.goal.read_state(SESSION)["objective"], "ship the release")

    def test_clear_deletes_state(self):
        self.set_goal()
        self.run_cli("slash", stdin="clear")
        self.assertIsNone(self.goal.read_state(SESSION))


class LifecycleTests(GoalTestCase):
    def test_pause_then_resume(self):
        self.set_goal()
        self.run_cli("slash", stdin="pause")
        state = self.goal.read_state(SESSION)
        self.assertEqual(state["status"], "paused")
        self.assertIsNone(state["pauses"][0][1])
        out = self.run_cli("slash", stdin="resume")
        self.assertIn("ACTION: work", out)
        state = self.goal.read_state(SESSION)
        self.assertEqual(state["status"], "active")
        self.assertIsNotNone(state["pauses"][0][1])

    def test_complete_requires_evidence(self):
        self.set_goal()
        with self.assertRaises(SystemExit):
            self.run_cli("complete", "--evidence", "  ")

    def test_complete_marks_done_and_hook_goes_quiet(self):
        self.set_goal()
        self.run_cli("complete", "--evidence", "tests pass: 12 ok")
        state = self.goal.read_state(SESSION)
        self.assertEqual(state["status"], "complete")
        self.assertIsNone(self.run_hook())

    def test_elapsed_excludes_paused_time(self):
        start = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        state = self.goal.new_state("x", start)
        self.goal.pause_state(state, "r", start + dt.timedelta(minutes=10))
        self.goal.resume_state(state, start + dt.timedelta(minutes=40))
        self.assertEqual(self.goal.elapsed_seconds(state, start + dt.timedelta(minutes=60)), 30 * 60)


class UsageTests(GoalTestCase):
    def test_usage_dedupes_message_ids_and_skips_pauses(self):
        start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        state = self.goal.new_state("x", start)
        self.goal.pause_state(state, "r", start + dt.timedelta(minutes=10))
        self.goal.resume_state(state, start + dt.timedelta(minutes=20))
        row = {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000}
        self.write_transcript([
            (start - dt.timedelta(minutes=5), "before", row),
            (start + dt.timedelta(minutes=1), "a", {**row, "output_tokens": 1}),
            (start + dt.timedelta(minutes=1), "a", row),
            (start + dt.timedelta(minutes=15), "paused", row),
            (start + dt.timedelta(minutes=30), "b", row),
        ])
        totals, by_model = self.goal.read_usage(SESSION, state)
        self.assertEqual(totals["output"], 10)
        self.assertEqual(totals["cache_read"], 2000)
        self.assertEqual(by_model["m1"]["input"], 20)
        self.assertEqual(self.goal.budget_tokens(totals), 2 * 115)


class StopHookTests(GoalTestCase):
    def test_no_goal_allows_stop(self):
        self.assertIsNone(self.run_hook())

    def test_active_goal_blocks_with_work_prompt(self):
        self.set_goal()
        result = self.run_hook()
        self.assertEqual(result["decision"], "block")
        self.assertIn("goal_objective", result["reason"])
        self.assertEqual(self.goal.read_state(SESSION)["continuations"], 1)

    def test_paused_goal_allows_stop(self):
        self.set_goal()
        self.run_cli("pause", "--reason", "need a decision")
        self.assertIsNone(self.run_hook())

    def test_stall_pauses_after_identical_turns(self):
        self.set_goal()
        self.assertEqual(self.run_hook()["decision"], "block")
        self.assertEqual(self.run_hook()["decision"], "block")
        result = self.run_hook()
        self.assertNotIn("decision", result)
        self.assertEqual(self.goal.read_state(SESSION)["status"], "paused")

    def test_changing_output_never_stalls(self):
        self.set_goal()
        for turn in range(5):
            self.assertEqual(self.run_hook({"last_assistant_message": f"step {turn}"})["decision"], "block")

    def test_continuation_limit_pauses(self):
        (self.root / "proj" / ".claude").mkdir()
        (self.root / "proj" / ".claude" / "goal-config.json").write_text(
            json.dumps({"goals": {"max_continuations": 2}}), encoding="utf-8")
        self.set_goal()
        self.run_hook({"last_assistant_message": "a"})
        self.run_hook({"last_assistant_message": "b"})
        result = self.run_hook({"last_assistant_message": "c"})
        self.assertNotIn("decision", result)
        self.assertIn("safety limit", self.goal.read_state(SESSION)["reason"])

    def test_budget_exhaustion_sends_one_wrapup_then_stops(self):
        os.environ["CLAUDE_GOAL_MAX_TOKEN_BUDGET"] = "100"
        self.set_goal()
        state = self.goal.read_state(SESSION)
        start = self.goal.parse_time(state["created_at"])
        self.write_transcript([(start + dt.timedelta(seconds=1), "a", {"input_tokens": 500, "output_tokens": 0})])
        result = self.run_hook()
        self.assertEqual(result["decision"], "block")
        self.assertIn("budget", result["reason"])
        self.assertEqual(self.goal.read_state(SESSION)["status"], "budget_limited")
        self.assertIsNone(self.run_hook())

    def test_feature_flag_off_disables_hook(self):
        self.set_goal()
        (self.root / "proj" / ".claude" / "goal-config.json").write_text(
            json.dumps({"features": {"goals": False}}), encoding="utf-8")
        self.assertIsNone(self.run_hook())


class CommandGenerationTests(GoalTestCase):
    """Regression tests for script_command() path resolution.

    GoalTestCase.setUp() sets CLAUDE_PROJECT_DIR to a temp directory that has
    no .claude/skills/goal/ tree, simulating any project that uses the skill
    from a global install rather than a local copy.
    """

    def test_script_command_produces_absolute_paths(self):
        import shlex
        cmd = self.goal.script_command("test-session")
        parts = shlex.split(cmd)
        # Expected shape: [python, goal.py, '--session', session_id]
        self.assertEqual(len(parts), 4, f"unexpected command shape: {cmd}")
        python_path, script_path = parts[0], parts[1]
        self.assertTrue(
            pathlib.Path(python_path).is_absolute(),
            f"python interpreter is not absolute: {python_path}",
        )
        self.assertTrue(
            pathlib.Path(script_path).is_absolute(),
            f"script path is not absolute: {script_path}",
        )

    def test_script_command_does_not_use_project_relative_venv(self):
        import shlex
        cmd = self.goal.script_command("test-session")
        python_path = shlex.split(cmd)[0]
        self.assertFalse(
            python_path.startswith(".venv"),
            f"python path must not be a relative .venv reference: {python_path}",
        )

    def test_script_command_does_not_use_relative_script_path(self):
        import shlex
        cmd = self.goal.script_command("test-session")
        script_path = shlex.split(cmd)[1]
        self.assertFalse(
            script_path.startswith("."),
            f"script path must not be relative: {script_path}",
        )


class RequirementsTests(GoalTestCase):
    def test_add_requirement_stores_in_state(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "tests pass", "--check", "exit 0")
        reqs = self.goal.read_state(SESSION)["requirements"]
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]["id"], "r1")
        self.assertEqual(reqs[0]["description"], "tests pass")
        self.assertEqual(reqs[0]["check"], "exit 0")

    def test_add_requirement_no_check_is_manual(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "manual review")
        reqs = self.goal.read_state(SESSION)["requirements"]
        self.assertIsNone(reqs[0]["check"])

    def test_add_duplicate_id_rejected(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "first", "--check", "exit 0")
        with self.assertRaises(SystemExit):
            self.run_cli("add-requirement", "--id", "r1", "--description", "second", "--check", "exit 0")

    def test_verify_pass(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "succeeds", "--check", "exit 0")
        out = self.run_cli("verify")
        self.assertIn("[PASS]", out)
        self.assertIn("ACTION: report", out)

    def test_verify_fail(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "fails", "--check", "exit 1")
        out = self.run_cli("verify")
        self.assertIn("[FAIL]", out)
        self.assertIn("ACTION: work", out)

    def test_verify_no_requirements(self):
        self.set_goal()
        out = self.run_cli("verify")
        self.assertIn("No requirements", out)

    def test_complete_blocked_when_requirement_fails(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "must pass", "--check", "exit 1")
        with self.assertRaises(SystemExit):
            self.run_cli("complete", "--evidence", "done")

    def test_complete_succeeds_when_all_pass(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "succeeds", "--check", "exit 0")
        self.run_cli("complete", "--evidence", "tests pass")
        self.assertEqual(self.goal.read_state(SESSION)["status"], "complete")

    def test_complete_with_no_requirements_unchanged(self):
        self.set_goal()
        self.run_cli("complete", "--evidence", "all done")
        self.assertEqual(self.goal.read_state(SESSION)["status"], "complete")

    def test_verify_manual_requirement_not_blocking_complete(self):
        self.set_goal()
        self.run_cli("add-requirement", "--id", "r1", "--description", "manual check")
        self.run_cli("complete", "--evidence", "manually verified")
        self.assertEqual(self.goal.read_state(SESSION)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
