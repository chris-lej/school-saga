# Autonomy v2 guarded production draft-PR activation

This activation promotes the validated code-editing path into a manually invoked production-development mode for `chris-lej/school-saga`.

It authorizes only one bounded issue-to-draft-PR cycle at a time. Human review and human merge remain mandatory.

## Enabled capability

When explicitly enabled, a trusted runtime may:

1. load one eligible persisted issue job;
2. verify the production activation configuration and preflight gates;
3. create or resume the deterministic issue branch;
4. apply only the bounded allowlisted file-change plan;
5. run allowlisted repository validation;
6. create a real local Git commit;
7. emit guarded GitHub mutations for the issue claim, branch, and draft pull request;
8. persist a machine-readable activation report and audit trail;
9. exit after the single result.

## Capabilities that remain disabled

The activation configuration rejects any attempt to enable:

- automated production review;
- automatic ready-for-review transitions;
- automated merge;
- unattended or always-on scheduling.

Pull requests remain drafts. A person must inspect the patch, validation evidence, and audit trail before changing PR state or merging.

## Required configuration

The activation must be disabled by default and supplied through trusted runtime configuration. It requires:

- exact repository identity;
- explicit local repository root;
- expected default-branch SHA;
- eligible issue-label allowlist;
- path allowlist;
- validation-command allowlist;
- GitHub mutation allowlist;
- token source;
- required check policy;
- rollback procedure;
- externally controlled emergency-stop source.

Empty or incomplete configuration fails closed.

## Startup preflight

The production runtime must provide concrete preflight gates for:

- repository root and Git worktree identity;
- clean worktree;
- exact default-branch/base SHA;
- credentials loaded from the declared source;
- repository permissions for issue, branch, and draft-PR mutations;
- visibility of branch protection and required checks;
- required validation commands present in the allowlist;
- emergency-stop source reachable and inactive;
- production review, ready-for-review, merge, and unattended scheduling disabled.

Any failed gate prevents Worker execution.

## Emergency stop

Check the emergency stop before preflight-sensitive work and again before entering the guarded Worker. A halt must persist a report and preserve the job, workspace, and operation records for inspection and recovery.

Operators must know who owns the stop mechanism and how to revoke the GitHub token independently of the agent process.

## One-job launch procedure

1. Confirm the target issue is eligible and sufficiently bounded.
2. Update the local default branch and record its exact SHA.
3. Confirm the worktree is clean.
4. Review repository, path, command, and mutation allowlists.
5. Confirm review, ready-for-review, merge, and unattended scheduling are disabled.
6. Confirm the emergency stop works.
7. Run the manual one-job activation entrypoint.
8. Inspect the persisted activation report, commit, validation output, and draft PR.
9. Stop. Do not start another job until the previous result is reviewed.

## Recovery and rollback

On failure or halt:

- keep the emergency stop active;
- inspect the persisted operation IDs and audit events;
- do not delete branches until determining whether work must be retained;
- revoke or rotate the token if permissions or remote state are uncertain;
- remove an unneeded local issue branch only after verifying its commit is preserved elsewhere;
- fix configuration or repository state explicitly, then resume through the same persisted job and operation IDs.

The activation never force-pushes and never rewrites branch history.

## Promotion criteria

Before enabling automated Reviewer behavior, require several successful production draft-PR jobs with human inspection of:

- patch scope and quality;
- validation reliability;
- idempotent restart behavior;
- emergency-stop evidence;
- token scope and audit completeness;
- branch and expected-head protections.

Reviewer activation must be proposed separately. Merge activation remains a later, independent decision.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
