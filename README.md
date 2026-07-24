# School Saga

School Saga is a Godot 4.7.1 project focused on a fictional Brazilian school-life vertical slice.

## Current playable route

The active repository contains a first-pass continuous route:

`home morning → Rua do Monte neighborhood threshold → Colégio Monte Araucária first day → return home`

The route includes character naming, a breakfast choice, neighborhood atmosphere, school courtyard routines, classroom seating, relationship consequences, independent NPC behavior, recess basketball, an unresolved rumor, return-home consequences, and completed-day persistence.

## Runtime foundations

The project also includes:

- reusable 2D player movement and directional presentation;
- bounded follow-camera behavior;
- walkable-world collision layers and scene validation;
- save/load and scene-transition services;
- Godot Web export and Vercel deployment contracts;
- focused Godot tests and an end-to-end vertical-slice route test.

## Validation

Run the shared repository gate:

```bash
bash scripts/validate-pr.sh
```

Advisory placeholder-asset checks are available separately:

```bash
bash scripts/validate-advisory.sh
```

## Migration status

Phase 5 migrated the retained gameplay, runtime, deployment, validation, and product-documentation contracts from `chris-lej/school-saga-1`.

Legacy Worker-01, Reviewer-01, Merge-01, supervisor, dispatch, and related autonomous-agent infrastructure are intentionally excluded from the active game repository.

See:

- `docs/migration-parity.md` for migration status and closeout criteria;
- `docs/vertical-slice.md` for the product target;
- `docs/player-foundation.md` and `docs/world-scene-contract.md` for runtime authoring contracts;
- `docs/validation-policy.md` for blocking and advisory validation;
- `docs/web-deployment.md` for Web export and deployment.

## Next product work

Remaining work is product development rather than undiscovered migration parity: a fully walkable authored neighborhood, production art and animation, broader save/resume entry points, accessibility and browser/controller testing, and final exported-build review.
