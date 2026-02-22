from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    from ui import UI

import pygame as pg

from machine_sprite_base import Machine, Inv, InvSlot
from settings import TILE_SIZE
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
        self.inv = Inv(input_slots={'fuel': InvSlot(valid_inputs={'coal', 'wood'})})
        # ui needs the inv attribute
        self.init_ui(PumpUI)

        if save_data:
            self.active = save_data['active']
            self.direction = save_data['direction']
            self.liquid = save_data['liquid']
        else:
            self.active = False
            self.direction = direction
            self.liquid = self.get_liquid_type()
    
        self.extract_speed = {'water': 1200, 'lava': 2400}
        self.fuel_burn_speed = {'wood': 1000, 'coal': 3000}
        self.alarms = {
            'extract liquid': Alarm(None, self.extract_liquid, False, False, True),
            'burn fuel': Alarm(self.ui.update_inv_slot, None, False, False, True, burn_fuel=True)
        }

    def get_liquid_type(self) -> str:
        x, y = self.tile_xy
        if isinstance(self, InletPump):
            if self.direction == 'left': 
                bottomleft_tile = pg.Vector2(self.rect.bottomleft) // TILE_SIZE
                x, y = bottomleft_tile
                liquid_tile_id = self.tile_map[int(x) - 1, int(y) + 1]
            else:
                bottomright_tile = pg.Vector2(self.rect.bottomright) // TILE_SIZE
                x, y = bottomright_tile
                liquid_tile_id = self.tile_map[int(x) + 1, int(y) + 1]
        else: # bc the outlet pumps are extracting a liquid, the direction variables work opposite of the inlet pump
            if self.direction == 'left':
                bottomright_tile = pg.Vector2(self.rect.bottomright) // TILE_SIZE
                x, y = bottomright_tile
                liquid_tile_id = self.tile_map[int(x) + 1, int(y) + 1]
            else:
                bottomleft_tile = pg.Vector2(self.rect.bottomleft) // TILE_SIZE
                x, y = bottomleft_tile
                liquid_tile_id = self.tile_map[int(x) - 1, int(y) + 1]

        name = self.game_obj.proc_gen.ids_to_names[liquid_tile_id]
        print(name)
        self.ui.liquid_icon = self.graphics['icons'][name]
        return name

    def extract_liquid(self) -> None:
        pass

    def update_alarms(self):
        for alarm in [a for a in self.alarms.values() if not a.running]:
            if alarm == self.alarms['extract liquid']:
                alarm.length = self.extract_speed[self.liquid]
            else:
                if fuel_item := self.inv.input_slots['fuel'].item:
                    alarm.length = self.fuel_burn_speed[fuel_item] 
            
            alarm.start()

        super().update_alarms()

    def update(self, dt: float=None) -> None:
            if self.active:
                self.update_alarms()

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