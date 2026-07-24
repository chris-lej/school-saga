from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import IssueWorkRequest, Job, JobState, RepositoryTarget
from .store import JsonJobStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="School Saga autonomy v2 local fixture CLI")
    parser.add_argument("--store", default=".autonomy/jobs.json", help="Path to the local JSON store")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a fixture job")
    create.add_argument("--repo", required=True, help="Repository in owner/name form")
    create.add_argument("--issue", required=True, type=int)
    create.add_argument("--title", required=True)
    create.add_argument("--body", default="")
    create.add_argument("--operation-id", required=True)

    inspect = subparsers.add_parser("inspect", help="Inspect one job")
    inspect.add_argument("job_id")

    subparsers.add_parser("list", help="List jobs")

    transition = subparsers.add_parser("transition", help="Transition one job")
    transition.add_argument("job_id")
    transition.add_argument("state", choices=[state.value for state in JobState])
    transition.add_argument("--operation-id", required=True)

    events = subparsers.add_parser("events", help="List audit events")
    events.add_argument("--job-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = JsonJobStore(Path(args.store))

    if args.command == "create":
        owner, separator, name = args.repo.partition("/")
        if not separator or not owner or not name:
            raise SystemExit("--repo must use owner/name form")
        job = Job(
            repository=RepositoryTarget(owner=owner, name=name),
            request=IssueWorkRequest(issue_number=args.issue, title=args.title, body=args.body),
        )
        result = store.create(job, args.operation_id)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "inspect":
        print(json.dumps(store.get(args.job_id).to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "list":
        print(json.dumps([job.to_dict() for job in store.list_jobs()], indent=2, sort_keys=True))
        return 0

    if args.command == "transition":
        result = store.transition(args.job_id, JobState(args.state), args.operation_id)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "events":
        print(json.dumps(store.list_events(args.job_id), indent=2, sort_keys=True))
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
