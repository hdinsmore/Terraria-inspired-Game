from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sprite_manager import SpriteManager
    from ui import UI

import pygame as pg
import numpy as np
from collections import Counter
from random import choice
from abc import ABC

from alarm import Alarm
from drill_ui import DrillUI
from machine_sprite_base import Machine, Inv, InvSlot
from settings import TILE_SIZE, TILE_ORE_RATIO, MAP_SIZE, RES, Z_LAYERS

class Drill(Machine, ABC):
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
        self.names_to_ids: dict[str, int] = game_obj.proc_gen.names_to_ids
        self.ids_to_names: dict[int, str] = game_obj.proc_gen.ids_to_names

        self.inv = Inv(input_slots=None) # only burners have an input slot (for fuel)

        min_x = self.rect.left // TILE_SIZE
        max_x = self.rect.right // TILE_SIZE
        min_y = self.rect.bottom // TILE_SIZE
        max_y = min_y + min(MAP_SIZE[1] - min_y, RES[1] // 4)
        self.span_x = max_x - min_x
        self.span_y = max_y - min_y
        self.map_slice = save_data['map slice'] if save_data else self.tile_map[min_x:max_x, min_y:max_y]

        self.ignore_ids = {self.names_to_ids[name] for name in ('air', 'dirt', 'item extended')} # keep above self.ore_data, get_ore_data() references it
        self.ore_data = save_data['ore data'] if save_data else self.get_ore_data()
        self.target_ore = save_data['target ore'] if save_data else None
        self.num_ore_available = save_data['num ore available'] if save_data else 0
        self.ore_col = save_data['ore col'] if save_data else 0
        self.ore_row = save_data['ore row'] if save_data else 0
        self.extract_time_factor = 1.05 # extraction times increase as the drill moves deeper into the ground

        self.alarms = {
            'extract': Alarm(
                2000 * self.speed_factor * self.extract_time_factor * (self.ore_row + 1), 
                self.extract, 
                loop=True, 
                track_percent=True
            )
        }

    def get_ore_data(self) -> dict[str, int]:
        ore_data = {
            self.ids_to_names[i]: {'amount': amt * TILE_ORE_RATIO} 
            for i, amt in zip(*np.unique(self.map_slice, return_counts=True)) if i not in self.ignore_ids
        }
        for k in ore_data:
            ore_data[k]['locations'] = np.argwhere(self.map_slice == self.names_to_ids[k])
        return ore_data

    def extract(self) -> None:
        self.num_ore_available -= 1
        if not self.num_ore_available:
            self.convert_tile(self.ore_xy)

        self.inv.output_slot.amount += 1
        if not self.inv.output_slot.item:
            self.inv.output_slot.item = self.target_ore
            
        if self.ore_col % self.span_x == 0:
            self.ore_row += 1
            self.alarms['extract'].length *= self.extract_time_factor

    def convert_tile(self, tile_xy: tuple[int, int]) -> None: 
        if dirs := self.get_neighbor_dirs(tile_xy):
            neighbor_id_counter = Counter(self.tile_map[tile_xy + xy] for xy in dirs)
        else:
            self.tile_map[tile_xy] = self.names_to_ids['air']
            return
        (ids, freqs) = zip(*neighbor_id_counter.most_common())
        f0, f1, f2, f3 = (list(freqs) + [0, 0, 0])[:4] # adding zeros to follow in case the original list has less than 4 elements
        if f0 > f1:
            self.tile_map[tile_xy] = ids[0]
        elif f0 == f1 and f1 != f2: # f0 & f1 have the majority
            self.tile_map[tile_xy] = choice(ids[:2])
        else: # all indices store different tiles
            self.tile_map[tile_xy] = choice(ids)

    def get_neighbor_dirs(self, tile_xy: tuple[int, int]) -> list[tuple[int, int]]:
        dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        if not self.ore_row > 1:
            dirs.remove((0, -1))
            
        if tile_xy[0] == 0:
            dirs.remove((-1, 0))

        if tile_xy[0] == MAP_SIZE[0] - 1:
            dirs.remove((1, 0))

        if tile_xy[1] == MAP_SIZE[1] - 1:
            dirs.remove((0, 1))
        return dirs

    def get_active_state(self) -> bool:
        conditions = self.inv.input_slots['fuel'].item and self.inv.output_slot.amount < self.max_capacity['output'] # TODO: the fuel condition will have to be updated for the electric drill
        if not self.active:
            if conditions:
                self.active = True
        elif not conditions:
            self.active = False
            self.alarms.clear()
        return self.active
    
    def update(self, dt: float) -> None:
        if self.target_ore and self.get_active_state():
            if self.alarms['extract'].running: 
                self.alarms['extract'].update()
            else:
                self.alarms['extract'].start()
            if self.variant == 'burner':
                if self.alarms['burn fuel'].running:
                    self.alarms['burn fuel'].update()
                else:
                    self.alarms['burn fuel'].start()

        self.game_obj.sprite_manager.check_dir_flip(self)           
        self.ui.update()
        
    def get_save_data(self) -> dict[str, list|dict]:
        return {
            'xy': list(self.rect.topleft), 
            'map slice': self.map_slice.tolist(), 
            'ore data': self.ore_data, 
            'target ore': self.target_ore, 
            'num ore available': self.num_ore_available, 
            'ore col': self.ore_col, 
            'ore row': self.ore_row, 
            'output': self.output
        }


class BurnerDrill(Drill):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: pg.Vector2, 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
    ):  
        self.speed_factor = 1
        super().__init__(save_data=save_data, xy=xy, image=image, sprite_groups=sprite_groups, game_obj=game_obj, ui=ui)
        self.variant = 'burner'
        self.fuel_sources = {
            'wood': {'capacity': 99, 'burn speed': 3000}, 
            'coal': {'capacity': 99, 'burn speed': 6000}
        }
        self.max_capacity = {'fuel': 50, 'output': 99}
        self.inv.input_slots = {'fuel': InvSlot(valid_inputs=self.fuel_sources.keys(), max_capacity=self.max_capacity['fuel'])}
        self.alarms['burn fuel'] = Alarm(
            2000 * self.speed_factor * self.extract_time_factor * (self.ore_row + 1), 
            self.burn_fuel, 
            loop=True, 
            track_percent=True
        )
        self.init_ui(DrillUI)

    def burn_fuel(self) -> None:
        self.inv.input_slots['fuel'].amount -= 1
        if not self.inv.input_slots['fuel'].amount:
            self.self.inv.input_slots['fuel'].item = None


class ElectricDrill(Drill):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: pg.Vector2, 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI,
    ):  
        self.speed_factor = 1.5
        super().__init__(save_data=save_data, xy=xy, image=image, sprite_groups=sprite_groups, game_obj=game_obj, ui=ui)
        self.variant = 'electric'
        self.fuel_sources = {'electric poles'}
        self.init_ui(DrillUI)  