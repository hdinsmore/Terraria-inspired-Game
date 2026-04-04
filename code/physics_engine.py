from __future__ import annotations
from typing import TYPE_CHECKING, Sequence
if TYPE_CHECKING:
    from main import Main
    from input_manager import Keyboard
    import numpy as np
    
import pygame as pg
from math import ceil

from settings import TILE_SIZE
from collision_detection import CollisionDetection, CollisionMap
from sprite_movement import SpriteMovement

class PhysicsEngine:
    def __init__(self, game_obj: Main):
        self.tile_map: np.ndarray = game_obj.proc_gen.tile_map
        self.names_to_ids: dict[str, int] = game_obj.proc_gen.names_to_ids
        self.ids_to_names: dict[int, str] = game_obj.proc_gen.ids_to_names

        self.keyboard: Keyboard = game_obj.input_manager.keyboard
        self.key_bindings: dict[str, int] = self.keyboard.key_bindings
        self.held_keys: Sequence[bool] = self.keyboard.held_keys
        self.pressed_keys: Sequence[bool] = self.keyboard.pressed_keys
        
        self.cam_offset: pg.Vector2 = game_obj.cam.offset

        self.collision_map = CollisionMap(self)
        self.collision_detection = CollisionDetection(self)

        self.sprite_movement = SpriteMovement(self)

    def step_over_tile(self, sprite, tile_x, tile_y) -> bool:
        if sprite.direction.y == 0:
            above_tiles = []
            for i in range(1, ceil(sprite.rect.height / TILE_SIZE)): # check if the number of air tiles above the given tile is at least equal to the sprite's height
                above_tiles.append(self.tile_map[tile_x, tile_y - i])
            above_tiles.append(self.tile_map[tile_x - 1, tile_y - 2]) # also check if the tile above the player's head is air
            return all(tile_id == self.names_to_ids['air'] for tile_id in above_tiles)
        return False

    def update(self, player: pg.sprite.Sprite, dt: float) -> None:
        self.sprite_movement.update(player, self.keyboard.held_keys, self.keyboard.pressed_keys, dt)


class WaterFlow:
    def __init__(self, physics_engine: PhysicsEngine):
        self.tile_map: np.ndarray = physics_engine.tile_map
        self.names_to_ids: dict[str, int] = physics_engine.names_to_ids
        self.ids_to_names: dict[int, str] = physics_engine.ids_to_names
