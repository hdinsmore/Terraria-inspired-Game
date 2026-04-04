from __future__ import annotations
from typing import TYPE_CHECKING, Sequence
if TYPE_CHECKING:
    from physics_engine import PhysicsEngine
    import numpy as np
    import pygame as pg

from settings import MAP_SIZE, TILE_SIZE

class SpriteMovement:
    def __init__(self, physics_engine: PhysicsEngine):
        self.tile_map: np.ndarray = physics_engine.tile_map
        self.names_to_ids: dict[str, int] = physics_engine.names_to_ids
        self.max_x = MAP_SIZE[0] * TILE_SIZE
        self.max_y = MAP_SIZE[1] * TILE_SIZE
        self.tile_collision_update: callable = physics_engine.collision_detection.tile_collision_update

        self.key_move_left: int = physics_engine.key_bindings['move left']
        self.key_move_right: int = physics_engine.key_bindings['move right']
        self.key_jump: int = physics_engine.key_bindings['jump']

        self.active_states: set[str] = {'jumping', 'mining', 'chopping'} # TODO: revisit this line in case more relevant states are added

    def move_sprite(self, sprite: pg.sprite.Sprite, direction_x: int, dt: float) -> None:
        if direction_x:
            if hasattr(sprite, 'underwater') and sprite.underwater:
                direction_x = 0.5 if direction_x > 0 else -0.5
            self.update_movement_x(sprite, direction_x, dt)  
        else:
            sprite.direction.x = 0
            if hasattr(sprite, 'state') and sprite not in self.active_states:
                sprite.state = 'idle'
                sprite.frame_index = 0
        
        self.tile_collision_update(sprite, 'x')
        self.update_movement_y(sprite, dt) # always called since it handles gravity
        self.tile_collision_update(sprite, 'y')

    def update_movement_x(self, sprite: pg.sprite.Sprite, direction_x: int, dt: float) -> None:
        sprite.direction.x = direction_x
        sprite.rect.x += sprite.direction.x * sprite.move_speed * dt
        sprite.rect.x = max(0, min(sprite.rect.x, self.max_x - sprite.rect.width)) # prevent moving off the map horizontally
        if hasattr(sprite, 'state') and sprite.state == 'idle': # avoid overwriting an active state
            sprite.state = 'walking'
    
    def update_movement_y(self, sprite, dt: float) -> None:
        # getting the average of the downward velocity
        sprite.direction.y += (sprite.gravity // 2) * dt
        sprite.rect.y += sprite.direction.y * dt
        sprite.direction.y += (sprite.gravity // 2) * dt

        sprite.rect.y = min(sprite.rect.y, self.max_y - sprite.rect.height) # don't add a top limit until the space biome borders are set, if any

    def jump(self, sprite: pg.sprite.Sprite, pressed_keys: Sequence[bool]) -> None:
        if pressed_keys[self.key_jump] and sprite.grounded and sprite.state != 'jumping':
            sprite.direction.y -= sprite.jump_height
            sprite.grounded = False
            sprite.state = 'jumping'
            sprite.frame_index = 0

    def update(self, player: pg.sprite.Sprite, held_keys: Sequence[bool], pressed_keys: Sequence[bool], dt: float):
        self.move_sprite(player, held_keys[self.key_move_right] - held_keys[self.key_move_left], dt)
        self.jump(player, pressed_keys)