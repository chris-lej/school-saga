# Godot Coding Standards

## GDScript

- Use static typing where it improves contracts, editor support, and reviewability.
- Keep public methods, signals, exported properties, and resource interfaces stable unless the issue authorizes a breaking change.
- Prefer small scripts with one clear responsibility.
- Use descriptive node, signal, method, and variable names.
- Avoid hidden global state. Autoloads must have a documented project-level reason.
- Connect signals explicitly and disconnect lifecycle-sensitive connections safely.
- Avoid frame-loop work in `_process` or `_physics_process` unless continuous execution is required.
- Keep editor-only code guarded and separate from runtime behavior.

## Scenes and resources

- Prefer reusable scenes for independently meaningful components.
- Avoid brittle absolute node paths when an exported reference, unique node, or explicit dependency is more appropriate.
- Treat `.tscn` and `.tres` files as source code: changes must be intentional and reviewable.
- Do not hand-edit imported resource cache files.

## Changes

- Keep diffs bounded to the issue.
- Preserve existing conventions when they are compatible with the profile.
- Add or update tests and validation coverage when behavior changes.
- Document newly introduced subsystem boundaries or compatibility surfaces.
