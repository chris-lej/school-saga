# Agent contracts

This directory defines the canonical organizational contracts for autonomous roles in the School Saga engineering organization.

Agents are bounded roles, not personalities. Each contract uses the same structure:

1. Mission
2. Responsibilities
3. Non-responsibilities
4. Inputs
5. Outputs
6. Artifacts produced
7. State ownership and transitions
8. Failure modes
9. Success criteria
10. Operational constraints

The contracts are normative. Prompts and executable implementations must conform to them. When implementation behavior conflicts with a contract, the contract is the source of truth until amended through an architecture decision.

## Initial roles

- Supervisor
- Implementer
- Validator
- Reviewer
- Repairer
- Merger

No agent may silently absorb another role's responsibilities. Cross-role coordination occurs through GitHub state and structured artifacts.