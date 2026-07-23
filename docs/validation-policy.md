# Validation policy

School Saga uses three validation tiers so routine pull requests protect runtime behavior without freezing temporary implementation details into permanent contracts.

## Tier 1: blocking runtime integrity

Required on every pull request:

- Godot project and configured main scene load successfully.
- Core smoke flows complete without runtime errors.
- The player scene loads and instantiates with valid referenced resources.
- Required autoloads and input actions exist.
- The Web export completes and its generated artifacts pass deployment validation.
- `git diff --check` passes.

Missing resources, parser failures, invalid scenes, runtime exceptions, and broken Web artifacts are always blocking.

## Tier 2: blocking behavioral contracts

Feature tests assert observable behavior. For directional player presentation this includes:

- all required idle and walk animation names exist;
- each animation has at least two non-null, loadable textures;
- movement selects the expected directional walk animation;
- stopping selects the corresponding directional idle animation;
- movement speed and facing state remain valid.

These tests must not require a specific image format, asset path, atlas layout, frame size, subresource ID, or placeholder artwork unless the repository deliberately promotes that detail into a stable contract.

The same principle applies to gameplay flow, camera behavior, save-state persistence, world-scene contracts, and deployment behavior: tests should assert externally meaningful outcomes rather than incidental internal structure.

## Tier 3: advisory implementation checks

Implementation conventions remain available through:

```bash
bash scripts/validate-advisory.sh
```

Current advisory checks cover the temporary placeholder sheet path, atlas count, and 18x26 layout. These checks are useful for diagnosing asset consistency but do not block normal pull requests.

## Classification examples

| Assertion | Classification | Blocking |
| --- | --- | --- |
| `player.tscn` loads | Runtime integrity | Yes |
| Every animation frame texture is non-null | Runtime integrity / behavior | Yes |
| Movement selects `walk_left` | Behavioral contract | Yes |
| Opening-flow save flags persist | Behavioral contract | Yes |
| Exported HTML references existing assets | Runtime integrity / deployment | Yes |
| Texture is PNG rather than SVG | Implementation detail | No |
| Atlas rectangles are exactly 18x26 | Implementation detail | No |
| Documentation names a temporary asset path | Style/documentation consistency | No |

The shared required gate is `bash scripts/validate-pr.sh`. Advisory checks are intentionally separate so implementation details cannot contradict the canonical runtime and behavioral contract.
