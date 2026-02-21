from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sprite_manager import SpriteManager

import pygame as pg
from random import randint, choice

from sprite_base_classes import Sprite
from settings import Z_LAYERS, GRAVITY

class ItemDrop(Sprite):
    def __init__(
        self, 
        xy: pg.Vector2,
        image: pg.Surface, 
        z: int,
        sprite_groups: list[pg.sprite.Group], 
        sprite_manager: SpriteManager,
        direction: pg.Vector2,
        name: str,
        sprite: pg.sprite.Sprite=None
    ):
        super().__init__(xy, image, z, sprite_groups)
        self.sprite_movement = sprite_manager.sprite_movement
        self.pick_up_item = sprite_manager.pick_up_item
        self.direction = direction
        self.name = name
        self.amount = sprite.inventory.contents[name]['amount'] if sprite else 1

        self.move_speed = 1
        self.gravity = GRAVITY // 3

    def update(self, dt: float) -> None:
        self.sprite_movement.move_sprite(self, self.direction.x, dt)
        if self.direction.x and int(self.direction.y) == 0:
            self.direction.x = 0
        
        self.pick_up_item(obj=self, name=self.name, amount=self.amount)

    def get_save_data(self) -> dict[str, list]:
        return {'xy': list(self.rect.topleft)}