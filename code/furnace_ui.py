from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui import UI
    from furnaces import Furnace

import pygame as pg
from math import ceil

from machine_ui import MachineUI
    
class FurnaceUI(MachineUI):
    def __init__(self, machine: Furnace):
        super().__init__(machine)
        self.is_burner = self.machine.variant == 'burner'
        if self.is_burner:
            self.y_offset = self.padding
            self.num_smelt_bars = 6
            self.smelt_bar_width = 3
        else:
            self.y_offset = (self.slot_len // 2)

        self.arrow_rect_width, self.arrow_rect_height = 10, 8
        self.arrow_triangle_width, self.arrow_triangle_height = 10, 20
        self.arrow_rect_width_percent = (self.arrow_rect_width / (self.arrow_rect_width + self.arrow_triangle_width)) * 100

    def update_slot_rects(self) -> None:
        self.inv.input_slots['smelt'].rect = pg.Rect(
            self.bg_rect.topleft + pg.Vector2(self.padding, self.y_offset), 
            (self.slot_len, self.slot_len)
        )

        self.inv.output_slot.rect = pg.Rect(
            self.bg_rect.midright - pg.Vector2(self.slot_len + self.padding, self.slot_len // 2), 
            (self.slot_len, self.slot_len)
        )

        if self.is_burner: 
            self.inv.input_slots['fuel'].rect = pg.Rect(
                self.bg_rect.bottomleft - pg.Vector2(-self.padding, self.slot_len + self.padding), 
                (self.slot_len, self.slot_len)
            )

    def render_smelt_bars(self) -> None:
        fuel_rect = self.inv.input_slots['fuel'].rect
        x_padding = (self.slot_len - 10) // self.num_smelt_bars # -10 for 5px of left/right padding
        progress_percent = 0 if not 'smelt' in self.machine.alarms else self.machine.alarms['smelt'].percent / 100
        for i in range(self.num_smelt_bars):
            if i in {0, self.num_smelt_bars - 1}:
                height = 15
            elif i in {self.num_smelt_bars // 2, (self.num_smelt_bars // 2) - 1}:
                height = 25
            else:
                height = 20

            image = pg.Surface((
                self.smelt_bar_width - (self.line_width * 2),
                max(1, (height * progress_percent) - (self.line_width * 2)) 
            ))
            image.fill('darkorange4')
            image.set_alpha(255 * progress_percent)
            rect = image.get_rect(bottomleft=(fuel_rect.left + 2 + (x_padding * (i + 1)), fuel_rect.top - 5))
            self.screen.blit(image, rect)
            # same as the rect except it stays at the max height
            outline = pg.Rect(
                (fuel_rect.left + 2 + (x_padding * (i + 1)), fuel_rect.top - (height + 5)),
                (rect.width, height)
            )
            self.gen_outline(outline, color='firebrick')
        
    def render_progress_arrow(self) -> None:
        available_width = self.inv.output_slot.rect.left - self.inv.input_slots['smelt'].rect.right
        center = self.inv.input_slots['smelt'].rect.right + (available_width // 2)
        left = center - (self.arrow_rect_width // 2) - 5
        available_height = self.inv.input_slots['fuel'].rect.top - self.inv.input_slots['smelt'].rect.bottom
        top = self.inv.input_slots['fuel'].rect.top - (available_height // 2) - (self.arrow_rect_height // 2)
        rect = pg.Rect((left, top), (self.arrow_rect_width, self.arrow_rect_height))
        pg.draw.rect(self.screen, 'orangered4', rect)

        pt1 = (rect.topright - pg.Vector2(0, (self.arrow_triangle_height - self.arrow_rect_height) // 2))
        pt2 = pt1 + pg.Vector2(self.arrow_triangle_width, self.arrow_triangle_height // 2)
        pt3 = pt1 + pg.Vector2(0, self.arrow_triangle_height)
        pg.draw.polygon(self.screen, 'orangered4', (pt1, pt2, pt3))

        if 'smelt' in self.machine.alarms:
            progress_percent = min(self.machine.alarms['smelt'].percent, self.machine.alarms['fuel'].percent)
            fill_image = pg.Surface((
                min(rect.width, rect.width * (progress_percent / self.arrow_rect_width_percent)),
                rect.height
            ))
            fill_image.fill('orangered3')
            self.screen.blit(fill_image, fill_image.get_rect(topleft=rect.topleft))

            if fill_image.width == rect.width:
                rect_width_percent = self.arrow_rect_width_percent / 100
                triangle_fill_percent = max(0.0, min(1.0, (progress_percent / 100) - rect_width_percent) / (1.0 - rect_width_percent))
                num_px_fill = ceil(self.arrow_triangle_width * triangle_fill_percent) 
                for i in range(num_px_fill):
                    line_height = self.arrow_triangle_height - (i * 2)
                    x, start_y = pt1.x + i, pt1.y + i
                    pg.draw.line(self.screen, 'orangered3', (x, start_y), (x, start_y + line_height))

    def render(self) -> None:
        super().render()
        
        if 'smelt' in self.machine.alarms:
            self.render_progress_bar(self.inv.input_slots['smelt'].rect, self.machine.alarms['smelt'].percent)
            if self.is_burner:
                self.render_progress_bar(self.inv.input_slots['fuel'].rect, self.machine.alarms['fuel'].percent) 
        
        if self.is_burner:
            self.render_smelt_bars()

        self.render_progress_arrow()