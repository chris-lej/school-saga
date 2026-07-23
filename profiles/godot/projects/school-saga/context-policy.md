# School Saga Context Policy

The Supervisor assembles a bounded, immutable context package for each agent invocation. Agents do not scan the entire repository for policy or product knowledge.

## Shared context

Every context package includes:

- issue identifier, title, body, acceptance criteria, and current lifecycle state;
- exact repository, base commit, working branch, and active profile version;
- School Saga constitution;
- applicable technology-profile rules;
- artifact locations and output contract for the invoked role.

## Implementer

Include:

- issue and acceptance criteria;
- constitution;
- coding standards;
- project layout;
- relevant architecture documents and ADRs;
- only the Bible sections directly relevant to the requested behavior;
- prior repair instructions when this is a repair attempt.

Exclude:

- CI status and branch-protection decisions;
- unrelated lore and subsystem documentation;
- Reviewer conclusions from unrelated runs;
- instructions to validate, push, merge, or mutate labels.

## Validator

Include:

- validation profile;
- repository and commit identity;
- declared command, prerequisites, timeout, and expected outputs;
- implementation artifact only when needed to identify intended validation scope.

Exclude subjective code-review criteria and product lore that cannot affect objective execution.

## Reviewer

Include:

- issue and acceptance criteria;
- constitution and coding standards;
- relevant architecture, ADRs, and Bible excerpts;
- implementation artifact;
- repository diff or changed-file set.

Exclude CI status, deployment state, branch protection, and mergeability.

## Repairer

Include:

- original Implementer context;
- the classified validation or review failure artifact;
- bounded repair objective;
- prior attempt metadata needed to avoid repetition.

Do not include environment or infrastructure failures as repair instructions.

## Merger

Include:

- pull request identity and exact head commit;
- required checks and their current results;
- required approvals;
- branch-protection and merge-policy configuration;
- successful validation and review artifact references.

Exclude authority to reinterpret product requirements or repair code.

## Selection rules

Documents are selected by explicit mappings in the issue, changed paths, subsystem metadata, or profile index. Similarity search may rank candidates, but it may not silently turn an unrelated document into governing policy.

The context package records every included source and its commit SHA so the run can be reproduced.
