from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main

import pygame as pg

from settings import Z_LAYERS, RES
from colonist import Colonist
from inventory import PlayerInventory

class Player(Colonist):
    def __init__(
        self, 
        game_obj: Main,
        xy: pg.Vector2,
        frames: dict[str, pg.Surface],
        sprite_groups: list[pg.sprite.Sprite],
        save_data: dict[str, any],
    ):
        super().__init__(game_obj, xy, frames, sprite_groups, save_data=save_data)
        self.inventory = PlayerInventory(self, None if not save_data else save_data['inventory data'])
        self.item_flip_dir = None 
        
        self.z = Z_LAYERS['player']
        self.heart_surf = self.graphics['icons']['heart']
        self.heart_width = self.heart_surf.get_width()
    
    def render_hearts(self) -> None:
        for i in range(self.hp):
            self.screen.blit(self.heart_surf, (RES[0] - (5 + self.heart_width + (25 * i)), 5))

    def respawn(self) -> None:
        self.hp = self.max_hp
        self.oxygen_lvl = self.max_oxygen_lvl
        self.underwater = False
        self.alarms['lose oxygen'].running = False

        self.rect.center = self.spawn_point
        self.frame_idx = 0
        self.direction = pg.Vector2()
        self.grounded = True
        self.gravity = self.default_gravity

        self.inventory.contents.clear()
        self.item_holding = None
    
    def update(self, dt: float) -> None:
        super().update(dt)
        self.inventory.get_idx_selection(self.keyboard)
        self.render_hearts()