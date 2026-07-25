# Autonomy v2 live operator CLI

This slice supplies the executable composition boundary used by an operator-controlled launcher. It loads trusted deployment configuration, wires persistent deployment state and scheduler lease storage, verifies readiness through an injected concrete verifier, and emits machine-readable JSON.

## Commands

The CLI supports:

- `readiness`
- `observe`
- `single_cycle`
- `always_on`
- `pause`
- `resume`
- `drain`
- `status`
- `shutdown`

Every invocation requires `--config <trusted-json-path>`.

## Trusted configuration

The JSON file must contain the production deployment fields documented in `docs/autonomy-v2-production-deployment.md`, including:

- repository identity and local repository root;
- exact expected `main` SHA;
- path, command, mutation, and required-check allowlists;
- token and signing-key environment-variable names;
- emergency-stop environment-variable name;
- audit and deployment-state paths;
- exclusive lease owner;
- bounded cycle and retry settings;
- explicit `enabled: true`.

Secret values are never read from issue text and are not emitted in command output. Configuration fields whose names indicate tokens, secrets, or signing keys are redacted from returned data.

## Runtime composition

`ProductionComposition.build` creates:

- the trusted `ProductionDeploymentConfig`;
- environment-backed emergency stop;
- file-backed exclusive scheduler lease with heartbeat and stale-lease recovery;
- atomic deployment-state persistence;
- the bounded unattended scheduler;
- the operator deployment runtime.

The launcher must inject concrete readiness and lifecycle runtime adapters. This prevents fixture implementations from being silently used in production.

## Launch progression

1. Set the emergency-stop environment variable to the inactive value.
2. Load the GitHub token and readiness signing key from their declared sources.
3. Update the local checkout and record the exact current `main` SHA in trusted configuration.
4. Run `readiness` and inspect the JSON response.
5. Run `observe`; verify lease acquisition, readiness reference, and persisted state.
6. Run `single_cycle` for one small canary issue.
7. Inspect the branch, commit, checks, review, merge, audit records, and deployment state.
8. Use bounded `always_on` only after successful canary evidence.

## Lease recovery

The file lease contains an owner and UTC heartbeat timestamp. A different owner is rejected while the heartbeat is current. A stale lease may be replaced after the configured lease TTL. Operators must investigate stale ownership before allowing recovery.

## Incident response

1. Activate the emergency stop.
2. Issue `pause`, `drain`, or `shutdown` as appropriate.
3. Revoke or rotate the GitHub token when remote state is uncertain.
4. Preserve readiness, lease, deployment, job, operation, review, merge, and audit records.
5. Verify current `main` and trusted configuration against the readiness binding.
6. Quarantine uncertain issues and branches.
7. Require a new readiness report.
8. Restart in `observe` mode.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
