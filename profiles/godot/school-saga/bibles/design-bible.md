# School Saga Design Bible

Status: Living document
Version: 0.1
Source: migrated from `chris-lej/school-saga-1` commit `005325265e674b4c21428777fa9f8ba64f80b5d6`

## Vision

School Saga is a nostalgic, exploration-driven RPG about what it felt like to be fifteen in Brazil during the 1990s and early 2000s.

It is not primarily a game about school as an institution. School is the stage for discovering people, places, routines, rumors, fears, jokes, affection, and memories.

The intended player feeling is simple:

> There is always more to discover.

## Audience

The primary audience is people who grew up in Brazil during the 1990s and early 2000s. The game should remain welcoming to players from elsewhere, but it must not dilute its cultural identity to become generic.

## Player fantasy

The player creates a fifteen-year-old protagonist who is the new student at a fictionalized school inspired primarily by Dom Bosco in the Ahú neighborhood of Curitiba.

The player is not a chosen hero. They are a teenager entering a world that already exists.

## Core experience

The player wakes up, goes to school, attends classes, navigates recess, participates in extracurricular activities, explores nearby places, forms relationships, hears rumors, and uncovers secrets.

The game rewards attention more than optimization. A player succeeds by noticing routines, remembering details, interpreting people, and being curious enough to test possibilities.

## Design pillars

### Curiosity over completion
The game should make the player wonder what else exists rather than push them to clear a checklist.

### Attention is the core mechanic
Secrets emerge from noticing time, place, behavior, sound, weather, light, repetition, and contradiction.

### Memories over missions
The player should remember moments, not objective text.

### Relationships are felt, not measured
Friendship, friction, trust, romance, and distance are inferred through behavior. No visible friendship bars.

### Shared experiences shape relationships
Relationships develop through overlapping lives: sitting together, playing sports, skipping class, witnessing something strange, sharing embarrassment, or simply being present repeatedly.

### The world does not revolve around the player
NPCs have schedules, friendships, disagreements, rumors, and changes that may occur off-screen.

### Humor creates connection
Humor is warm, observant, awkward, defensive, affectionate, and human. It should not become constant gag density or broad stupidity.

### Lighting drives mood
Lighting communicates emotional tone before dialogue. Morning suggests possibility, afternoon can feel reflective or energetic, and dusk can invite mystery or fear.

### Brazilian specificity is a strength
Architecture, sidewalks, gates, dogs, utility poles, wires, sounds, food, school rituals, social customs, and language should feel unmistakably Brazilian.

### Exaggerated emotion, grounded context
NPC reactions may become visually exaggerated at designed moments. The exaggeration should amplify remembered emotion rather than create random chaos.

### Authored simulation, AI enrichment
NPCs should be built from authored roles, schedules, relationships, traits, memories, and rules. Generative AI may enrich expression later, but core gameplay must remain coherent, deterministic, testable, and playable without external AI services.

## Structure

The game begins as a sandbox with recurring schedules and consequences. Chapters may emerge from accumulated choices and obligations rather than from a strictly linear campaign.

Examples include academic consequences such as recuperação after repeated absences. Hard failure is possible when life circumstances justify it, but failure should produce meaning rather than arbitrary punishment.

## Time

Time should flow continuously enough for routines to feel real, while avoiding minute-by-minute anxiety. Classes, recess, extracurricular activities, after-school windows, and evening events provide natural anchors.

Many discoveries should be time-dependent rather than quest-dependent. Patterns repeat so players can learn the world. Missing one event should usually create another future opportunity, variation, or consequence rather than permanently destroying the experience.

## Social simulation

- Relationships are inferred from actions and behavior.
- NPC-to-NPC relationships evolve independently.
- Friendships can deepen, drift, fracture, and sometimes recover.
- Romance exists from the beginning as a possibility, but must emerge through sustained shared experience.
- Rumors may be true, false, exaggerated, misunderstood, or conditionally true.
- Reliability is a learned character trait; some people gossip, embellish, or deliberately mislead.

## Secrets and achievements

Secrets are a major long-term source of progression. Some should depend on unusual combinations of time, place, person, prior knowledge, and player behavior.

Achievements should be rare and meaningful. Most should remain hidden until earned. They acknowledge unusual experiences rather than prescribe tasks.

The early achievement concept `Curious Mind` rewards an unexpected act of exploration, not completion of a mandatory objective.

## Visual direction

The visual target is high-end, highly detailed pixel art with painterly lighting, expressive animation, and strong environmental specificity.

The world should feel lived in rather than pristine:

- uneven and cracked sidewalks
- faded paint and chipped walls
- gates and dogs behind them
- dense overhead wires and utility poles
- mismatched tiles and practical construction
- humid vegetation and Curitiba trees
- school courtyards full of overlapping activity

The chosen visual reference is the final concept image produced during discovery: detailed pixel art, strong lighting, naturalistic composition, warmth, texture, and emotional atmosphere.

## Opening atmosphere

The game begins on an ordinary morning rather than with a dramatic cutscene.

The first emotional impression is light and possibility. The player wakes, makes a small breakfast decision, and steps into a neighborhood alive with dogs barking behind gates, distant traffic, birds, someone washing the sidewalk, and the sounds of the city beginning its day.

## Open questions

- What is the central long-running mystery?
- What are the major endings?
- Who is the protagonist's first friend?
- Which memories form the initial cast?
- What exact school-year period and calendar structure will be used?
- How large is the first neighborhood map?
- What hard failure states belong in the vertical slice versus the full game?
