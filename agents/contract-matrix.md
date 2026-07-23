# Agent responsibility matrix

This matrix is a quick normative reference. Detailed contracts remain authoritative.

| Capability | Supervisor | Implementer | Validator | Reviewer | Repairer | Merger |
|---|---:|---:|---:|---:|---:|---:|
| Select work | Owner | No | No | No | No | No |
| Mutate lifecycle labels | Owner | No | No | No | No | No |
| Assemble context package | Owner | Consumer | Consumer | Consumer | Consumer | Consumer |
| Modify product code | No | Owner | No | No | Repair-only | No |
| Run objective validation | Dispatch | No | Owner | No | No | Verify artifact only |
| Evaluate code quality | No | No | No | Owner | Address assigned findings | No |
| Classify failure | Owner | Report only | Evidence and category | Findings only | Reject unsupported category | Publication gate category |
| Repair code failure | Dispatch | Initial implementation only | No | No | Owner | No |
| Inspect CI status | Route evidence | No | May produce CI evidence | No | No | Owner for merge gate |
| Check mergeability and branch protection | No | No | No | No | No | Owner |
| Merge pull request | Dispatch | No | No | No | No | Owner |
| Produce run summary | Owner | Implementation summary | Validation summary | Review summary | Repair summary | Merge summary |

## Boundary rules

1. No specialist mutates canonical lifecycle state.
2. The Implementer is not accountable for CI or validation execution.
3. The Reviewer must ignore CI, deployment, mergeability, and branch protection when forming its code-review decision.
4. The Validator reports objective facts and never repairs code.
5. The Repairer runs only against classified, actionable code or review failures.
6. The Merger verifies publication gates but does not duplicate code review.
7. The Supervisor coordinates roles but does not perform their specialist work.