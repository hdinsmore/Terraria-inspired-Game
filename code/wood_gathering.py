from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sprite_manager import SpriteManager
    import numpy as np
    import pygame as pg

from settings import TILE_SIZE

class WoodGathering:
    def __init__(self, sprite_manager: SpriteManager):
        self.tile_map: np.ndarray = sprite_manager.tile_map
        self.names_to_ids: dict[str, int] = sprite_manager.names_to_ids

        self.tree_sprites: pg.sprite.Group = sprite_manager.tree_sprites
        self.tree_map: list[tuple[int, int]] = sprite_manager.tree_map

        self.cam_offset: pg.Vector2 = sprite_manager.cam_offset
        
        self.get_tool_strength: callable = sprite_manager.get_tool_strength
        self.pick_up_item: callable = sprite_manager.pick_up_item
        self.rect_in_sprite_radius: callable = sprite_manager.rect_in_sprite_radius

        self.reach_radius = TILE_SIZE * 3

    def make_cut(self, sprite: pg.sprite.Sprite, mouse_button_held: dict[str, bool], mouse_world_xy: tuple[int, int]) -> None:
        if mouse_button_held['left']:
            if sprite.item_holding and sprite.item_holding.split()[-1] == 'axe':
                if tree := next((t for t in self.tree_sprites if self.rect_in_sprite_radius(sprite, t.rect) and t.rect.collidepoint(mouse_world_xy)), None):
                    tree.cut_down(sprite, self.get_tool_strength, self.pick_up_item)

    def update(self, player: pg.sprite.Sprite, mouse_button_held: dict[str, bool], mouse_world_xy: tuple[int, int]) -> None:
        self.make_cut(player, mouse_button_held, mouse_world_xy)