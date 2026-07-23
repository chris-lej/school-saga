# Vertical Slice: First School Day

## Goal

Prove that School Saga creates the feeling that there is always more to discover.

Target playtime: 30–60 minutes.

## Setting

The slice takes place at **Colégio Monte Araucária**, a fully fictional Curitiba school with its own history, traditions, architecture, and folklore.

## Player impressions

1. This feels specifically Brazilian.
2. These people have lives beyond me.
3. I want to return because I did not see everything.

## Flow

1. Wake up at home in soft, hopeful morning light.
2. Eat or skip breakfast; the choice produces a subtle later consequence.
3. Step into a lived-in neighborhood: someone washing the sidewalk, dogs behind gates, traffic, birds, overhead wires, uneven sidewalks, walls, and vegetation.
4. Travel to Colégio Monte Araucária; the first version may automate most of the route.
5. Enter a courtyard already alive with independent activity.
6. Attend class and choose where to sit, creating the first shared experience.
7. Explore recess, observe groups, approach someone, or join a simple basketball activity.
8. Notice an NPC-to-NPC relationship moment that happens without player involvement.
9. Hear one unverified rumor that invites attention but creates no quest marker.
10. Return home with subtle consequences and evidence that unseen events continued elsewhere.

## Systems demonstrated

- movement and interaction
- lightweight character creation
- time anchors and NPC routines
- observational internal thoughts
- relationships expressed through behavior
- rumor delivery
- simple basketball interaction
- environmental sound and mood lighting
- save/load

## Initial cast scope

- 3–5 classmates
- 1 teacher
- 1 parent or guardian
- 1 ambient neighborhood character

Only two classmates need meaningful first-pass relationship behavior.

All characters and institutions are fictionalized, even when their emotional basis comes from real memories.

## Out of scope

- full school year
- full neighborhood traversal
- generative NPC dialogue
- resolved romance
- complete academic simulation
- combat
- central mystery resolution
- direct reproduction of any real school or person

## Current migrated implementation

The active repository now contains the first-pass runtime for the opening morning, neighborhood atmosphere, first school-day class flow, relationship consequences, recess basketball, and unresolved rumor observation.

The school sequence begins after the neighborhood threshold and keeps scope to arrival, an active courtyard, four authored classmate routines, a short class seating moment, and one recess basketball interaction. Seating and basketball consequences are recorded as shared memories and later behavior rather than shown as relationship meters.

The first rumor is authored data attached to Bia's observable reliability pattern. It can be overheard only by lingering at the canteen shade after recess basketball, combines time, place, and repeated-attention clues, and remains unresolved at slice end instead of becoming a tracked objective.

Reusable player movement, bounded follow-camera behavior, walkable-world collision contracts, Web export, deployment validation, and focused visual prototypes are available as supporting foundations. The current main flow does not yet connect every listed step into a single continuous 30–60 minute playthrough, and the return-home step remains future integration work.

## Acceptance criteria

- The first-day flow is playable end to end.
- The setting reads as Brazilian without explanatory text.
- Colégio Monte Araucária feels like a distinct institution rather than a generic school.
- One small choice creates a later non-binary consequence.
- One NPC-to-NPC behavior occurs independently.
- One rumor or secret encourages return play.
- No friendship meter, quest marker, or prescriptive internal thought is required.
