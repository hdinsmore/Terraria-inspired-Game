from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import procgen as ProcGen
    from input_manager import Keyboard
    
import pygame as pg
from math import ceil
from collections import defaultdict

from settings import MAP_SIZE, TILE_SIZE, CELL_SIZE, WORLD_EDGE_RIGHT, WORLD_EDGE_BOTTOM

class PhysicsEngine:
    def __init__(self, game_obj: Main):
        proc_gen: ProcGen = game_obj.proc_gen
        self.tile_map: np.ndarray = proc_gen.tile_map
        self.names_to_ids: dict[str, int] = proc_gen.names_to_ids
        self.ids_to_names: dict[int, str] = proc_gen.ids_to_names

        self.cam_offset: pg.Vector2 = game_obj.cam.offset

        self.keyboard: Keyboard = game_obj.input_manager.keyboard
        self.key_bindings: dict[str, int] = self.keyboard.key_bindings
        self.held_keys: Sequence[bool] = self.keyboard.held_keys
        self.pressed_keys: Sequence[bool] = self.keyboard.pressed_keys

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


class CollisionMap:
    def __init__(self, physics_engine: PhysicsEngine):
        self.tile_map: np.ndarray = physics_engine.tile_map
        self.names_to_ids: dict[str, int] = physics_engine.names_to_ids

        self.map = defaultdict(list)
        self.generate_map()

    def generate_map(self) -> None:
        '''precompute rects with the coordinates of solid tiles'''
        for x in range(MAP_SIZE[0]):
            for y in range(MAP_SIZE[1]):
                if self.tile_map[x, y] != self.names_to_ids['air']: 
                    cell_coords = (x // CELL_SIZE, y // CELL_SIZE)
                    self.map[cell_coords].append(pg.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    def search_map(self, sprite: pg.sprite.Sprite) -> list[pg.Rect]:
        '''extract the rects within the current cell for collision detection'''
        rects = []
        # determine which collision map cell(s) the player is within
        min_tile_x = sprite.rect.left // TILE_SIZE
        max_tile_x = sprite.rect.right // TILE_SIZE

        min_tile_y = sprite.rect.top // TILE_SIZE
        max_tile_y = sprite.rect.bottom // TILE_SIZE

        min_cell_x = min_tile_x // CELL_SIZE
        max_cell_x = max_tile_x // CELL_SIZE

        min_cell_y = min_tile_y // CELL_SIZE
        max_cell_y = max_tile_y // CELL_SIZE
        
        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1): 
                if (cell_x, cell_y) in self.map:
                    rects.extend(self.map[(cell_x, cell_y)])

        return rects

    # update tiles that have been mined/placed, will also have to account for the use of explosives and perhaps weather altering the terrain
    def update_map(self, tile_coords: tuple[int, int], add_tile: bool = False, remove_tile: bool = False) -> None:
        cell_coords = (tile_coords[0] // CELL_SIZE, tile_coords[1] // CELL_SIZE)
        rect = pg.Rect(tile_coords[0] * TILE_SIZE, tile_coords[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)    
        if cell_coords in self.map: # false if you're up in the stratosphere
            if add_tile and rect not in self.map[cell_coords]:
                self.map[cell_coords].append(rect)
            
            elif remove_tile and rect in self.map[cell_coords]:
                # sprites could occasionally pass through tiles whose graphic was still being rendered
                # removing the associated rectangle only after the tile ID update is confirmed appears to fix the issue
                if self.tile_map[tile_coords] == self.names_to_ids['air']:
                    self.map[cell_coords].remove(rect)
        

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


class SpriteMovement:
    def __init__(self, physics_engine: PhysicsEngine):
        self.tile_map: np.ndarray = physics_engine.tile_map
        self.names_to_ids: dict[str, int] = physics_engine.names_to_ids
        self.tile_collision_update: callable = physics_engine.collision_detection.tile_collision_update
        key_bindings: dict[str, int] = physics_engine.key_bindings
        self.key_move_left: int = key_bindings['move left']
        self.key_move_right: int = key_bindings['move right']
        self.key_jump: int = key_bindings['jump']

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

    @staticmethod
    def update_movement_x(sprite: pg.sprite.Sprite, direction_x: int, dt: float) -> None:
        sprite.direction.x = direction_x
        sprite.rect.x += sprite.direction.x * sprite.move_speed * dt
        sprite.rect.x = max(0, min(sprite.rect.x, WORLD_EDGE_RIGHT))
        if hasattr(sprite, 'state') and sprite.state == 'idle': # avoid overwriting an active state
            sprite.state = 'walking'
    
    @staticmethod
    def update_movement_y(sprite, dt: float) -> None:
        # getting the average of the downward velocity
        sprite.direction.y += (sprite.gravity // 2) * dt
        sprite.rect.y += sprite.direction.y * dt
        sprite.direction.y += (sprite.gravity // 2) * dt

        sprite.rect.y = min(sprite.rect.y, WORLD_EDGE_BOTTOM) # don't add a top limit until the space biome borders are set, if any

    def jump(self, sprite: pg.sprite.Sprite, pressed_keys: Sequence[bool]) -> None:
        if pressed_keys[self.key_jump] and sprite.grounded and sprite.state != 'jumping':
            sprite.direction.y -= sprite.jump_height
            sprite.grounded = False
            sprite.state = 'jumping'
            sprite.frame_index = 0

    def update(self, player: pg.sprite.Sprite, held_keys: Sequence[bool], pressed_keys: Sequence[bool], dt: float):
        self.move_sprite(player, held_keys[self.key_move_right] - held_keys[self.key_move_left], dt)
        self.jump(player, pressed_keys)


class WaterFlow:
    def __init__(self, physics_engine: PhysicsEngine):
        self.tile_map: np.ndarray = physics_engine.tile_map
        self.names_to_ids: dict[str, int] = physics_engine.names_to_ids
        self.ids_to_names: dict[int, str] = physics_engine.ids_to_names
        
