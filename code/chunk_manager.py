from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pygame as pg

from settings import CHUNK_SIZE, TILE_SIZE, MAP_SIZE, RES
import math

class ChunkManager:
    def __init__(self, camera_offset: pg.Vector2) -> None:
        self.camera_offset = camera_offset

    @staticmethod
    def get_chunk(topleft_x: int, topleft_y: int) -> list[tuple[int, int]]:
        '''divide the map into chunks of tiles to render as needed'''
        chunk_coords = []
        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                # coordinates for individual tiles within a chunk
                tile_x = x + topleft_x 
                tile_y = y + topleft_y 
                chunk_coords.append((tile_x, tile_y))
        
        return chunk_coords

    def update(self) -> list[list[tuple[int, int]]]:
        '''add/remove chunks as the camera offset shifts'''
        visible_chunks = []
        
        # calculate how many chunks are needed to fill the screen
        num_chunks_x = math.ceil(RES[0] / (CHUNK_SIZE * TILE_SIZE))
        num_chunks_y = math.ceil(RES[1] / (CHUNK_SIZE * TILE_SIZE))

        for x in range(num_chunks_x):
            for y in range(num_chunks_y):
                chunk_x = (x * CHUNK_SIZE) + (self.camera_offset.x // TILE_SIZE)
                chunk_y = (y * CHUNK_SIZE) + (self.camera_offset.y // TILE_SIZE)

                max_x = MAP_SIZE[0] - CHUNK_SIZE
                max_y = MAP_SIZE[1] - CHUNK_SIZE

                target_x = max(0, min(chunk_x, max_x))
                target_y = max(0, min(chunk_y, max_y))

                chunk = self.get_chunk(topleft_x = int(target_x), topleft_y = int(target_y))
                visible_chunks.append(chunk)

        return visible_chunks