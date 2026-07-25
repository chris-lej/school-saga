# Autonomy v2 production readiness gate

The readiness gate is a mutation-free preflight for the guarded production Worker–Reviewer–Merger loop.

It does not enable autonomous development. It produces a signed, time-bounded report proving that the exact repository state and trusted runtime configuration passed the required checks.

## Required evidence

A READY report must cover:

- exact repository identity and current `main` SHA;
- clean local worktree and branch-protection visibility;
- required status checks and validation commands;
- repository path, command, and GitHub mutation allowlists;
- declared and verified token scopes;
- externally controlled emergency stop;
- writable audit persistence and restart-recovery evidence;
- one-active-job policy, bounded fix iterations, and quarantine policy;
- continued disabling of unattended scheduling, force push, and direct writes to `main`.

## Report binding

Each report contains:

- operator identity;
- issue time and expiry time;
- repository and exact SHA;
- deterministic configuration digest;
- every readiness gate and its result;
- unresolved risks;
- HMAC-SHA256 signature metadata.

A report is invalid when:

- it is not READY;
- its signature does not verify;
- it has expired;
- `main` moved;
- configuration changed;
- repository identity changed.

The production loop must receive and verify the report before performing a live activation.

## Operator procedure

1. Update the local checkout and record the exact `main` SHA.
2. Confirm the worktree is clean.
3. Review all path, command, mutation, check, and token-scope allowlists.
4. Exercise the emergency stop independently of the agent runtime.
5. Confirm audit storage is writable and restart recovery has current evidence.
6. Run the readiness evaluator without GitHub mutations.
7. Inspect every gate and unresolved risk.
8. Retain the signed READY report with the activation audit record.
9. Start only one supervised canary cycle before broader operation.

## Expiry and revocation

Readiness reports must use a bounded lifetime of at most 24 hours. Re-run readiness after any repository movement, configuration edit, permission change, emergency-stop change, or incident.

Operators may revoke readiness by rotating the signing key, activating the emergency stop, revoking the GitHub token, or changing the trusted activation configuration.

## Incident response

On any unexpected mutation or state mismatch:

1. activate the emergency stop;
2. revoke or rotate the GitHub token;
3. preserve the readiness report, job store, operation records, and audit events;
4. compare the report SHA and configuration digest with the current runtime;
5. quarantine affected issues and branches;
6. invalidate prior reports and require a new readiness evaluation.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
