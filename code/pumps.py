from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    from ui import UI

import pygame as pg

from machine_sprite_base import Machine, Inv, InvSlot
from settings import Z_LAYERS
from alarm import Alarm
from pump_ui import PumpUI

class Pump(Machine):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: tuple[int, int], 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
        direction: str
    ):
        image = image.copy()
        super().__init__(save_data, xy, image, sprite_groups, game_obj, ui)
        self.direction = direction if not save_data else save_data['direction']

        self.names_to_ids = self.game_obj.proc_gen.names_to_ids

        self.inv = Inv(input_slots={'fuel': InvSlot(valid_inputs={'coal', 'wood'})})
        
        self.liquid = None if not save_data else save_data['liquid']
        self.extract_speed = {'water': 1200, 'lava': 2400}
        self.fuel_burn_speed = {'wood': 1000, 'coal': 3000}
        self.alarms = {
            'extract liquid': Alarm(None, self.extract_liquid, False, False, True),
            'burn fuel': Alarm(None, None, False, False, True, burn_fuel=True)
        }

        self.init_ui(PumpUI)
        self.alarms['burn fuel'].function = self.ui.update_inv_slot

    def extract_liquid(self) -> None:
        pass

    def update(self, dt: float=None) -> None:
        if self.active:
            if not self.alarm.running:
                self.alarm.speed = self.speed[self.liquid]
                self.alarm.start()
            else:
                self.alarm.update()

        self.game_obj.sprite_manager.check_dir_flip(self)
        self.ui.render()

    def get_save_data(self) -> dict[str, any]:
        return {
            'active': self.active, 
            'direction': self.direction, 
            'liquid': self.liquid
        }


class InletPump(Pump):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: tuple[int, int], 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
        direction: str
    ):  
        super().__init__(save_data, xy, image, sprite_groups, game_obj, ui, direction)
        if self.direction == 'right':
            self.image = pg.transform.flip(self.image, True, False)


class OutletPump(Pump):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: tuple[int, int], 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
        direction: str
    ):
        super().__init__(save_data, xy, image, sprite_groups, game_obj, ui, direction)
        if self.direction == 'left':
            self.image = pg.transform.flip(self.image, True, False)