from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from input_manager import InputManager
    import numpy as np
    from sprite_manager import SpriteManager

import pygame as pg
from random import choice

from sprite_base_classes import AnimatedSprite
from inventory import SpriteInventory
from item_drop import ItemDrop
from settings import Z_LAYERS, GRAVITY, TILE_SIZE, BIOME_WIDTH
from alarm import Alarm

class Colonist(AnimatedSprite):
    def __init__(
        self,
        game_obj: Main,
        xy: pg.Vector2,
        frames: dict[str, pg.Surface],
        sprite_groups: list[pg.sprite.Group],
        move_speed: int=500,
        animation_speed: dict[str, int]={'walking': 8, 'mining': 4, 'jumping': 0},
        save_data: dict[str, any]=None
    ):
        super().__init__(game_obj, xy, frames, sprite_groups, move_speed, animation_speed)
        self.spawn_point = xy
        self.graphics = game_obj.asset_manager.assets['graphics']
        self.sprite_manager = game_obj.sprite_manager
        proc_gen = game_obj.proc_gen
        self.biome_order, self.idxs_to_biomes = proc_gen.biome_order, proc_gen.idxs_to_biomes
        self.save_data = save_data
        
        self.current_biome = game_obj.proc_gen.current_biome

        input_manager = game_obj.input_manager
        self.keyboard, self.mouse = input_manager.keyboard, input_manager.mouse

        self.facing_left = save_data['facing left'] if save_data else True
        self.grounded = False
        self.default_gravity = self.gravity
        self.default_jump_height, self.jump_height = 350, 350 

        self.inventory = SpriteInventory(self, None if not save_data else save_data['inventory data'])
        self.item_holding = save_data['item holding'] if save_data else None
        self.arm_strength = 4
        
        self.hp, self.max_hp = save_data['hp'] if save_data else 8, 8

        self.underwater = False
        self.oxygen_lvl, self.max_oxygen_lvl = 8, 8
        self.oxygen_icon = self.graphics['icons']['oxygen']
        self.oxygen_icon_w, self.oxygen_icon_h = self.oxygen_icon.get_size()

        self.alarms = {
            'lose oxygen': Alarm(length=2500, fn=self.lose_oxygen),
            'regen hp': Alarm(length=10000, fn=self.regen_hp)
        }
    
    def update_current_biome(self) -> None:
        if self.direction:
            biome = self.idxs_to_biomes[(self.rect.x // TILE_SIZE) // BIOME_WIDTH]
            if not self.current_biome or self.current_biome != biome:
                self.current_biome = biome
                        
    def check_oxygen_level(self) -> None:
        if self.underwater:
            if not self.alarms['lose oxygen'].running:
                self.alarms['lose oxygen'].start()
            self.render_oxygen_icons()

    def render_oxygen_icons(self) -> None:
        x_padding = self.oxygen_icon_w * (self.oxygen_lvl // 2)
        for i in range(self.oxygen_lvl):
            self.screen.blit(
                self.oxygen_icon, 
                self.rect.midtop - self.cam_offset + pg.Vector2((self.oxygen_icon_w * i) - x_padding, -self.oxygen_icon_h)
            ) 

    def lose_oxygen(self) -> None:
        if self.oxygen_lvl >= 1:
            self.oxygen_lvl -= 1
        else:
            self.hp -= 1
            if not self.hp:
                self.die()
    
    def die(self) -> None: 
        self.drop_inventory()
        if self.z == Z_LAYERS['player']: 
            self.respawn()
        else:
            self.kill()

    def drop_inventory(self) -> None:
        for item_name in self.inventory.contents:
            item = ItemDrop(
                self.rect.center,
                self.graphics[item_name],
                Z_LAYERS['main'],
                [self.sprite_manager.all_sprites, self.sprite_manager.active_sprites],
                self.sprite_manager,
                pg.Vector2(choice((-1, 1)), 1),
                item_name,
                self
            )

    def check_hp_level(self) -> None:
        if self.hp < self.max_hp and not self.underwater and not self.alarms['regen hp'].running:
            self.alarms['regen hp'].start()

    def regen_hp(self) -> None:
        self.hp += 1

    def update_alarms(self) -> None:
        for alarm in [a for a in self.alarms.values() if a.running]:
            alarm.update()

    def update(self, dt: float) -> None:
        self.update_current_biome()
        self.check_oxygen_level()
        self.check_hp_level()
        self.update_alarms()

    def get_save_data(self) -> dict[str, any]:
        return {
            'xy': self.spawn_point, 
            'current biome': self.current_biome, 
            'inventory data': {'contents': self.inventory.contents, 'index': self.inventory.index},
            'facing left': self.facing_left, 
            'hp': self.hp, 
            'item holding': self.item_holding
        }