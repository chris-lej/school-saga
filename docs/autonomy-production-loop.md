# Guarded production Worker–Reviewer–Merger loop

This controller connects the existing guarded production Worker boundary to bounded Reviewer and Merger stages.

## Lifecycle

One cycle performs:

1. select one eligible `state:ready` issue;
2. run the guarded Worker and open a draft pull request;
3. review the exact expected head SHA;
4. return actionable findings to the Worker when changes are required;
5. review the updated exact head SHA;
6. merge only after approval and policy checks;
7. select the next eligible issue only when bounded multi-cycle mode allows it.

## Safety boundary

The loop is disabled by default. It requires:

- one active job;
- bounded issue count per invocation;
- bounded Worker fix iterations;
- exact reviewed-head and merge-head matching;
- emergency-stop checks between lifecycle stages;
- quarantine for stale heads, non-actionable reviews, repeated rejection, and Worker failures;
- no force push, history rewrite, direct writes to `main`, or execution of issue text.

Unattended always-on scheduling remains disabled.

## Initial operating mode

Begin with `max_issues_per_run=1` and an operator-triggered invocation. Inspect the Worker patch, validation evidence, review decision, reviewed head SHA, and merge result after every run.

Only after multiple successful supervised cycles should bounded multi-cycle mode be enabled. Always-on scheduling requires a separate promotion.

## Recovery

On halt or failure:

1. activate the emergency stop;
2. inspect persisted job, operation, validation, review, and merge records;
3. verify the pull request head and default branch have not moved unexpectedly;
4. quarantine an unsafe or repeatedly failing issue;
5. resume using the same persisted operation identifiers;
6. do not force-push or recreate existing branches, commits, reviews, or pull requests.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
