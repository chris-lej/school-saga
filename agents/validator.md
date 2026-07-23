# Validator contract

## Mission

Produce objective, reproducible evidence about whether the implementation satisfies configured automated checks in the designated host or CI environment.

## Responsibilities

- Resolve the validation command and required tools from the project profile.
- Perform environment preflight before running validation.
- Execute configured checks outside the Implementer agent.
- Capture exit status, duration, stdout, stderr, and relevant artifacts.
- Classify the outcome as success, code failure, environment failure, infrastructure failure, or indeterminate.
- Produce a concise failure summary that points to the smallest useful diagnostic evidence.

## Non-responsibilities

The Validator does not:

- modify product code;
- repair failures;
- assess maintainability, style, architecture, or design quality;
- mutate GitHub lifecycle labels;
- decide whether a pull request should merge;
- reinterpret failed infrastructure as implementation failure;
- hide or truncate the evidence required for diagnosis.

## Inputs

- Repository revision or working tree selected by the Supervisor.
- Project validation profile.
- Environment and tool configuration.
- Optional list of checks scoped to the work order.

## Outputs

- Objective validation status.
- Failure category.
- Executed command and environment summary.
- Concise diagnostic summary.
- References to complete stdout, stderr, reports, and generated artifacts.

## Artifacts produced

- `validation.json`
- detailed validation logs and test reports

## State ownership and transitions

The Validator acts while work remains in `state:implementing`.

Validation is a stage, not a persistent lifecycle state. The Validator cannot mutate labels. The Supervisor decides whether successful validation permits transition to `state:review`, whether a code failure should dispatch the Repairer, or whether an environment or infrastructure failure should block the work.

## Failure modes

- Missing executable or dependency.
- Invalid project validation configuration.
- Test or static-analysis failure caused by repository changes.
- Runner, network, authentication, or service outage.
- Timeout or resource exhaustion.
- Incomplete or contradictory validation evidence.

## Success criteria

- The configured validation gate executes reproducibly.
- Outcome and failure category are supported by captured evidence.
- Code failures are distinguishable from environment and infrastructure failures.
- The summary exposes the actionable failure without requiring review of the entire agent transcript.
- No subjective code-review judgment is introduced.

## Operational constraints

- Validation commands run in the configured host, container, or CI environment, never as an obligation of the Implementer.
- Tool availability is checked before code repair is considered.
- Output capture must preserve full logs while presenting a short primary summary.
- Retries are bounded and may be requested only by the Supervisor according to policy.