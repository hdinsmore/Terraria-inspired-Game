from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main

import pygame as pg
from abc import ABC

from settings import TILE_SIZE, GRAVITY, Z_LAYERS

class Sprite(pg.sprite.Sprite, ABC):
    def __init__(
        self, 
        xy: tuple[int, int], 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        z: int=Z_LAYERS['main']
    ):
        super().__init__(*sprite_groups)
        self.xy = xy
        self.image = image
        self.rect = self.image.get_rect(topleft=self.xy)
        self.z = z # layer to render on


class AnimatedSprite(pg.sprite.Sprite, ABC):
    def __init__(
        self, 
        game_obj: Main,
        xy: tuple[int, int],
        frames: dict[str, pg.Surface],
        sprite_groups: list[pg.sprite.Group],
        move_speed: int,
        animation_speed: int | dict[str, int],
        z: int=Z_LAYERS['main'],
        gravity: int=GRAVITY
    ):
        super().__init__(*sprite_groups)
        self.screen = game_obj.screen
        self.cam_offset = game_obj.cam.offset
        self.xy = xy
        self.frames = frames
        self.move_speed = move_speed
        self.animation_speed = animation_speed
        self.z = z
        self.gravity = gravity

        self.state = 'idle'
        self.frame_idx = 0
        self.image = self.frames[self.state][self.frame_idx]
        self.rect = self.image.get_rect(midbottom=self.xy)
        self.direction = pg.Vector2()
        self.tile_xy = (self.xy[0] // TILE_SIZE, self.xy[1] // TILE_SIZE)