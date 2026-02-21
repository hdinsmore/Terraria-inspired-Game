from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from assembler import Assembler
    from ui import UI
    from machine_sprite_base import InvSlot

import pygame as pg
from math import ceil

from machine_ui import MachineUI

class AssemblerUI(MachineUI):
    def __init__(self, machine: Assembler):
        super().__init__(machine)
        self.bg_w = self.bg_h = 200

        self.slot_len = 50
        self.icon_size = self.slot_len * 0.6

        self.category_names = list(self.machine.item_category_data.keys())
        self.category_icons = self.get_icons(self.graphics['icons'], self.category_names)
        self.category_cols = 3
        self.category_rows = ceil(len(self.category_names) / self.category_cols)
        self.category_rect = pg.Rect((0, 0), (self.slot_len, self.slot_len))

        self.item_rows = self.item_cols = None
        self.item_surf = None
        self.machine_icons = None
        
        self.inv = self.machine.inv

        self.update_bg_dimensions()

    def get_icons(self, folder: dict[str, pg.Surface], keys: list[str], scale: int=None) -> dict[str, pg.Surface]:
        scale = (self.icon_size, self.icon_size) if scale is None else (self.slot_len * scale, self.slot_len * scale)
        return {k: pg.transform.scale(surf, scale) for k, surf in folder.items() if k in keys}

    def update_bg_dimensions(self) -> None:
        if not self.machine.item_category:
            self.bg_w = (self.category_cols * self.slot_len) + ((self.category_cols + 1) * self.padding)
            self.bg_h = (self.category_rows * self.slot_len) + ((self.category_rows + 1) * self.padding)
            self.bg_rect = self.update_bg_rect()
        elif not self.machine.item:
            num_icons = max(1, len(self.machine_icons)) # TODO: remove the max when you have all the graphics
            self.item_cols = min(5, num_icons)
            self.item_rows = ceil(num_icons / self.item_cols)
            self.bg_w = (self.item_cols * self.slot_len) + ((self.item_cols + 1) * self.padding)
            self.bg_h = (self.item_rows * self.slot_len) + ((self.item_rows + 1) * self.padding) + self.padding + self.slot_len # last 2 additions to save room for the category rect
        else:
            num_slots = len(self.machine.recipe) + 1 # plus the output slot
            self.bg_w = (num_slots * self.slot_len) + (self.padding * ((num_slots % self.item_cols) + 1))
            self.bg_h = self.slot_len + self.category_rect.height + (self.padding * (self.item_rows + 1))

    def render_item_categories(self) -> None:
        if not self.machine.item_category:
            for x in range(self.category_cols):
                for y in range(self.category_rows):
                    x_padding = (self.padding * (x + 1)) + (x * self.slot_len)
                    y_padding = (self.padding * (y + 1)) + (y * self.slot_len)
                    outline = pg.Rect(self.bg_rect.topleft + pg.Vector2(x_padding, y_padding), (self.slot_len, self.slot_len))
                    self.gen_bg(outline, self.colors['ui bg highlight'] if outline.collidepoint(self.mouse.screen_xy) else 'black') 
                    self.gen_outline(outline)

                    category = self.category_names[x + (y * self.category_cols)]
                    icon = self.icons[category]
                    self.screen.blit(icon, icon.get_rect(center=outline.center))

                    font = self.fonts['item label small'].render(category, True, self.colors['text'])
                    self.screen.blit(font, font.get_rect(midtop=outline.midbottom + pg.Vector2(0, 1)))
                    self.get_category_input(outline, category)
        elif not self.machine.item:
            self.category_rect = pg.Rect(
                self.bg_rect.topleft + pg.Vector2((self.bg_w // 2) - (self.slot_len // 2), self.padding), 
                (self.slot_len, self.slot_len)
            )
            self.screen.blit(self.icons[self.machine.item_category], self.category_rect)

            font = self.fonts['item label'].render(self.machine.item_category, True, self.colors['text'])
            self.screen.blit(font, font.get_rect(midtop=self.category_rect.midbottom - pg.Vector2(0, 8))) # subtracting since the icon is smaller than the rect

            self.render_item_options()
        else:
            self.category_rect = pg.Rect(self.bg_rect.topleft + pg.Vector2((self.bg_w // 2) - (self.slot_len // 2), 5), (self.slot_len, self.slot_len))
            self.screen.blit(self.item_surf, self.category_rect)

            font = self.fonts['item label small'].render(self.machine.item, True, self.colors['text'])
            self.screen.blit(font, font.get_rect(midtop=self.category_rect.midbottom + pg.Vector2(0, 1)))
            for item in self.machine.recipe:
                font = self.fonts['item label small'].render(item, True, self.colors['text'])
                self.screen.blit(font, font.get_rect(midtop=self.inv.input_slots[item].rect.midbottom + pg.Vector2(0, self.progress_bar_height + 2)))

            self.render_slots(item_preview=True)
    
    def get_category_input(self, slot: InvSlot, category: str) -> None:
        if slot.collidepoint(self.mouse.screen_xy) and self.mouse.buttons_pressed['left']:
            self.machine.item_category = category
            self.machine_icons = self.get_icons(self.graphics, self.machine.item_category_data[category].keys())
            self.update_bg_dimensions() 

    def render_item_options(self) -> None:
        icon_names, icon_surfs = list(self.machine_icons.keys()), list(self.machine_icons.values())
        y = self.category_rect.bottom - self.bg_rect.top
        for i in range(len(icon_names)):
            row, col = divmod(i, self.item_cols)
            x_padding = (self.padding * (col + 1)) + (col * self.slot_len)
            y_padding = y + (self.padding * (row + 1)) + (row * self.slot_len)
            outline = pg.Rect(self.bg_rect.topleft + pg.Vector2(x_padding, y_padding), (self.slot_len, self.slot_len))
            if outline.collidepoint(self.mouse.screen_xy):
                color = self.colors['ui bg highlight']
                if self.mouse.buttons_pressed['left']:
                    self.machine.assign_item(i)
                    self.item_surf = pg.transform.scale(self.graphics[self.machine.item].copy(), self.category_rect.size)
                    self.update_bg_dimensions()

                font = self.fonts['item label small'].render(icon_names[i], True, self.colors['text'])
                self.screen.blit(font, font.get_rect(midtop=outline.midbottom + pg.Vector2(0, 1)))
            else:
                color = 'black'
            self.gen_bg(outline, color) 
            self.gen_outline(outline)

            icon_surf = icon_surfs[i]
            self.screen.blit(icon_surf, icon_surf.get_rect(center=outline.center))

    def update_slot_rects(self) -> None:
        y = self.padding + self.category_rect.bottom - self.bg_rect.top
        if self.machine.recipe is not None:
            for i, item in enumerate(self.machine.recipe):
                rect = pg.Rect(
                    self.bg_rect.topleft + pg.Vector2((self.padding * (i + 1)) + (i * self.slot_len), y), 
                    (self.slot_len, self.slot_len)
                )
                if item not in self.machine.inv.input_slots:
                    self.inv.input_slots[item] = InvSlotSlot(item, rect, valid_inputs={item})
                else:
                    self.inv.input_slots[item].rect = rect
            self.inv.output_slot.rect = pg.Rect(
                self.inv.input_slots[list(self.machine.recipe.keys())[-1]].rect.topleft + pg.Vector2(self.slot_len + self.padding, 0), 
                (self.slot_len, self.slot_len) 
            )

    def check_selection_undo(self) -> None:
        if self.keyboard.pressed_keys[pg.K_x] and self.machine.rect.collidepoint(self.mouse.world_xy):
            self.machine.item_category = self.machine_icons = None
            self.update_bg_dimensions()
            
    def render(self) -> None:
        super().render()
        self.render_item_categories()
        for slot in [s for s in [*self.inv.input_slots.values(), self.inv.output_slot] if s.rect]:
            self.render_progress_bar(
                slot.rect, 
                self.machine.alarms[next(iter(slot.valid_inputs))].percent, 
                self.slot_len, 
                y_padding=2, 
                color=self.colors['progress bar']
            )
        self.check_selection_undo()