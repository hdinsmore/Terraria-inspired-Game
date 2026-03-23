import pygame as pg 

from machine_ui import MachineUI

class PumpUI(MachineUI):
    def __init__(self, machine: pg.sprite.Sprite):
        super().__init__(machine)
        self.liquid_icon = None # the Pump class searches for the nearby liquid type and updates this variable after
        self.outline_colors = {
            'water': 'aqua',
            'lava': 'orangered',
            'honey': 'goldenrod'
        }

    def update_slot_rects(self) -> None:
        self.inv.input_slots['fuel'].rect = pg.Rect(
            self.bg_rect.topleft + pg.Vector2(self.padding + self.slot_len, (self.padding * 2) + self.liquid_icon.get_height() + 5), 
            (self.slot_len, self.slot_len)
        )

    def render(self) -> None:
        if self.machine.liquid:
            outline_color = self.outline_colors[self.machine.liquid]
            liquid_icon_rect = self.liquid_icon.get_rect(midtop=self.bg_rect.midtop + pg.Vector2(0, self.padding))
            super().render(outline_color=outline_color)
            self.screen.blit(self.liquid_icon, liquid_icon_rect)
            self.render_progress_bar(
                liquid_icon_rect, 
                self.machine.alarms['extract liquid'].percent if self.machine.alarms['extract liquid'].running else 0, 
                outline_color=outline_color
            )
        else:
            super().render(outline_color='silver')
            if self.liquid_icon:
                self.screen.blit(self.liquid_icon, self.liquid_icon.get_rect(midtop=self.bg_rect.midtop + pg.Vector2(0, self.padding)))

        if self.machine.inv.input_slots['fuel'].item:
            self.render_progress_bar(
                self.inv.input_slots['fuel'].rect, 
                self.machine.alarms['burn fuel'].percent if self.machine.alarms['burn fuel'].running else 0,
                outline_color=outline_color
            )
        else:
            self.screen.blit(self.empty_fuel_surf, self.empty_fuel_surf.get_rect(center=self.machine.rect.center))