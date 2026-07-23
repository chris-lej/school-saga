# Project Profiles

Project profiles make the autonomous engineering organization project agnostic.

The platform owns orchestration, lifecycle, artifacts, logging, and agent execution. A profile supplies the project-specific facts required to perform work safely and consistently.

## Profile hierarchy

Profiles are layered from general to specific:

```text
profiles/
  <technology>/
    profile.yaml
    constitution.md
    coding-standards.md
    validation.md
    projects/
      <project>/
        profile.yaml
        constitution.md
        context-policy.md
        project-layout.md
        validation.md
        coding-standards.md
        architecture/
        bibles/
        adr/
```

A project profile may inherit technology-level defaults and override them explicitly. Unstated values are never inferred by agents.

## Required project-profile capabilities

A complete profile defines:

- identity and supported technology versions;
- repository layout and ownership boundaries;
- engineering constitution;
- coding and documentation standards;
- validation commands, prerequisites, and expected evidence;
- context assembly policy per agent role;
- architecture and product knowledge locations;
- forbidden operations and escalation conditions.

## Resolution rules

The Supervisor resolves an active profile before dispatching work. It combines the technology profile and project profile into an immutable context package for a single run.

Agents do not discover project policy independently. They consume only the resolved context package and the artifacts declared by their contracts.

## Reference implementation

`profiles/godot/projects/school-saga/` is the first project profile and the reference implementation for the profile system.
