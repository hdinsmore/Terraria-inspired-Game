from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from input_manager import InputManager
    from sprite_manager import SpriteManager
    from player import Player
    from procgen import ProcGen
    from ui import UI

import pygame as pg
import numpy as np
from collections import defaultdict
from math import ceil

from settings import MAP_SIZE, TILE_SIZE, TILES, RAMP_TILES, TILE_REACH_RADIUS, Z_LAYERS, OBJ_ITEMS, PRODUCTION, PIPE_TRANSPORT_DIRS, LIQUIDS

class ItemPlacement:
    def __init__(self, game_obj: Main):
        self.screen: pg.Surface = game_obj.screen
        self.cam_offset: pg.Vector2 = game_obj.cam.offset

        proc_gen: ProcGen = game_obj.proc_gen
        self.tile_map: np.ndarray = proc_gen.tile_map
        self.height_map: np.ndarray = proc_gen.height_map
        self.names_to_ids: dict[str, int] = proc_gen.names_to_ids

        self.collision_map: dict[tuple[int, int], pg.Rect] = game_obj.physics_engine.collision_map

        self.sprite_manager: SpriteManager = game_obj.sprite_manager
        self.rect_in_sprite_radius: callable = self.sprite_manager.rect_in_sprite_radius
        self.items_init_when_placed: dict[str, pg.sprite.Sprite] = self.sprite_manager.items_init_when_placed

        input_manager: InputManager = game_obj.input_manager
        self.keyboard: Keyboard = input_manager.keyboard
        self.mouse: Mouse = input_manager.mouse

        self.player: Player = game_obj.player

        self.graphics: dict[str, pg.Surface] = game_obj.asset_manager.assets['graphics']
        ui: UI = game_obj.ui
        self.gen_outline: callable = ui.gen_outline 
        self.gen_bg: callable = ui.gen_bg,
        self.render_item_amount: callable = ui.render_item_amount
       
        self.obj_map = np.full(MAP_SIZE, None, dtype=object) # stores every tile an object overlaps with (tile_map only stores the topleft since it controls rendering)
        self.machine_ids = {self.names_to_ids[k] for k in PRODUCTION} | {self.names_to_ids['item extended']}
        self.pipe_ids = {self.names_to_ids[f'pipe {i}'] for i in range(len(PIPE_TRANSPORT_DIRS))}
        self.tile_ids = {self.names_to_ids[name] for name in TILES}
        self.ramp_ids = {self.names_to_ids[name] for name in RAMP_TILES}
        self.liquid_ids = {self.names_to_ids[name] for name in LIQUIDS}
        self.tiles_can_place_over = {self.names_to_ids['air'], self.names_to_ids['water']}

    def place_item(self, sprite: pg.sprite.Sprite, xy: tuple[int, int], old_pipe_idx: int=None) -> None:
        surf = self.graphics[sprite.item_holding]
        if surf.size[0] <= TILE_SIZE and surf.size[1] <= TILE_SIZE:
            if self.valid_placement(xy, sprite):
                self.place_single_tile_item(xy, sprite, old_pipe_idx)
        else:
            tiles_covered = self.get_tiles_covered(xy, surf)
            if self.valid_placement(tiles_covered, sprite):
                self.place_multi_tile_item(tiles_covered, surf, sprite)

    def valid_placement(self, tiles_covered: tuple[int, int] | list[tuple[int, int]], sprite: pg.sprite.Sprite) -> bool:
        if isinstance(tiles_covered, tuple):
            return self.tile_map[*tiles_covered] in self.tiles_can_place_over and \
            self.can_reach_tile(*tiles_covered, sprite.rect.center) and \
            self.valid_item_border(sprite.item_holding, tiles_covered)
        
        return self.valid_item_border(sprite.item_holding, self.get_ground_tiles(tiles_covered)) and \
        self.can_reach_tile(*tiles_covered[0], sprite.rect.center) and \
        all(self.tile_map[xy] in self.tiles_can_place_over for xy in tiles_covered)
        
    def can_reach_tile(self, x: int, y: int, sprite_xy_world: tuple[int, int]) -> bool:
        sprite_tile_xy = pg.Vector2(sprite_xy_world) // TILE_SIZE
        return abs(x - sprite_tile_xy.x) <= TILE_REACH_RADIUS and abs(y - sprite_tile_xy.y) <= TILE_REACH_RADIUS 
    
    @staticmethod
    def get_ground_tiles(tiles_covered: list[tuple[int, int]]) -> list[tuple[int, int]]:
        max_y = max(y for _, y in tiles_covered)
        return [(x, y + 1) for x, y in tiles_covered if y == max_y]

    def valid_item_border(self, item: str, tiles_covered: tuple[int, int] | list[tuple[int, int]]) -> bool:
        if isinstance(tiles_covered, tuple):
            x, y = tiles_covered
            if 'pipe' in item:
                return self.valid_pipe_border(x, y, int(item[-1]))
            else:
                return any(self.tile_map[xy] in self.tile_ids | self.ramp_ids for xy in [
                    (x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)
                ]) # TODO: update the ramp tile checks to prevent placing tiles that only attach to the slanted side
        
        on_ground = all(self.tile_map[x, y] in self.tile_ids for x, y in self.get_ground_tiles(tiles_covered))
        if 'pump' in item:
            liquid_source_x = tiles_covered[-1][0] + 1 if self.player.item_flip_dir == 'left' else tiles_covered[0][0] - 1
            return on_ground and self.tile_map[liquid_source_x, round(self.height_map[liquid_source_x]) + 1] in self.liquid_ids
        else:
            return on_ground
        
    def valid_pipe_border(self, x: int, y: int, pipe_idx: int) -> bool:
        pipe_data = PIPE_TRANSPORT_DIRS[pipe_idx]
        for dx, dy in pipe_data if pipe_idx <= 5 else (pipe_data['horizontal'] + pipe_data['vertical']):
            if 0 <= x + dx < MAP_SIZE[0] and 0 <= y + dy < MAP_SIZE[1] and self.tile_map[x + dx, y + dy] in (self.machine_ids | self.pipe_ids):
                return True
        return False

    def place_single_tile_item(self, tile_xy: tuple[int, int], sprite: pg.sprite.Sprite, old_pipe_idx: int=None) -> None: # passing the item name if a class needs to be initialized
        self.tile_map[tile_xy] = self.names_to_ids[sprite.item_holding]
        self.collision_map.update_map(tile_xy, add_tile=True)
        sprite.inventory.remove_item()
        if sprite.item_holding in OBJ_ITEMS:
            self.init_obj(sprite.item_holding, [tile_xy])  

    def place_multi_tile_item(self, tiles_covered: list[tuple[int, int]], surf: pg.Surface, sprite: pg.sprite.Sprite) -> None:
        obj = sprite.item_holding in OBJ_ITEMS
        for i, xy in enumerate(tiles_covered):
            if i == 0:
                self.tile_map[xy] = self.names_to_ids[sprite.item_holding] # only store the topleft as the item ID to avoid rendering multiple surfaces
                if obj:
                    self.init_obj(sprite.item_holding, tiles_covered)
            else:
                self.tile_map[xy] = self.names_to_ids['item extended'] 

            self.collision_map.update_map(xy, add_tile=True)
            
        sprite.inventory.remove_item(sprite.item_holding)

    @staticmethod
    def get_tiles_covered(xy: tuple[int, int], image: pg.Surface) -> list[tuple[int, int]]:
        tiles = [] 
        x, y = xy
        for tx in range(ceil(image.get_width() / TILE_SIZE)):
            for ty in range(ceil(image.get_height() / TILE_SIZE)):
                tiles.append((x + tx, y + ty))
        return tiles

    def render_ui(self, icon_image: pg.Surface, icon_rect: pg.Rect, xy: tuple[int, int], player: Player) -> None:
        tint_image = pg.Surface(icon_image.get_size())
        tint_image.fill('green' if self.valid_placement(self.get_tiles_covered(xy, icon_image), player) else 'red')
        tint_image.set_alpha(25)
        self.screen.blit(tint_image, tint_image.get_rect(topleft=icon_rect.topleft))

    def init_obj(self, name: str, tiles_covered: list[tuple[int, int]]) -> None:
        obj = self.items_init_when_placed[name if 'pipe' not in name else name.split(' ')[0]]
        obj_instance = obj(**self.sprite_manager.get_cls_init_params(name, tiles_covered)) # don't add the pipe index here, they all use the same Pipe class
        for xy in tiles_covered:
            self.obj_map[xy] = obj_instance