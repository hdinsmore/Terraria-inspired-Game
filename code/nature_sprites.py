from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from physics_engine import PhysicsEngine
    from player import Player

import pygame as pg
from random import randint, choice
from math import sin, ceil

from settings import RES, TOOLS, Z_LAYERS, GRAVITY
from sprite_base_classes import Sprite
from item_drop import ItemDrop
from alarm import Alarm
from ui import UI

class Cloud(Sprite):
    def __init__(
        self, 
        xy: pg.Vector2, 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        z: int, 
        speed: int, 
        player: Player, 
        rect_in_sprite_radius: callable
    ):
        super().__init__(xy, image, z, sprite_groups)
        self.speed = speed
        self.player = player
        self.rect_in_sprite_radius = rect_in_sprite_radius

    def move(self, dt: float) -> None:  
        self.rect.x -= self.speed * dt
        if self.rect.right <= 0:
            self.kill()
        
    def update(self, dt: float) -> None:
        self.move(dt)


class Tree(Sprite):
    def __init__(
        self, 
        xy: pg.Vector2, 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        z: int, 
        tree_map_xy: tuple[int, int] | list[int, int],  
        sprite_manager: SpriteManager,
        save_data: dict[str, any]
    ):
        super().__init__(xy, image, sprite_groups, z)
        self.image = self.image.copy()
        self.rect = self.image.get_rect(midbottom=self.xy) # SpriteBase uses the topleft

        self.tree_map_xy = tree_map_xy if type(tree_map_xy) == tuple else tuple(tree_map_xy)

        self.sprite_manager = sprite_manager
        self.wood_image = sprite_manager.graphics['wood']
        self.tree_obj_map = sprite_manager.tree_map
        self.wood_sprite_groups = [
            getattr(sprite_manager, group) for group in (
                'all_sprites', 'active_sprites', 'nature_sprites', 'item_sprites'
            )
        ]
        self.sprite_movement = sprite_manager.sprite_movement

        self.save_data = save_data

        self.max_strength = 50
        self.current_strength = save_data['current strength'] if save_data else self.max_strength

        self.alpha = 255

        self.total_wood = ceil(self.image.height / 25)

        self.delay_alarm = Alarm(length=500) # prevents cut_down() from being called every frame

    def cut_down(self, sprite: pg.sprite.Sprite, get_tool_strength: callable, pick_up_item: callable) -> None:
        self.delay_alarm.update()
        if not self.delay_alarm.running:
            sprite.state = 'chopping'
            axe_material = sprite.item_holding.split()[0]
            tool_strength = get_tool_strength(sprite)
            self.current_strength = max(0, self.current_strength - tool_strength)
            rel_strength = self.max_strength // tool_strength
            rel_alpha = self.alpha * (1 / rel_strength)
            self.alpha = max(0, self.alpha - rel_alpha)
            self.image.set_alpha(self.alpha)
            if self.current_strength == 0 and self.tree_map_xy in self.tree_obj_map:
                self.tree_obj_map.remove(self.tree_map_xy)  
                self.kill()
                sprite.state = 'idle'
                self.produce_wood(sprite, pick_up_item)
                return
            self.delay_alarm.start()
    
    def produce_wood(self, sprite: pg.sprite.Sprite, pick_up_item: callable) -> None:
        for i in range(self.total_wood):
            wood = ItemDrop(
                pg.Vector2(
                    choice((self.rect.left - randint(5, 15), self.rect.right + randint(5, 15))), 
                    self.rect.top + (self.wood_image.height * i)
                ), 
                self.wood_image, 
                Z_LAYERS['main'], 
                self.wood_sprite_groups,
                self.sprite_manager,
                pg.Vector2(randint(-1, 1), 1),
                'wood'
            )
    # the tree map takes care of its coordinate position
    def get_save_data(self) -> dict[str, int]:
        return {'current strength': self.current_strength}