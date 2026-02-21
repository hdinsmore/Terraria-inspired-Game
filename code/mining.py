from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sprite_manager import SpriteManager
    import numpy as np
    from player import Player
    from mouse import Mouse
    from keyboard import Keyboard

import pygame as pg

from settings import TILES, TILE_SIZE, TILE_REACH_RADIUS, FPS

class Mining:
    def __init__(self, sprite_manager: SpriteManager):
        self.sprite_manager = sprite_manager

        self.tile_map: np.ndarray = sprite_manager.tile_map
        self.names_to_ids: dict[str, int] = sprite_manager.names_to_ids

        self.mouse: Mouse = sprite_manager.mouse
        self.keyboard: Keyboard = sprite_manager.keyboard
        self.key_mine: int = sprite_manager.keyboard.key_bindings['mine']
        
        self.update_map: callable = sprite_manager.collision_map.update_map
        self.get_tool_strength: callable = sprite_manager.get_tool_strength
        self.pick_up_item: callable = sprite_manager.pick_up_item
        self.get_tile_material: callable = sprite_manager.get_tile_material
        self.end_action: callable = sprite_manager.end_action
        
        self.mining_map: dict[tuple[int, int]: dict[str, int]] = {}
        self.invalid_ids = {sprite_manager.names_to_ids[k] for k in ('air', 'water', 'tree base')} # can't be mined

    def run(self, sprite: pg.sprite.Sprite, dt: float) -> None:
        if sprite.item_holding and 'pickaxe' in sprite.item_holding:
            if self.valid_tile(sprite):
                sprite.state = 'mining'
                if self.mouse.xy_world_tile not in self.mining_map:
                    self.mining_map[self.mouse.xy_world_tile] = {
                        'hardness': TILES[self.get_tile_material(self.tile_map[self.mouse.xy_world_tile])]['hardness'], 
                        'hits': 0
                    }
                self.update_tile(sprite, dt) 
            else:
                if sprite.state == 'mining':
                    sprite.state = 'idle'

    def valid_tile(self, sprite: pg.sprite.Sprite) -> bool:
        sprite_coords = pg.Vector2(sprite.rect.center) // TILE_SIZE 
        return sprite_coords.distance_to(self.mouse.xy_world_tile) <= TILE_REACH_RADIUS and \
        self.tile_map[self.mouse.xy_world_tile] not in self.invalid_ids
    
    # TODO: decrease the strength of the current tool as its usage accumulates    
    def update_tile(self, sprite: pg.sprite.Sprite, dt: float) -> bool:   
        tile_data = self.mining_map[self.mouse.xy_world_tile]
        tile_data['hits'] += 1 / (FPS * dt)
        tile_data['hardness'] = max(0, tile_data['hardness'] - (self.get_tool_strength(sprite) * tile_data['hits']))
        if tile_data['hardness'] == 0:
            sprite.inventory.add_item(self.get_tile_material(self.tile_map[self.mouse.xy_world_tile]))
            self.tile_map[self.mouse.xy_world_tile] = self.names_to_ids['air']
            self.update_map(self.mouse.xy_world_tile, remove_tile=True)
            del self.mining_map[self.mouse.xy_world_tile]
    
    def update(self, dt: float) -> None:
        if self.keyboard.held_keys[self.key_mine]:
            self.run(self.sprite_manager.player, dt)
        else:
            if self.sprite_manager.player.state == 'mining':
                self.end_action(self.sprite_manager.player)