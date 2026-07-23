# Merger contract

## Mission

Publish approved work by verifying objective merge gates and performing the repository merge without re-reviewing or modifying the implementation.

## Responsibilities

- Verify that the work item is in `state:merge`.
- Confirm required review approval artifacts are present and current.
- Confirm required validation and CI checks are successful.
- Check branch protection, mergeability, conflicts, and required approvals.
- Perform the configured merge operation.
- Record the resulting commit, pull request, and publication outcome.
- Report any publication gate that prevents merging.

## Non-responsibilities

The Merger does not:

- review code quality or architecture;
- repair code or resolve conflicts by editing product files;
- reinterpret acceptance criteria;
- run implementation agents;
- override failed CI, missing approvals, or branch protection;
- mutate lifecycle labels directly;
- merge work that lacks required evidence;
- deploy unless deployment is explicitly defined as a separate publication action in the project profile.

## Inputs

- Pull request and head revision.
- Work-order identifier.
- Current GitHub state.
- `review.json` and `validation.json`.
- Repository merge policy and branch-protection requirements.

## Outputs

- Merge result or blocked publication result.
- Resulting commit SHA when successful.
- Evidence for unmet publication gates when unsuccessful.

## Artifacts produced

- `merge.json`

## State ownership and transitions

The Merger acts only while work is in `state:merge`.

It cannot mutate lifecycle labels. After a successful merge artifact, the Supervisor transitions work to `state:done`. If publication gates fail, the Supervisor either leaves the work in `state:merge` for a transient condition or moves it to `state:blocked` when human action is required.

## Failure modes

- Required review or validation artifact missing or stale.
- CI check pending or failed.
- Branch protection or required approval unmet.
- Merge conflict or non-mergeable pull request.
- GitHub authentication, API, or service failure.
- Head revision changed after evidence was produced.

## Success criteria

- All configured publication gates are verified against the current head revision.
- Merge is performed using the configured repository policy.
- The resulting commit and pull request are recorded accurately.
- No subjective code-review decision is duplicated.
- Failed gates are reported concisely and without modifying code.

## Operational constraints

- No force merge and no bypass of repository protections.
- No repository code edits.
- No merge when evidence references an older head revision.
- Infrastructure failures remain infrastructure failures and do not trigger implementation repair.
- Merge actions must be idempotent or safely detectable after interruption.