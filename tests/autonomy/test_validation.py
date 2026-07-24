from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from autonomy.contracts import IssueWorkRequest, Job, RepositoryTarget
from autonomy.store import JsonJobStore
from autonomy.validation import (
    SubprocessCommandRunner,
    ValidationCommand,
    ValidationService,
    ValidationStatus,
    ValidationStepResult,
)


class FakeRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def run(self, command, *, cwd, environment, max_output_chars):
        result = self.results[self.calls]
        self.calls += 1
        return result


class ValidationServiceTests(unittest.TestCase):
    def create_job(self, root: Path):
        store = JsonJobStore(root / "jobs.json")
        job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=43, title="Validation service"),
        )
        store.create(job, "create-job")
        return store, job

    def test_multiple_steps_aggregate_and_same_operation_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, job = self.create_job(root)
            runner = FakeRunner(
                [
                    ValidationStepResult("unit", ValidationStatus.PASSED, 0),
                    ValidationStepResult("gate", ValidationStatus.FAILED, 1, stderr="failed"),
                ]
            )
            service = ValidationService(
                store,
                runner,
                commands=(
                    ValidationCommand("unit", ("unit",)),
                    ValidationCommand("gate", ("gate",)),
                ),
                cwd=root,
            )

            first = service.validate(job.job_id, "validate-1")
            second = service.validate(job.job_id, "validate-1")

            self.assertEqual(first.status, ValidationStatus.FAILED)
            self.assertEqual(second.status, ValidationStatus.FAILED)
            self.assertEqual(runner.calls, 2)
            self.assertEqual(store.count_events(job.job_id, "validation.completed"), 1)

    def test_distinct_retry_operation_runs_again_and_increments_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, job = self.create_job(root)
            runner = FakeRunner(
                [
                    ValidationStepResult("unit", ValidationStatus.FAILED, 1),
                    ValidationStepResult("unit", ValidationStatus.PASSED, 0),
                ]
            )
            service = ValidationService(
                store,
                runner,
                commands=(ValidationCommand("unit", ("unit",)),),
                cwd=root,
            )

            first = service.validate(job.job_id, "validate-1")
            second = service.validate(job.job_id, "validate-2")

            self.assertEqual(first.attempt, 1)
            self.assertEqual(second.attempt, 2)
            self.assertTrue(second.passed)
            self.assertEqual(runner.calls, 2)

    def test_subprocess_runner_success_failure_and_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = SubprocessCommandRunner()
            environment = {"PATH": str(Path(sys.executable).parent)}

            success = runner.run(
                ValidationCommand("success", (sys.executable, "-c", "print('ok')"), 5),
                cwd=root,
                environment=environment,
                max_output_chars=100,
            )
            failure = runner.run(
                ValidationCommand("failure", (sys.executable, "-c", "raise SystemExit(2)"), 5),
                cwd=root,
                environment=environment,
                max_output_chars=100,
            )
            timeout = runner.run(
                ValidationCommand("timeout", (sys.executable, "-c", "import time; time.sleep(2)"), 1),
                cwd=root,
                environment=environment,
                max_output_chars=100,
            )

            self.assertEqual(success.status, ValidationStatus.PASSED)
            self.assertEqual(failure.status, ValidationStatus.FAILED)
            self.assertEqual(timeout.status, ValidationStatus.TIMED_OUT)


if __name__ == "__main__":
    unittest.main()
