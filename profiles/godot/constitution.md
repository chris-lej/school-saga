# Godot Profile Constitution

These rules apply to every project inheriting the Godot technology profile unless a project profile explicitly strengthens them.

## Engineering rules

1. Preserve compatibility with the project's declared Godot version.
2. Prefer clear scene composition and explicit ownership over implicit runtime coupling.
3. Keep gameplay logic testable without requiring editor interaction where practical.
4. Do not edit imported artifacts or generated metadata as source-of-truth files.
5. Do not introduce addons or third-party dependencies without explicit project authorization.
6. Avoid broad subsystem rewrites when a bounded change satisfies the requirement.
7. Treat resource paths, node paths, signals, and exported properties as compatibility surfaces.
8. Keep editor tooling separate from runtime behavior.
9. Validation evidence must distinguish project defects from missing executables, unavailable assets, or runner failures.
10. Agents must escalate when the declared engine version, project entry point, or validation command cannot be resolved.

## Override policy

Project constitutions may add stricter requirements. They may not silently weaken these rules. Any exception must be recorded as a project ADR and included in the active context package.
