# Visual Style Validation

Status: Migrated prototype

## Scene

Open `res://scenes/locations/neighborhood_visual_validation.tscn` in Godot.

The scene validates one ordinary morning exterior at the street/courtyard threshold near Colégio Monte Araucária. It is a visual prototype only: it does not add traversal, dialogue, quests, or new canon beyond the already-approved fictional school identity.

## Intended Memory Or Feeling

The scene should create the feeling of stepping outside on a school morning and sensing that the neighborhood is already awake. The mood should read through warm light, damp sidewalk texture, lived-in construction, and small ambient motion before any dialogue is needed.

## Required Visual Signals

- detailed pixel-art composition rendered at a fixed 320x180 internal resolution;
- painterly morning light and soft shadow over the street;
- gates, utility poles, dense wires, uneven sidewalk slabs, cracked pavement, faded paint, and practical buildings;
- vegetation with humid, Curitiba-adjacent texture without naming or reproducing a real place;
- small expressive ambient animation: water movement, laundry sway, and a dog behind the gate.

## Pixel And Camera Constraints

- The scene renders through a `SubViewport` sized to `320x180`.
- The viewport is displayed only at integer scale and centered inside the game window.
- Filtering is nearest-neighbor for the viewport and canvas items.
- The camera is fixed at `(160, 90)` with zoom `(1, 1)`.
- Camera position and rotation smoothing are disabled.
- Prototype art must be snapped to whole-pixel coordinates unless a deliberate light overlay requires sub-pixel softness.

## Performance Constraints

- This prototype uses procedural drawing only; no imported texture memory is required.
- The visual canvas redraws once per frame for ambient animation.
- Keep animated procedural elements small and localized until a real asset pipeline exists.
- Avoid post-processing, particles, dynamic shadows, pathfinding, and simulation systems in this validation scene.
- Any future expansion should be measured in Godot's profiler before adding more animated layers.

## Validation

The shared gate loads the scene headlessly through `scripts/validate-pr.sh`. This confirms scene and script integrity but does not replace manual visual inspection in the Godot editor or exported Web build.

## Current Limits

- The composition is a validation target, not final art.
- Audio is covered by the existing neighborhood atmosphere prototype, not this visual-only scene.
- The scene does not prove player navigation, collision, or NPC scheduling.
