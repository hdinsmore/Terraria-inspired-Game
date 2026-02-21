from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from drills import Drill
    from ui import UI

import pygame as pg

from machine_ui import MachineUI
from dataclasses import dataclass
from settings import TILE_SIZE

@dataclass
class OreSelectUI:
    available_ores: dict
    rect: pg.Rect=None
    amount: int=0
    slot_len: int=(TILE_SIZE * 2) + 2
    idx: int=0

class DrillUI(MachineUI):
    def __init__(self, machine: Drill):
        super().__init__(machine)
        self.bg_width = 200
        self.ore_names = list(self.machine.ore_data.keys())
        self.num_ores = len(self.ore_names)
        self.ore_surfs = {k: pg.transform.scale2x(self.graphics[k]) for k in self.ore_names}
        ore_data = self.machine.ore_data
        self.ore_select_ui = OreSelectUI(dict(zip(ore_data.keys(), [ore_data[k]['amount'] for k in ore_data])))

    def update_slot_rects(self) -> None:
        if self.machine.variant == 'burner':
            self.inv.input_slots['fuel'].rect = pg.Rect(
                self.bg_rect.bottomleft + pg.Vector2(self.padding, -(self.padding + self.slot_len)), 
                (self.slot_len, self.slot_len)
            )
            self.inv.output_slot.rect = pg.Rect(
                self.bg_rect.bottomright - pg.Vector2(self.slot_len + self.padding, self.slot_len + self.padding), 
                (self.slot_len, self.slot_len)
            )
        else:
            self.inv.output_slot.rect = pg.Rect(
                self.bg_rect.midbottom - pg.Vector2(0, self.padding), 
                (self.slot_len, self.slot_len)
            )
        self.ore_select_ui.rect = pg.Rect(
            self.bg_rect.midtop - pg.Vector2(self.ore_select_ui.slot_len // 2, -self.padding), 
            (self.ore_select_ui.slot_len, self.ore_select_ui.slot_len)
        )

    def render_ore_select_ui(self) -> None:
        self.gen_outline(self.ore_select_ui.rect)
        ore_name = self.ore_names[self.ore_select_ui.idx]
        if not self.machine.target_ore:
            self.update_target_ore() 
        elif not self.inv.output_slot.amount: # fade in a preview of the ore as it's extracted for the 1st time
            ore_preview_surf = self.graphics[ore_name].copy()
            ore_preview_surf.set_alpha(155 + int(self.machine.alarms['extract'].percent))
            self.screen.blit(ore_preview_surf, ore_preview_surf.get_rect(center=self.inv.output_slot.rect.center))
        ore_surf = self.ore_surfs[ore_name] 
        self.screen.blit(ore_surf, ore_surf.get_rect(center=self.ore_select_ui.rect.center))
        ore_name_surf = self.fonts['item label small'].render(ore_name, True, self.colors['text'])
        ore_name_rect = ore_name_surf.get_rect(midtop=self.ore_select_ui.rect.midbottom + pg.Vector2(0, self.padding // 2))
        self.screen.blit(ore_name_surf, ore_name_rect) 
        ore_amount_surf = self.fonts['item label small'].render(
            f'available: {self.machine.ore_data[ore_name]["amount"]}', 
            True, 
            self.colors['text']
        )
        self.screen.blit(ore_amount_surf, ore_amount_surf.get_rect(midtop=ore_name_rect.midbottom))

    def update_target_ore(self) -> None:
        if self.keyboard.pressed_keys[pg.K_RIGHT]:
            self.select_ui.idx = (self.ore_select_ui.idx + 1) % self.num_ores
        elif self.keyboard.pressed_keys[pg.K_LEFT]:
            self.select_ui.idx = (self.ore_select_ui.idx - 1) % self.num_ores  
        elif self.keyboard.pressed_keys[pg.K_RETURN]:
            ore_name = self.ore_names[self.ore_select_ui.idx]
            self.machine.target_ore = ore_name
            self.machine.num_ore_available = self.machine.ore_data[ore_name]['amount']

    def render(self) -> None:
        super().render()
        self.render_ore_select_ui()
        if self.machine.target_ore:
            self.render_progress_bar(
                self.inv.output_slot.rect, 
                self.machine.alarms['extract'].percent, 
                color=self.colors['progress bar']
            )
            if self.machine.variant == 'burner':
                self.render_progress_bar(
                    self.inv.input_slots['fuel'].rect, 
                    self.machine.alarms['burn fuel'].percent, 
                    color=self.colors['progress bar']
                )