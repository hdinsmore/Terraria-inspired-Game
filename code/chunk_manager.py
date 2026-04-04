from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    import numpy as np
    from asset_manager import AssetManager

from settings import TILE_SIZE, RES, LIQUIDS, MAX_PX_X, MAX_PX_Y, MAP_SIZE
from math import ceil

import pygame as pg

class ChunkManager:
    '''divides the map into chunks of tiles to only render when they come into view'''
    def __init__(self, game_obj: Main) -> None:
        self.screen: pg.Surface = game_obj.screen
        self.cam_offset: pg.Vector2 = game_obj.cam.offset
        self.asset_manager: AssetManager = game_obj.asset_manager

        self.tile_map: np.ndarray = game_obj.proc_gen.tile_map
        self.names_to_ids: dict[str, int] = game_obj.proc_gen.names_to_ids
        self.ids_to_names: dict[int, str] = game_obj.proc_gen.ids_to_names
        self.tile_types_ignore = {self.names_to_ids[tile] for tile in ('air', *LIQUIDS, 'tree base', 'item extended')} # adding liquids because they're rendered at a layer in front of sprites
        self.mining_map: dict[tuple[int, int], dict[str, int]] = game_obj.sprite_manager.mining.mining_map

        self.num_chunk_tiles = 24
        self.chunk_px_size = self.num_chunk_tiles * TILE_SIZE
        self.num_screen_chunks_x = ceil(RES[0] / self.chunk_px_size) + 1
        self.num_screen_chunks_y = ceil(RES[1] / self.chunk_px_size) + 1
        self.visible_chunks: list[list[tuple[int, int]]] = []
        self.chunk_img_cache: dict[tuple[int, int], pg.Surface] = {} # making a collage of tile images within a chunk
        self.get_mined_tile_img: callable = None # initialized in TerrainGraphics
        
    # TODO: cache this for visited chunks
    def get_chunk(self, topleft_x: int, topleft_y: int) -> list[tuple[int, int]]:
        return [
            (x + topleft_x, y + topleft_y) 
            for x in range(self.num_chunk_tiles) 
            for y in range(self.num_chunk_tiles)
        ]
        
    def update_chunks(self) -> None:
        '''adds/removes chunks as the camera offset shifts'''
        self.visible_chunks.clear()
        for x in range(self.num_screen_chunks_x):
            for y in range(self.num_screen_chunks_y):
                chunk_x = (x * self.num_chunk_tiles) + (self.cam_offset.x // TILE_SIZE)
                chunk_y = (y * self.num_chunk_tiles) + (self.cam_offset.y // TILE_SIZE)
                target_x = max(0, min(chunk_x, MAX_PX_X - 1))
                target_y = max(0, min(chunk_y, MAX_PX_Y - 1))
                self.visible_chunks.append(self.get_chunk(int(target_x), int(target_y)))

    def render_chunks(self) -> None:
        self.update_chunks()
        print(self.visible_chunks[-1][0][0] - self.visible_chunks[0][0][0])
        for chunk in self.visible_chunks:
            topleft_tile = chunk[0]
            if topleft_tile in self.chunk_img_cache:
                img = self.chunk_img_cache[topleft_tile]
            else:
                img = self.get_chunk_img(chunk, topleft_tile)
            self.screen.blit(img, (topleft_tile[0] * TILE_SIZE, topleft_tile[1] * TILE_SIZE) - self.cam_offset)

    def get_chunk_img(self, chunk: list[tuple[int, int]], topleft_tile: tuple[int, int]) -> pg.Surface:
        '''combines a chunk's individual tile images into one surface'''
        img_w = min(self.chunk_px_size, MAX_PX_X - topleft_tile[0])
        img_h = min(self.chunk_px_size, MAX_PX_Y - topleft_tile[1])
        blit_surf = pg.Surface((img_w, img_h), pg.SRCALPHA) # canvas representing the entire chunk space where individual tile images will be blitted
        for x in range(img_w // TILE_SIZE):
            for y in range(img_h // TILE_SIZE):
                tile_coord = (min(topleft_tile[0] + x, MAP_SIZE[0] - 1), min(topleft_tile[1] + y, MAP_SIZE[1] - 1))
                if self.tile_map[tile_coord] not in self.tile_types_ignore:
                    tile_img = self.asset_manager.get_image(self.ids_to_names[self.tile_map[tile_coord]])
                    if tile_coord in self.mining_map:
                        tile_img = self.get_mined_tile_img(tile_coord, tile_img)
                    blit_surf.blit(tile_img, (x * TILE_SIZE, y * TILE_SIZE))
        self.chunk_img_cache[topleft_tile] = blit_surf
        return blit_surf