# Godot Validation Profile

Validation is executed outside the Implementer and produces objective evidence.

## Executable resolution

Resolve the Godot executable lazily when validation begins:

1. `GODOT_BIN`
2. `GODOT_EXECUTABLE`
3. `godot4` on `PATH`
4. `godot` on `PATH`

Failure to resolve an executable is an `environment` failure, not an implementation defect.

## Baseline validation sequence

1. Confirm `project.godot` exists.
2. Resolve the declared engine version and executable.
3. Load the project in headless mode.
4. Parse scripts and resources.
5. Execute project-defined tests or validation scripts.
6. Record command, exit code, duration, stdout, stderr, and produced artifacts.

## Classification

- `implementation`: deterministic project or test failure caused by repository changes.
- `environment`: missing executable, SDK, display service, permission, or external asset.
- `infrastructure`: runner, network, checkout, storage, or CI-provider failure.
- `configuration`: invalid or incomplete project profile.

Only actionable implementation failures may be routed to Repairer.
