from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main, Keyboard, Mouse
    from player import Player
    import numpy as np
    from ui import UI
    from machine_ui import MachineUI

import pygame as pg
from dataclasses import dataclass, field
from abc import ABC

from settings import Z_LAYERS, TILE_SIZE, TILE_SIZE
from sprite_base_classes import Sprite

@dataclass(slots=True)
class InvSlot:
    item: str=None
    rect: pg.Rect=None
    valid_inputs: set=None
    amount: int=0
    max_capacity: int=99

@dataclass
class Inv:
    input_slots: dict[str, InvSlot]=None
    output_slot: InvSlot=field(default_factory=InvSlot)

    def __iter__(self):
        if self.input_slots:
            for slot in self.input_slots.values():
                yield slot
                
        yield self.output_slot


class Machine(Sprite, ABC):
    def __init__(
        self, 
        save_data: dict[str, any],
        xy: tuple[int, int], 
        image: pg.Surface, 
        sprite_groups: list[pg.sprite.Group], 
        game_obj: Main,
        ui: UI | None=None
    ):
        super().__init__(xy=xy, image=image, sprite_groups=sprite_groups, z=Z_LAYERS['main'])
        self.tile_xy = (xy[0] // TILE_SIZE, xy[1] // TILE_SIZE)
        print(xy, self.tile_xy)

        self.game_obj = game_obj

        self.screen: pg.Surface = game_obj.screen
        self.cam_offset: pg.Vector2 = game_obj.cam.offset

        self.keyboard: Keyboard = game_obj.input_manager.keyboard
        self.mouse: Mouse = game_obj.input_manager.mouse

        self.player: Player = game_obj.player

        self.assets: dict[str, dict[str, pg.Surface]] = game_obj.asset_manager.assets
        self.graphics: dict[str, pg.Surface] = self.assets['graphics']

        self.tile_map: np.ndarray = game_obj.proc_gen.tile_map
        self.obj_map: np.ndarray = game_obj.item_placement.obj_map

        if ui is not None:
            self.rect_in_sprite_radius: callable = game_obj.sprite_manager.rect_in_sprite_radius
            self.gen_outline: callable = ui.gen_outline
            self.gen_bg: callable = ui.gen_bg
            self.render_item_amount: callable = ui.render_item_amount

            self.fuel_input = save_data['fuel input'] if save_data else {'item': None, 'amount': 0}
            self.output = save_data['output'] if save_data else {'item': None, 'amount': 0}

            self.pipe_connections = {}
            
        self.active: bool = False if not save_data else save_data['active']

    def init_ui(self, ui_cls: MachineUI) -> None:
        self.ui = ui_cls(machine=self) # not initializing self.ui until the machine variant (burner/electric) is determined

    def update_alarms(self) -> None:
        for alarm in self.alarms.values():
            alarm.update()