from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    from input_manager import InputManager, Keyboard, Mouse
    from player import Player
    from ui import UI
    from machine_sprite_base import InvSlot

import pygame as pg
from itertools import chain

class MachineUI:
    def __init__(self, machine: pg.sprite.Sprite):
        self.machine = machine
        game_obj: Main = machine.game_obj

        self.screen: pg.Surface = machine.screen
        self.cam_offset: pg.Surface = machine.cam_offset

        self.keyboard: Keyboard = machine.keyboard
        self.mouse: Mouse = machine.mouse

        self.player: Player = machine.player

        assets = machine.assets
        self.graphics: dict[str, pg.Surface] = assets['graphics']
        self.fonts: dict[str, pg.font.Font] = assets['fonts']
        self.colors: dict[str, str] = assets['colors']

        self.gen_outline: callable = machine.gen_outline
        self.gen_bg: callable = machine.gen_bg
        self.render_item_amount: callable = machine.render_item_amount
        
        self.rect_in_sprite_radius = machine.rect_in_sprite_radius
       
        self.active = False
        self.mouse_hover = False

        self.bg_w = self.bg_h = 150
        self.padding = 15
        self.bg_rect = self.update_bg_rect()
        self.progress_bar_height = 4
        self.icons = self.graphics['icons']
        self.slot_len = 40
        self.line_width = 1

        self.machine_mask = pg.mask.from_surface(machine.image)
        self.machine_mask_surf = self.machine_mask.to_surface(setcolor=(20, 20, 20, 255), unsetcolor=(0, 0, 0, 0))

        self.empty_fuel_surf = pg.transform.scale(
            self.icons['empty fuel'].convert_alpha(), 
            pg.Vector2(machine.image.get_size()) * 0.8
        )
        self.empty_fuel_surf.set_colorkey((255, 255, 255))
        self.empty_fuel_surf.set_alpha(150)

        self.key_close_ui = self.keyboard.key_bindings['close ui window']

        self.inv = machine.inv
        
    def update_bg_rect(self) -> pg.Rect:
        return pg.Rect(
            self.machine.rect.midtop - self.cam_offset - pg.Vector2(self.bg_w // 2, self.bg_h + self.padding), 
            (self.bg_w, self.bg_h)
        )

    def get_slot_input(self) -> InvSlot | None:
        return next((slot for slot in self.inv if slot.rect and slot.rect.collidepoint(self.mouse.xy_screen)), None)

    def input_item(self, slot: InvSlot, amount: int) -> None: 
        if self.player.item_holding in slot.valid_inputs:
            if slot.item is None:
                slot.item = self.player.item_holding
            slot.amount += amount
            self.player.inventory.remove_item(amount=amount)

    def extract_item(self, slot: InvSlot, click_type: str) -> None:
        amount = slot.amount if click_type == 'left' else max(1, slot.amount // 2)
        slot.amount -= amount
        self.player.inventory.add_item(slot.item, amount)
        if slot.amount == 0:
            slot.item = None
            
    def highlight_surf_when_hovered(self) -> None:
        if self.mouse_hover:
            self.screen.blit(
                self.machine_mask_surf, 
                self.machine.rect.topleft - self.cam_offset, 
                special_flags=pg.BLEND_RGBA_ADD
            )

    def render_slots(self, icon_scale: int=None, item_preview: bool=False) -> None: 
        self.update_slot_rects()
        for name, slot in chain(self.inv.input_slots.items(), [('output', self.inv.output_slot)]):
            if slot.rect:
                if slot.rect.collidepoint(self.mouse.xy_screen):
                    if slot.valid_inputs and self.player.item_holding:
                        color = 'forestgreen' if self.player.item_holding in slot.valid_inputs else 'crimson'
                    else:
                        color = self.colors['ui bg highlight']
                else:
                    color = 'black'

                self.gen_bg(slot.rect, color, alpha=50) 
                self.gen_outline(slot.rect)

                if slot.item or (item_preview and slot.valid_inputs): # checking valid inputs to avoid rendering a preview of nothing if the assembler's output slot is empty
                    self.render_slot_contents(slot, icon_scale, item_preview)
        
    def render_slot_contents(self, slot: InvSlot, icon_scale: int | None=None, item_preview: bool=False) -> None:
        try:
            surf = self.graphics[slot.item if not item_preview else next(iter(slot.valid_inputs))].copy() # valid_inputs only contains 1 string
        except KeyError:
            return

        if icon_scale:
            surf = pg.transform.scale(surf, pg.Vector2(surf.get_size()) * icon_scale)
        if not slot.amount > 0 and item_preview:
            surf.set_alpha(150)
        self.screen.blit(surf, surf.get_frect(center=slot.rect.center))

        if slot.amount:
            self.render_item_amount(slot.amount, slot.rect.bottomright - pg.Vector2(5, 5))

    def update_inv_slot(self, smelt: bool=False, burn_fuel: bool=False) -> None:
        slot_data = self.inv.input_slots['smelt' if smelt else 'burn fuel']
        slot_data.amount -= 1
        if not slot_data.amount:
            slot_data.item = None
            self.active = False

        if smelt and slot_data.item:
            if not self.inv.output_slot.item:
                self.inv.output_slot.item = self.can_smelt[slot_data.item]['output']
            self.inv.output_slot.amount += 1

    def render_progress_bar(
        self, 
        rect: pg.Rect, 
        percent: float, 
        width: int | None=None, 
        outline_color: str='black',
        fill_color: str='forestgreen'
    ) -> None:
        w = width if width else self.slot_len
        outline = pg.Rect(rect.midbottom + pg.Vector2(-(w // 2), 3), (w, self.progress_bar_height))

        progress_percent = percent / 100
        padding = pg.Vector2(self.line_width, self.line_width)
        progress_image = pg.Surface((
            max(1, (outline.width * progress_percent) - (self.line_width * 2)), 
            self.progress_bar_height - (self.line_width * 2)
        )) 
        progress_image.fill(fill_color)
        progress_image.set_alpha(255 * progress_percent)
        self.screen.blit(progress_image, progress_image.get_rect(topleft=outline.topleft + padding))
        
        pg.draw.rect(self.screen, outline_color, outline, self.line_width)

    def update_fuel_status(self) -> None:
        slots = self.inv.input_slots
        if 'smelt' in slots and not slots['fuel'].item:
            self.screen.blit(
                self.empty_fuel_surf, 
                self.empty_fuel_surf.get_rect(center=self.machine.rect.center - self.cam_offset)
            )

    def render(self, bg_color: str | None=None, outline_color: str | None=None) -> None:
        self.bg_rect = self.update_bg_rect()
        self.active = self.rect_in_sprite_radius(self.player, self.bg_rect, rect_world_space=False)
        if self.active:
            self.gen_bg(self.bg_rect, color=bg_color if bg_color else 'black', alpha=200)
            self.gen_outline(self.bg_rect, color=outline_color if outline_color else 'black')
            self.render_slots()

    def update(self, bg_color: str | None=None, outline_color: str | None=None) -> None:
        self.mouse_hover = self.machine.rect.collidepoint(self.mouse.xy_world)
        self.highlight_surf_when_hovered()

        if not self.active:
            self.active = self.mouse_hover and self.mouse.buttons_pressed['left']
        elif self.keyboard.held_keys[self.key_close_ui]:
            self.active = False
        else:
            self.render(bg_color, outline_color)

        self.update_fuel_status()