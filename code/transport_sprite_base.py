from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    
import pygame as pg
from abc import ABC

from machine_sprite_base import Machine

class TransportSprite(Machine, ABC):
    def __init__(
        self, 
        xy: tuple[int, int], 
        image: pg.Surface, 
        z: int, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        save_data: dict[str, any]=None
    ):
        super().__init__(save_data=save_data, xy=xy, image=image, sprite_groups=sprite_groups, game_obj=game_obj)
        self.dir_ui = self.graphics['transport dirs']
        self.item_holding = None
        self.xy_to_dir = {
            0: {(1, 0): 'E', (-1, 0): 'W'},
            1: {(0, -1): 'N', (0, 1): 'S'},
            2: {(1, 0): 'SE', (0, -1): 'WN'},
            3: {(0, -1): 'EN', (-1, 0): 'SW'},
            4: {(1, 0): 'NE', (0, 1): 'WS'},
            5: {(-1, 0): 'NW', (0, 1): 'ES'},
            6: {(1, 0): 'E', (-1, 0): 'W', (0, -1): 'N', (0, 1): 'S'},
            7: {(1, 0): 'E', (0, -1): 'N', (0, 1): 'S'},
            8: {(0, -1): 'N', (0, 1): 'S', (-1, 0): 'W'},
            9: {(1, 0): 'E', (-1, 0): 'W', (0, -1): 'N'},
            10: {(1, 0): 'E', (-1, 0): 'W', (0, 1): 'S'}
        }
        self.obj_connections = {}
        if hasattr(self, 'rotated_over'): # is an inserter
             self.image = self.image.copy() # for the rotations

    def update_alarms(self) -> None:
        for alarm in self.alarms.values():
            alarm.update()