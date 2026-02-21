from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sprite_manager import SpriteManager
    from ui import UI

import pygame as pg

from machine_sprite_base import Machine, Inv, InvSlot
from settings import PRODUCTION, LOGISTICS, ELECTRICITY, MATERIALS, STORAGE, RESEARCH 
from assembler_ui import AssemblerUI
from alarm import Alarm

class Assembler(Machine):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: tuple[int, int], 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI | None
    ):
        super().__init__(save_data=save_data, xy=xy, image=image, sprite_groups=sprite_groups, game_obj=game_obj, ui=ui)
        self.inv = Inv(input_slots={})
        self.item_category = self.item = self.recipe = None
        self.item_category_data = {
            'production': PRODUCTION, 
            'logistics': LOGISTICS, 
            'electricity': ELECTRICITY, 
            'materials': MATERIALS, 
            'storage': STORAGE, 
            'research': RESEARCH
        }
        self.assemble_progress = {}
        self.alarms = {}
        self.init_ui(AssemblerUI)

    def assign_item(self, idx: int) -> None:
        data = self.item_category_data[self.item_category]
        self.item = list(data.keys())[idx]
        self.inv.output_slot.valid_inputs = {self.item}
        self.recipe = list(data.values())[idx]['recipe']
        for dict_ in (self.inv.input_slots, self.alarms, self.assemble_progress):
            dict_.clear()
        for item in self.recipe:
            self.assemble_progress[item] = 0
            self.inv.input_slots[item] = InvSlot(item, valid_inputs={item}) # assigning the rect in the ui class
            self.alarms[item] = Alarm(2500, self.update_slot, loop=True, track_percent=True, slot=self.inv.input_slots[item]) # TODO: have alarm length vary by material
        self.alarms[self.item] = Alarm(max(self.recipe.values()) * 2500, loop=True, track_percent=True, slot=self.inv.output_slot)
    
    def update_slot(self, slot: InvSlot) -> None:
        slot.amount -= 1
        self.assemble_progress[slot.item] += 1
        if not slot.amount:
            slot.item = None

    def assemble_item(self) -> None:
        if self.inv.input_slots and all(slot.amount > 0 for slot in self.inv.input_slots.values()):
            for alarm in self.alarms.values():
                if not alarm.running:
                    alarm.start()
                else:
                    alarm.update()
            if all(self.assemble_progress[item] >= self.recipe[item] for item in self.recipe):
                if not self.inv.output_slot.item:
                    self.inv.output_slot.item = self.item
                self.inv.output_slot.amount += 1
                for item in self.recipe:
                    self.assemble_progress[item] = 0

    def update(self, dt=None) -> None:
        self.assemble_item()
        self.ui.update()