from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    from ui import UI
    
import pygame as pg
from abc import ABC

from machine_sprite_base import Machine, Inv, InvSlot
from furnace_ui import FurnaceUI
from alarm import Alarm
from settings import Z_LAYERS, PRODUCTION

class Furnace(Machine, ABC):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: pg.Vector2, 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
    ):  
        super().__init__(save_data=save_data, xy=xy, image=image, sprite_groups=sprite_groups, game_obj=game_obj, ui=ui)
        self.can_smelt = {
            'copper': {'speed': 3000, 'output': 'copper plate'}, 
            'iron': {'speed': 5000, 'output': 'iron plate'},
            'iron plate': {'speed': 7000, 'output': 'steel plate'},
        }

        self.inv = Inv(
            input_slots={
                'burn fuel': InvSlot(valid_inputs=self.fuel_sources.keys()), 
                'smelt': InvSlot(valid_inputs=self.can_smelt.keys())
            }
        )

        self.alarms = {}

    def update_active_state(self) -> None:
        self.active = self.inv.input_slots['smelt'].item and self.inv.input_slots['fuel'].item and \
        self.inv.output_slot.amount < self.inv.output_slot.max_capacity
        if not self.active:
            self.alarms.clear()
    
    def smelt(self) -> None:
        if not self.alarms:
            self.alarms['smelt'] = Alarm(
                length=self.can_smelt[self.inv.input_slots['smelt'].item]['speed'] // self.speed_factor, 
                function=self.update_inv_slot, 
                auto=True, 
                loop=True, 
                track_percent=True, 
                smelt=True
            )
            self.alarms['smelt'].start()

            if self.variant == 'burner':
                self.alarms['burn fuel'] = Alarm(
                    length=self.can_smelt[self.inv.input_slots['smelt'].item]['speed'] // self.speed_factor, 
                    function=self.update_inv_slot, 
                    auto=True, 
                    loop=True, 
                    track_percent=True,
                    fuel=True
                )
                self.alarms['burn fuel'].start()

        for alarm in self.alarms.values():
            alarm.update()

    def get_save_data(self) -> dict[str, list|str]:
        return {
            'xy': list(self.rect.topleft), 
            'smelt input': self.smelt_input, 
            'fuel input': self.fuel_input, 
            'output': self.output
        }

    def update(self, dt: float) -> None:
        self.ui.update()
        self.update_active_state()
        if self.active:
            self.smelt()
        
            
class BurnerFurnace(Furnace):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: pg.Vector2, 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
    ):  
        self.fuel_sources = {
            'wood': {'capacity': 99, 'burn speed': 2000}, 
            'coal': {'capacity': 99, 'burn speed': 4000}
        }
        super().__init__(save_data=save_data, xy=xy, image=image, sprite_groups=sprite_groups, game_obj=game_obj, ui=ui)
        self.variant = 'burner'
        self.recipe = PRODUCTION['burner furnace']['recipe']
        self.speed_factor = 1
        self.init_ui(FurnaceUI)


class ElectricFurnace(Furnace):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: pg.Vector2, 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
    ):  
        super().__init__(save_data=save_data, xy=xy, image=image, sprite_groups=sprite_groups, game_obj=game_obj, ui=ui)
        self.variant = 'electric'
        self.recipe = MACHINES['electric furnace']['recipe']
        self.inv = Inventory(input_slots={'smelt': InvSlot(valid_inputs=self.can_smelt.keys())})
        self.fuel_sources = {'electric poles'}
        self.speed_factor = 2.5
        self.init_ui(FurnaceUI)