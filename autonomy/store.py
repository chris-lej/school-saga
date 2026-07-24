from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import AuditEvent, Job, JobState, utc_now

STORE_SCHEMA_VERSION = 1


class JsonJobStore:
    """Small local JSON store with atomic writes and idempotent operations."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": STORE_SCHEMA_VERSION,
            "jobs": {},
            "events": [],
            "operations": {},
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to read autonomy store {self.path}: {exc}") from exc
        if data.get("schema_version") != STORE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported store schema version: {data.get('schema_version')!r}; expected {STORE_SCHEMA_VERSION}"
            )
        for key in ("jobs", "events", "operations"):
            if key not in data:
                raise ValueError(f"Corrupt autonomy store: missing {key!r}")
        return data

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=self.path.name, dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def create(self, job: Job, operation_id: str) -> Job:
        data = self._load()
        existing_job_id = data["operations"].get(operation_id)
        if existing_job_id:
            return Job.from_dict(data["jobs"][existing_job_id])
        if job.job_id in data["jobs"]:
            raise ValueError(f"Job already exists: {job.job_id}")
        event = AuditEvent(
            event_id=f"{job.job_id}:created:{operation_id}",
            job_id=job.job_id,
            operation_id=operation_id,
            event_type="job.created",
            timestamp=utc_now(),
            to_state=job.state.value,
        )
        data["jobs"][job.job_id] = job.to_dict()
        data["events"].append(asdict(event))
        data["operations"][operation_id] = job.job_id
        self._save(data)
        return job

    def get(self, job_id: str) -> Job:
        data = self._load()
        try:
            payload = data["jobs"][job_id]
        except KeyError as exc:
            raise KeyError(f"Unknown job: {job_id}") from exc
        return Job.from_dict(payload)

    def list_jobs(self) -> list[Job]:
        data = self._load()
        jobs = [Job.from_dict(payload) for payload in data["jobs"].values()]
        return sorted(jobs, key=lambda job: job.created_at)

    def list_events(self, job_id: str | None = None) -> list[dict[str, Any]]:
        events = self._load()["events"]
        if job_id is None:
            return events
        return [event for event in events if event["job_id"] == job_id]

    def transition(self, job_id: str, target: JobState, operation_id: str) -> Job:
        data = self._load()
        existing_job_id = data["operations"].get(operation_id)
        if existing_job_id:
            if existing_job_id != job_id:
                raise ValueError(
                    f"Operation {operation_id!r} already belongs to job {existing_job_id!r}"
                )
            return Job.from_dict(data["jobs"][job_id])

        try:
            job = Job.from_dict(data["jobs"][job_id])
        except KeyError as exc:
            raise KeyError(f"Unknown job: {job_id}") from exc
        previous, current = job.transition(target)
        event = AuditEvent(
            event_id=f"{job.job_id}:transition:{operation_id}",
            job_id=job.job_id,
            operation_id=operation_id,
            event_type="job.transitioned",
            timestamp=job.updated_at,
            from_state=previous.value,
            to_state=current.value,
            details={"attempts": job.attempts},
        )
        data["jobs"][job_id] = job.to_dict()
        data["events"].append(asdict(event))
        data["operations"][operation_id] = job_id
        self._save(data)
        return job
