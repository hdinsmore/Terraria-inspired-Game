from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from input_manager import InputManager
    from player import Player
    from inventory import PlayerInventory
    from sprite_manager import SpriteManager
    from ui import UI
    
import pygame as pg
from dataclasses import dataclass

from settings import TILE_SIZE
from item_drag import ItemDrag

@dataclass(slots=True)
class InventoryDimensions:
    outline_rect_expanded: pg.Rect
    outline_rect_closed: pg.Rect
    item_rect_base: pg.Rect
    slot_len: int
    num_cols: int
    num_rows: int


class InventoryUI:
    def __init__(self, ui: UI, input_manager: InputManager, sprite_manager: SpriteManager):  
        self.screen = ui.screen
        self.cam_offset = ui.cam_offset
        self.graphics = ui.assets['graphics']
        self.fonts = ui.assets['fonts']
        self.colors = ui.assets['colors']

        self.top = ui.mini_map.outline_h + ui.mini_map.padding

        self.player: Player = ui.player
        self.inventory: PlayerInventory = ui.player.inventory

        self.gen_outline = ui.gen_outline
        self.gen_bg = ui.gen_bg
        self.render_inv_item_name = ui.render_inv_item_name
        self.get_scaled_image = ui.get_scaled_image
        self.get_grid_xy = ui.get_grid_xy
        self.render_item_amount = ui.render_item_amount

        self.mech_sprites = sprite_manager.mech_sprites
        self.get_sprites_in_radius = sprite_manager.get_sprites_in_radius

        self.num_slots = ui.inventory.num_slots
        self.num_cols = 5
        self.num_rows_expanded = self.num_slots // self.num_cols
        self.num_rows_closed = 2
        self.num_rows = self.num_rows_closed
        self.max_idx_closed = (self.num_cols * self.num_rows_closed)

        self.slot_len = TILE_SIZE * 2
        self.padding = 5
        self.border_width = 1
        
        self.outline_width = self.slot_len * self.num_cols
        self.outline_rect_expanded = pg.Rect(self.padding, self.top, self.outline_width, self.slot_len * self.num_rows_expanded)
        self.outline_rect_closed = pg.Rect(self.padding, self.top, self.outline_width, self.slot_len * self.num_rows_closed)
        self.outline_rect = self.outline_rect_closed

        self.icon_size = pg.Vector2(TILE_SIZE, TILE_SIZE)
        self.icon_padding = ((self.slot_len, self.slot_len) - self.icon_size) // 2
        
        self.render = True
        self.expand = False

        inv_dims = InventoryDimensions(
            self.outline_rect_expanded, 
            self.outline_rect_closed, 
            pg.Rect(self.icon_padding, self.icon_size), 
            self.slot_len, 
            self.num_cols, 
            self.num_rows
        )

        self.item_drag = ItemDrag(ui, self, inv_dims, sprite_manager, input_manager)

        self.item_placement = None # not initialized yet

    def update_dimensions(self) -> None:
        if self.expand:
            self.num_rows = self.num_rows_expanded
            self.outline_rect = self.outline_rect_expanded
            self.item_drag.outline_rect = self.outline_rect_expanded
        else:
            self.num_rows = self.num_rows_closed
            self.outline_rect = self.outline_rect_closed
            self.item_drag.outline_rect = self.outline_rect_closed

    def render_bg(self) -> None:
        self.gen_bg(self.outline_rect)
        self.gen_outline(self.outline_rect)

    def render_slots(self) -> None:
        for x in range(self.num_cols):
            for y in range(self.num_rows):
                slot = pg.Rect(
                    (self.padding, self.top) + pg.Vector2(x * self.slot_len, y * self.slot_len), 
                    (self.slot_len - (self.border_width * 2), self.slot_len - (self.border_width * 2))
                )
                pg.draw.rect(self.screen, 'purple2', slot, self.border_width)

                self.check_slot_highlight(slot, x, y)

    def check_slot_highlight(self, slot: pg.Rect, col_idx: int, row_idx: int) -> None:
        if self.player.item_holding:
            slot_idx = (row_idx * self.num_cols) + col_idx
            if slot_idx <= 10 and slot_idx == self.inventory.index:
                hl_surf = pg.Surface(slot.size - pg.Vector2(self.border_width * 2, self.border_width * 2))
                hl_surf.fill('silver')
                hl_surf.set_alpha(25)
                self.screen.blit(hl_surf, hl_surf.get_rect(topleft=slot.topleft + pg.Vector2(self.border_width, self.border_width)))
        
    def render_icons(self) -> None:
        inv_contents = list(self.inventory.contents.items()) # storing in a list to avoid the 'dictionary size changed during iteration' error when removing placed items
        for item_name, item_data in inv_contents if self.expand else inv_contents[:self.max_idx_closed]:
            try:
                surf = self.get_item_surf(item_name)
                row, col = divmod(item_data['index'], self.num_cols) # determine the slot an item corresponds to
                topleft = self.outline_rect.topleft + pg.Vector2(col * self.slot_len, row * self.slot_len)
                padding = (pg.Vector2(self.slot_len, self.slot_len) - surf.get_size()) // 2
                rect = surf.get_rect(topleft=topleft + padding)
                self.screen.blit(surf, rect)

                self.render_item_amount(item_data['amount'], topleft + padding)
                self.render_inv_item_name(rect, item_name)
            except KeyError:
                pass

    def get_item_surf(self, name: str) -> pg.Surface:
        surf = self.graphics[name]
        return surf if surf.get_size() == self.icon_size else self.get_scaled_image(surf, name, *self.icon_size)

    def update(self) -> None:
        if self.render:
            self.render_bg()
            self.render_slots()
            self.render_icons()
            self.item_drag.update()