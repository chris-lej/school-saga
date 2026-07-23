# School Saga Validation

School Saga validation extends the generic Godot validation policy.

## Entry point

```text
./scripts/validate-pr.sh
```

The command is executed from the repository root. The script is responsible for invoking the appropriate Godot executable and project-specific checks. Until the script exists, validation must return a `configuration` failure rather than fabricate success.

## Required stages

1. Repository preflight
   - confirm `project.godot` and required profile files exist;
   - record repository and commit identity.
2. Environment resolution
   - resolve Godot lazily according to the technology profile;
   - record executable path and version.
3. Project load
   - load the project headlessly;
   - detect parse, resource, and startup failures.
4. Automated checks
   - execute project-defined unit, behavioral, integration, and static checks.
5. Result publication
   - write `validation.json` using the platform schema when available;
   - retain stdout, stderr, durations, and referenced artifacts separately.

## Outcome rules

- A successful command with incomplete required evidence is not a valid pass.
- Missing Godot is an environment failure.
- A missing validation script or invalid profile is a configuration failure.
- Runner outages and checkout corruption are infrastructure failures.
- Deterministic script, scene, resource, or test failures attributable to repository changes are implementation failures.

Only implementation failures may create a repair request. All other failure categories require Supervisor routing or human intervention.
