from __future__ import annotations
from typing import TYPE_CHECKING, Sequence
if TYPE_CHECKING:
    from physics_engine import PhysicsEngine
    import numpy as np
    
import pygame as pg
from collections import defaultdict

from settings import TILE_SIZE, MAP_SIZE

class CollisionDetection:
    def __init__(self, physics_engine: PhysicsEngine):
        self.collision_map: CollisionMap = physics_engine.collision_map
        self.tile_map: np.ndarray = physics_engine.tile_map
        self.names_to_ids: dict[str, int] = physics_engine.names_to_ids
        self.ids_to_names: dict[int, str] = physics_engine.ids_to_names
        self.cam_offset: pg.Vector2 = physics_engine.cam_offset
        self.step_over_tile: callable = physics_engine.step_over_tile

        self.ramp_ids = {self.names_to_ids[tile] for tile in self.names_to_ids if 'ramp' in tile}
        self.liquid_ids = {self.names_to_ids['water']} # TODO: add lava

    def tile_collision_update(self, spr: pg.sprite.Sprite, axis: str) -> None:
        tiles_near = self.collision_map.search_map(spr)
        if not tiles_near: # surrounded by air
            spr.grounded = False
            spr.state = 'jumping' # the jumping graphic applies to both jumping/falling
            return
        has_underwater_attr = hasattr(spr, 'underwater')
        for tile in tiles_near:
            if spr.rect.colliderect(tile):
                tile_id = self.tile_map[tile.x // TILE_SIZE, tile.y // TILE_SIZE]
                if tile_id in self.ramp_ids:
                    self.ramp_collision(spr, tile, 'left' if 'left' in self.ids_to_names[tile_id] else 'right')
                else:
                    if tile_id not in self.liquid_ids:
                        if axis == 'x' and spr.direction.x:
                            self.tile_collision_x(spr, tile, 'right' if spr.direction.x > 0 else 'left')
                        elif axis == 'y' and spr.direction.y:
                            self.tile_collision_y(spr, tile, 'up' if spr.direction.y < 0 else 'down')
                if has_underwater_attr:
                        self.check_spr_underwater(spr)
    
    def tile_collision_x(self, sprite: pg.sprite.Sprite, tile: pg.Rect, direction: str) -> None:
        if not self.step_over_tile(sprite, tile.x // TILE_SIZE, tile.y // TILE_SIZE):
            if direction == 'right':
                sprite.rect.right = tile.left
            else:
                sprite.rect.left = tile.right

            sprite.state = 'idle'
        else:
            if sprite.grounded: # prevents some glitchy movement from landing on the side of a tile
                if direction == 'right':
                    sprite.rect.bottomright = tile.topleft
                else:
                    sprite.rect.bottomleft = tile.topright

        sprite.direction.x = 0

    @staticmethod
    def tile_collision_y(sprite: pg.sprite.Sprite, tile: pg.Rect, direction: str) -> None:
        if direction == 'up': 
            sprite.rect.top = tile.bottom
        
        elif direction == 'down':
            sprite.rect.bottom = tile.top
            if hasattr(sprite, 'grounded') and not sprite.grounded:
                sprite.grounded = True
            
            if hasattr(sprite, 'state') and sprite.state == 'jumping':
                sprite.state = 'idle'

        sprite.direction.y = 0
    
    @staticmethod
    def ramp_collision(sprite: pg.sprite.Sprite, tile: pg.Rect, ramp_direction: str) -> None:
        if ramp_direction == 'left':
            rel_x = max(0, min(sprite.rect.centerx - tile.left, TILE_SIZE)) # sprite coords relative to the ramp
            ramp_y = tile.top + (TILE_SIZE - rel_x)
        
        elif ramp_direction == 'right':
            rel_x = max(0, min(sprite.rect.centerx - tile.right, TILE_SIZE))
            ramp_y = tile.top + rel_x
    
        if sprite.direction.y > 0:
            if sprite.rect.bottom > ramp_y:
                sprite.rect.bottom = ramp_y
                sprite.grounded = True
                sprite.direction.y = 0
                sprite.state = 'idle'

        elif sprite.direction.y < 0:
            sprite.rect.top = tile.bottom
            sprite.direction.y = 0
        
        sprite.direction.x = 0 # otherwise the player paused midway through ascending the ramp
    
    def check_spr_underwater(self, spr: pg.sprite.Sprite) -> None:
        spr_w, spr_h = spr.rect.width // TILE_SIZE, spr.rect.height // TILE_SIZE
        spr_midtop = spr.rect.midtop
        spr_tile_x, spr_tile_y = spr_midtop[0] // TILE_SIZE, spr_midtop[1] // TILE_SIZE
        water_id = self.names_to_ids['water'] 
        spr.underwater = all(
            self.tile_map[spr_tile_x + x, spr_tile_y + y] == water_id
            for x in range(int(spr_w)) for y in range(int(spr_h) - 1)
        )
        if spr.underwater:
            if spr.gravity == spr.default_gravity:
                spr.gravity //= 10
            if spr.jump_height == spr.default_jump_height:
                spr.jump_height = int(spr.jump_height / 1.25)
        else:
            spr.gravity = spr.default_gravity
            spr.jump_height = spr.default_jump_height
            spr.oxygen_lvl = spr.max_oxygen_lvl


class CollisionMap:
    def __init__(self, physics_engine: PhysicsEngine):
        self.tile_map: np.ndarray = physics_engine.tile_map
        self.names_to_ids: dict[str, int] = physics_engine.names_to_ids

        self.cell_size = 10
        self.map = defaultdict(list)
        self.generate_map()

    def generate_map(self) -> None:
        '''precompute rects with the coordinates of solid tiles'''
        for x in range(MAP_SIZE[0]):
            for y in range(MAP_SIZE[1]):
                if self.tile_map[x, y] != self.names_to_ids['air']: 
                    cell_coords = (x // self.cell_size, y // self.cell_size)
                    self.map[cell_coords].append(pg.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    def search_map(self, sprite: pg.sprite.Sprite) -> list[pg.Rect]:
        '''extract the rects within the current cell for collision detection'''
        rects = []
        # determine which collision map cell(s) the player is within
        min_tile_x = sprite.rect.left // TILE_SIZE
        max_tile_x = sprite.rect.right // TILE_SIZE

        min_tile_y = sprite.rect.top // TILE_SIZE
        max_tile_y = sprite.rect.bottom // TILE_SIZE

        min_cell_x = min_tile_x // self.cell_size
        max_cell_x = max_tile_x // self.cell_size

        min_cell_y = min_tile_y // self.cell_size
        max_cell_y = max_tile_y // self.cell_size
        
        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1): 
                if (cell_x, cell_y) in self.map:
                    rects.extend(self.map[(cell_x, cell_y)])

        return rects

    # update tiles that have been mined/placed, will also have to account for the use of explosives and perhaps weather altering the terrain
    def update_map(self, tile_coords: tuple[int, int], add_tile: bool = False, remove_tile: bool = False) -> None:
        cell_coords = (tile_coords[0] // self.cell_size, tile_coords[1] // self.cell_size)
        rect = pg.Rect(tile_coords[0] * TILE_SIZE, tile_coords[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)    
        if cell_coords in self.map: # false if you're up in the stratosphere
            if add_tile and rect not in self.map[cell_coords]:
                self.map[cell_coords].append(rect)
            
            elif remove_tile and rect in self.map[cell_coords]:
                # sprites could occasionally pass through tiles whose graphic was still being rendered
                # removing the associated rectangle only after the tile ID update is confirmed appears to fix the issue
                if self.tile_map[tile_coords] == self.names_to_ids['air']:
                    self.map[cell_coords].remove(rect)