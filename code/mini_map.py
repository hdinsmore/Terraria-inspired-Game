from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    from ui import UI

import pygame as pg
import numpy as np

from settings import MAP_SIZE, TILE_SIZE, TILES

class MiniMap:
    def __init__(self, game_obj: Main, ui: UI): # keep ui as a parameter, Main doesn't have UI as a class attribute yet since UI instantiates MiniMap
        self.screen = game_obj.screen
        self.cam_offset = game_obj.cam.offset
        
        proc_gen = game_obj.proc_gen
        self.tile_map = proc_gen.tile_map
        self.names_to_ids = proc_gen.names_to_ids
        self.ids_to_names = proc_gen.ids_to_names
        
        self.get_tile_material = game_obj.sprite_manager.mining.get_tile_material

        self.gen_outline = ui.gen_outline
        self.save_data = ui.save_data

        self.visited_tiles = np.array(self.save_data['visited tiles']) if self.save_data else np.full(MAP_SIZE, False, dtype = bool)
        self.update_radius = 6
        self.tiles_x, self.tiles_y = 80, 80
        self.tile_px_w, self.tile_px_h = 2, 2
        self.outline_w = self.tiles_x * self.tile_px_w
        self.outline_h = self.tiles_y * self.tile_px_h
        self.border_dist_x = self.tiles_x // 2
        self.border_dist_y = self.tiles_y // 2
        self.padding = 5
        self.topleft = pg.Vector2(self.padding, self.padding)
        self.render = True
        self.terrain_tiles = TILES.keys()
        self.non_tiles = {
            'air': {'rgb': (178, 211, 236)}, 
            'tree base': {'rgb': (74, 54, 47)},
            'water': {'rgb': (41, 80, 140)}
        }
        self.tree_px_height = 8
        self.branch_y = self.tree_px_height // 2

    def render_outline(self) -> None:
        if self.render:
            base_rect = pg.Rect(*self.topleft, self.outline_w, self.outline_h)
            outline1 = self.gen_outline(base_rect, draw = False, return_outline = True)
            outline2 = self.gen_outline(outline1, draw = True)
            pg.draw.rect(self.screen, 'black', outline1, 1)

    def render_tiles(self) -> None:
        tile_map, visited_map = self.get_map_slices()
        cols, rows = tile_map.shape
        for y in range(rows): # keep y first otherwise tree branches to the right get blitted over by the following x index
            for x in range(cols):
                image = pg.Surface((self.tile_px_w, self.tile_px_h))
                if visited_map[x, y]:
                    tile_id = tile_map[x, y]
                    tile_name = self.ids_to_names[tile_id]
                    if tile_name in self.non_tiles:
                        tile_color = self.non_tiles[tile_name]['rgb']
                        if tile_name == 'tree base':
                            self.render_tree(image, tile_color, x, y)
                    else:
                        if tile_name != 'obj extended':
                            if tile_name in self.terrain_tiles:
                                tile_color = TILES[tile_name]['rgb']
                            else:
                                pass
                        else:
                            pass
                else:
                    tile_color = 'black'
                image.fill(tile_color)
                rect = image.get_rect(topleft = self.topleft + (x * self.tile_px_w, y * self.tile_px_h))
                self.screen.blit(image, rect)

    def render_tree(self, image: pg.Surface, tile_color: str, x: int, y: int) -> None:
        image.fill(tile_color)
        for i in range(self.tree_px_height):
            rect = image.get_rect(topleft = self.topleft + (x * self.tile_px_w, (y - i) * self.tile_px_h))
            self.screen.blit(image, rect)
            if i == self.branch_y:
                left_branch = image.get_rect(topleft = self.topleft + ((x - 1) * self.tile_px_w, (y - i) * self.tile_px_h))
                right_branch = image.get_rect(topleft = self.topleft + ((x + 1) * self.tile_px_w, (y - i) * self.tile_px_h))
                self.screen.blit(image, left_branch)
                self.screen.blit(image, right_branch)

    def get_map_slices(self) -> tuple[np.ndarray, np.ndarray]:
        '''returns the slice of the tile map to display & the updated visited tiles map'''
        screen_w = self.screen.get_width() // 2
        screen_h = self.screen.get_height() // 2
        tile_offset_x = int((self.cam_offset.x + screen_w) / TILE_SIZE) # not using int division since the camera offset is a vector2
        tile_offset_y = int((self.cam_offset.y + screen_h) / TILE_SIZE)

        left = max(0, tile_offset_x - self.border_dist_x)
        right = min(self.tile_map.shape[0], tile_offset_x + self.border_dist_x)
        top_default = tile_offset_y - self.border_dist_y # keeping the default in case it's negative so the top/bottom row calculation can be adjusted
        top = max(0, top_default)
        bottom = min(self.tile_map.shape[1], tile_offset_y + self.border_dist_y)
        if top_default < 0:
            bottom += abs(top_default) # prevents rows below from being occluded when the camera offset is negative 
        
        left_visited = max(0, tile_offset_x - self.update_radius)
        right_visited = min(self.tile_map.shape[0], tile_offset_x + self.update_radius)
        top_default = tile_offset_y - self.update_radius
        top_visited = max(0, tile_offset_y - self.update_radius)
        bottom_visited = min(self.tile_map.shape[1], tile_offset_y + self.update_radius)
        if top_default < 0:
            bottom_visited += abs(top_default)
        self.visited_tiles[left_visited:right_visited, top_visited:bottom_visited] = True
        
        start_x = max(0, self.border_dist_x - (tile_offset_x - left))
        start_y = max(0, self.border_dist_y - (tile_offset_y - top))
        
        map_slice = self.tile_map[left:right, top:bottom]
        map_cols, map_rows = map_slice.shape
        cols = min(map_cols, self.tiles_x - start_x) 
        rows = min(map_rows, self.tiles_y - start_y)

        full_slice = np.full((self.tiles_x, self.tiles_y), self.names_to_ids['air'], dtype = np.uint8)
        full_slice[start_x:start_x + map_cols, start_y:start_y + map_rows] = map_slice[start_x:start_x + map_cols, start_y:start_y + map_rows]
        
        visited_slice = np.full((self.tiles_x, self.tiles_y), False, dtype = bool)
        visited_slice[start_x:start_x + cols, start_y:start_y + rows] = self.visited_tiles[left:left + cols, top:top + rows]
        
        return full_slice, visited_slice

    def update(self) -> None:
        self.render_outline()
        self.render_tiles()