import pygame as pg 

from machine_ui import MachineUI

class PumpUI(MachineUI):
    def __init__(self, machine: pg.sprite.Sprite):
        super().__init__(machine)
        self.water_icon = self.icons['water droplet'].convert_alpha()
        self.water_icon_height = self.water_icon.get_height()

    def update_slot_rects(self) -> None:
        self.inv.input_slots['fuel'].rect = pg.Rect(
            self.bg_rect.topleft + pg.Vector2(self.padding + self.slot_len, (self.padding * 2) + self.water_icon_height + 5), 
            (self.slot_len, self.slot_len)
        )

    def render(self) -> None:
        super().render()
        water_icon_rect = self.water_icon.get_rect(midtop=self.bg_rect.midtop + pg.Vector2(0, self.padding))
        self.screen.blit(self.water_icon, water_icon_rect)
        self.render_progress_bar(
            water_icon_rect, 
            self.machine.alarms['extract liquid'].percent if self.machine.alarms['extract liquid'].running else 0, 
            outline_color='silver'
        )

        self.render_progress_bar(
            self.inv.input_slots['fuel'].rect, 
            self.machine.alarms['burn fuel'].percent if self.machine.alarms['burn fuel'].running else 0,
            outline_color='silver'
        )