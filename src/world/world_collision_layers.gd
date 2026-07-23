extends RefCounted
class_name WorldCollisionLayers

const PLAYER_LAYER: int = 1
const WORLD_SOLID_LAYER: int = 2
const INTERACTABLE_LAYER: int = 3
const EXIT_LAYER: int = 4
const FOREGROUND_OCCLUSION_LAYER: int = 5

const PLAYER: int = 1 << (PLAYER_LAYER - 1)
const WORLD_SOLID: int = 1 << (WORLD_SOLID_LAYER - 1)
const INTERACTABLE: int = 1 << (INTERACTABLE_LAYER - 1)
const EXIT: int = 1 << (EXIT_LAYER - 1)
const FOREGROUND_OCCLUSION: int = 1 << (FOREGROUND_OCCLUSION_LAYER - 1)

const PLAYER_COLLISION_MASK: int = WORLD_SOLID
const WORLD_SOLID_COLLISION_MASK: int = PLAYER
const SENSOR_COLLISION_MASK: int = PLAYER
