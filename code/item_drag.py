from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui import UI
    from inventory_ui import InventoryUI, InventoryDimensions
    from sprite_manager import SpriteManager
    from input_manager import InputManager

import pygame as pg

from settings import MATERIALS, TILES, TILE_SIZE, PLACEABLE_ITEMS, PIPE_TRANSPORT_DIRS, PRODUCTION, ITEMS_CAN_FLIP, DEFAULT_ITEM_FLIP_DIRS

class ItemDrag:
    def __init__(
        self, 
        ui: UI, 
        inv_ui: InventoryUI, 
        inv_dims: InventoryDimensions, 
        sprite_manager: SpriteManager, 
        input_manager: InputManager
    ):
        self.screen = ui.screen
        self.cam_offset = ui.cam_offset
        self.graphics = ui.assets['graphics']
        self.player = ui.player
        self.get_grid_xy = ui.get_grid_xy
        self.inv_ui = inv_ui
        
        self.outline_rect_expanded = inv_dims.outline_rect_expanded
        self.outline_rect_closed = inv_dims.outline_rect_closed
        self.outline_rect = self.inv_ui.outline_rect
        self.item_rect_base = inv_dims.item_rect_base

        self.slot_len = inv_dims.slot_len
        self.num_cols = inv_dims.num_cols
        self.num_rows = inv_dims.num_rows

        self.get_sprites_in_radius = sprite_manager.get_sprites_in_radius
        self.mech_sprites = sprite_manager.mech_sprites

        self.keyboard = input_manager.keyboard
        self.mouse = input_manager.mouse

        self.active = False
        self.image = None 
        self.rect = None
        self.amount = None

        self.material_names = set(MATERIALS.keys()) 
        self.tile_names = set(TILES.keys())

        self.machine_recipes = {item for machine in PRODUCTION.values() for item in machine['recipe']}
        self.machine_inputs = (self.material_names | self.tile_names | self.machine_recipes)

        self.old_pipe_idx = None # storing the original pipe index if it gets rotated while being dragged
        self.can_flip_item = False

        self.item_placement = None # not initialized yet

    def check_drag(self) -> None:
        l_click, r_click = self.mouse.buttons_pressed.values()
        if l_click or r_click:
            self.handle_click(l_click, r_click)
        else:
            if self.active:
                self.render_item_drag()
                self.check_keyboard_input()

    def handle_click(self, l_click: bool, r_click: bool) -> None:
        if self.active:
            if r_click:
                self.amount //= 2
            else:
                self.end_drag()
        else:
            if self.outline_rect.collidepoint(self.mouse.xy_screen):
                if self.check_inv_click():
                    self.start_drag('left' if l_click else 'right')   
            else:
                if machines_with_inv := [
                    m for m in self.get_sprites_in_radius(self.player.rect, self.mech_sprites) 
                    if hasattr(m, 'inv') and m.ui.render
                ]:
                    self.check_machine_extract(machines_with_inv, l_click, r_click)

    def check_inv_click(self) -> bool:
        for item_name, item_data in self.player.inventory.contents.items():
            row, col = divmod(item_data['index'], self.num_cols)
            padding = pg.Vector2(col * self.slot_len, row * self.slot_len)
            if (rect := self.item_rect_base.move(self.outline_rect.topleft + padding)).collidepoint(self.mouse.xy_screen):
                self.player.item_holding = item_name
                return True
        return False

    def check_keyboard_input(self) -> None:
        if self.keyboard.pressed_keys[self.keyboard.key_bindings['stop holding item']]:
            self.update_item_data(remove=True)
        elif self.keyboard.pressed_keys[self.keyboard.key_bindings['rotate item']]:
            if 'pipe' in self.player.item_holding:
                self.rotate_pipe()
            elif self.can_flip_item:
                self.player.item_flip_dir = 'right' if self.player.item_flip_dir == 'left' else 'left'
                self.image = pg.transform.flip(self.image, True, False)

    def start_drag(self, click_type: str) -> None:
        self.player.inventory.index = self.player.inventory.contents[self.player.item_holding]['index']
        self.update_item_data(click_type, add=True)
        if self.player.item_holding in ITEMS_CAN_FLIP:
            self.player.item_flip_dir = DEFAULT_ITEM_FLIP_DIRS[self.player.item_holding]
            self.can_flip_item = True

    def end_drag(self) -> None: 
        if self.player.item_holding: # prevents a KeyError from trying to place an item immediately before dying and having item_holding set to None
            if self.player.item_holding in self.machine_inputs and not self.item_placement.valid_placement( # calling valid_placement to distinguish between placing e.g a copper block in the smelt compartment vs on the ground
                self.item_placement.get_tiles_covered(self.mouse.xy_world_tile, self.graphics[self.player.item_holding]), self.player
            ): 
                self.place_item_in_machine()
            else:
                if self.player.item_holding in PLACEABLE_ITEMS:
                    self.item_placement.place_item(self.player, self.mouse.xy_world_tile, self.old_pipe_idx)
                    
            if self.player.item_holding not in self.player.inventory.contents: # placed the last of its kind
                self.update_item_data(remove=True)
            else:
                if self.player.item_holding in ITEMS_CAN_FLIP:
                    if self.player.item_flip_dir != DEFAULT_ITEM_FLIP_DIRS[self.player.item_holding]:
                        self.player.item_flip_dir = DEFAULT_ITEM_FLIP_DIRS[self.player.item_holding]
                        self.image = pg.transform.flip(self.image, True, False)

    def update_item_data(self, click_type: str=None, add: bool=False, remove: bool=False) -> None:
        if add:
            self.image = self.graphics[self.player.item_holding].copy() # a copy to not alter the alpha value of the original
            self.image.set_alpha(100)
            self.rect = self.image.get_rect(center=self.mouse.xy_world)
            item_amount = self.player.inventory.contents[self.player.item_holding]['amount'] 
            self.amount = item_amount if click_type in {'left', None} else (item_amount // 2)
        else:
            self.player.item_holding = None
            self.image = None
            self.rect = None
            self.amount = 0
            self.old_pipe_idx = None
            self.player.item_flip_dir = None
            self.can_flip_item = False

        self.active = add

    def render_item_drag(self) -> None:
        self.rect.topleft = self.get_grid_xy()
        self.screen.blit(self.image, self.rect)
        if self.player.item_holding in PLACEABLE_ITEMS:
            item_xy_world = (pg.Vector2(self.rect.topleft) + self.cam_offset) // TILE_SIZE
            self.item_placement.render_ui(self.image, self.rect, (int(item_xy_world.x), int(item_xy_world.y)), self.player)
    
    def rotate_pipe(self) -> None:
        if self.old_pipe_idx is None:
            self.old_pipe_idx = int(self.player.item_holding[-1])

        idx = (int(self.player.item_holding[-1]) + 1) % len(PIPE_TRANSPORT_DIRS)
        self.image = self.graphics[f'pipe {idx}']
        self.player.item_holding = f'pipe {idx}'

    def place_item_in_machine(self) -> None:
        for machine in [m for m in self.get_sprites_in_radius(self.player.rect, self.mech_sprites) if hasattr(m, 'inv') and m.ui.render]:
            if slot := machine.ui.get_slot_input():
                machine.ui.input_item(slot, self.amount)
                self.player.item_holding = None
                return
    
    def check_machine_extract(self, machines: list[pg.sprite.Sprite], l_click: bool, r_click: bool) -> None:
        for machine in machines:
            for slot in machine.inv:
                if isinstance(slot, dict):
                    for s in slot.values():
                        if s.amount and rect.collidepoint(self.mouse.xy_screen):
                            machine.ui.extract_item(s, 'left' if l_click else 'right')
                            return
                else:
                    if slot.amount and slot.rect.collidepoint(self.mouse.xy_screen):
                        machine.ui.extract_item(slot, 'left' if l_click else 'right')
                        return

    def update(self) -> None:
        if self.player.item_holding and not self.active:
            self.update_item_data(add=True)

        self.check_drag()