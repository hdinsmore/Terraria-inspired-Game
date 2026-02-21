from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main

import pygame as pg
import numpy as np

from settings import MAP_SIZE, TILE_SIZE, PIPE_TRANSPORT_DIRS, Z_LAYERS
from transport_sprite_base import TransportSprite
from alarm import Alarm

class Pipe(TransportSprite):
    def __init__(
        self, 
        save_data: [str, any],
        xy: tuple[int, int], 
        image: dict[str, dict[str, pg.Surface]],
        sprite_groups: list[pg.sprite.Group],
        game_obj: Main,
        variant_idx: int
    ):
        super().__init__(xy, image, Z_LAYERS['main'], sprite_groups, game_obj, save_data)
        self.names_to_ids: dict[str, int] = game_obj.names_to_ids
        self.variant_idx = variant_idx
        
        self.speed_factor = 1
        self.alarms = {'move item': Alarm(2000 / self.speed_factor, self.transport, True, True)}
        self.transport_dir = None
        self.get_connected_objs()

    def get_connected_objs(self) -> None:
        pipe_data = PIPE_TRANSPORT_DIRS[self.variant_idx]
        self.obj_connections = {xy: None for xy in (pipe_data if self.variant_idx <= 5 else [xy for dirs in pipe_data.values() for xy in dirs])}
        x, y = self.tile_xy
        for dx, dy in self.obj_connections if self.variant_idx <= 5 else [xy for dirs in pipe_data.values() for xy in dirs]:
            if (0 < x + dx < MAP_SIZE[0] and 0 < y + dy < MAP_SIZE[1]) and (obj := self.obj_map[x + dx, y + dy]):
                if isinstance(obj, Pipe):
                    if (dx * -1, dy * -1) in obj.obj_connections: # ensure the pipes are connected and not just adjacent
                        self.obj_connections[dx, dy] = obj
                else:
                    self.obj_connections[dx, dy] = obj # machines don't have a 'facing direction' so no need to check if they're only just adjacent
        
        self.transport_dir = list(self.obj_connections.keys())[0] if self.variant_idx <= 5 else {
            'horizontal': pipe_data['horizontal'][0], 'vertical': pipe_data['vertical'][0] # default to the 1st index
        } 

    def update_rotation(self) -> None:
        if self.keyboard.pressed_keys[pg.K_r] and self.rect.collidepoint(self.mouse.world_xy) and not self.player.item_holding:
            self.variant_idx = (self.variant_idx + 1) % len(PIPE_TRANSPORT_DIRS)
            self.image = self.graphics[f'pipe {self.variant_idx}']
            self.tile_map[self.tile_xy] = self.tile_IDs[f'pipe {self.variant_idx}']
            self.get_connected_objs()

    def transport(self) -> None:
        for dxy in [xy for xy in self.obj_connections if self.obj_connections[xy] is not None]:
            transport_dir = self.transport_dir if self.variant_idx <= 5 else self.transport_dir['horizontal' if dxy[0] != 0 else 'vertical']
            if obj := self.obj_connections[dxy]:                         
                if self.item_holding:
                    if dxy == transport_dir: 
                        if isinstance(obj, Pipe):
                            if not obj.item_holding:
                                obj.item_holding = self.item_holding
                                self.item_holding = None
                        else:
                            self.send_item_to_inserter(obj)
                else:
                    if isinstance(obj, Pipe): # don't add the bottom conditions to this line, it needs to be alone for the else condition to run without error
                        obj_dir = obj.transport_dir if obj.variant_idx <= 5 else obj.transport_dir['horizontal' if dxy[0] != 0 else 'vertical']
                        if obj.item_holding and dxy == (obj_dir[0] * -1, obj_dir[1] * -1) and \
                        (self.tile_xy[0] + transport_dir[0], self.tile_xy[1] + transport_dir[1]) != obj.tile_xy:
                            self.item_holding = obj.item_holding
                            obj.item_holding = None

    def send_item_to_inserter(self, obj: Inserter) -> None:
        if not obj.item_holding and obj.rotated_over:
            obj.item_holding = self.item_holding
            self.item_holding = None
        
    def config_transport_dir(self) -> None:
        if self.variant_idx <= 5:
            if self.keyboard.pressed_keys[pg.K_LSHIFT] and self.rect.collidepoint(self.mouse.world_xy):
                dirs = list(self.connections.keys())
                self.transport_dir = dirs[1] if self.transport_dir == dirs[0] else dirs[0]
        else:
            if (self.keyboard.pressed_keys[pg.K_LSHIFT] or self.keyboard.pressed_keys[pg.K_RSHIFT]) and self.rect.collidepoint(self.mouse.world_xy):
                axis = 'horizontal' if self.keyboard.pressed_keys[pg.K_LSHIFT] else 'vertical'
                dx, dy = self.transport_dir[axis]
                self.transport_dir[axis] = (dx * -1, dy * -1)

    def render_transport_ui(self) -> None:
        if self.variant_idx <= 5:
            dir_surf = self.dir_ui[self.xy_to_cardinal[self.variant_idx][self.transport_dir]]
            self.screen.blit(dir_surf, dir_surf.get_frect(center=self.rect.center - self.cam_offset))
        else:
            for axis in ('horizontal', 'vertical'):
                dir_surf = self.dir_ui[self.xy_to_cardinal[self.variant_idx][self.transport_dir[axis]]]
                self.screen.blit(dir_surf, dir_surf.get_rect(center=self.rect.center - self.cam_offset))

        if self.item_holding:
            item_surf = self.graphics[self.item_holding]
            self.screen.blit(item_surf, item_surf.get_rect(center=self.rect.center - self.cam_offset))

    def extract_item(self) -> None:
        if self.mouse.buttons_pressed['left'] and self.mouse.tile_xy == self.tile_xy and \
        (not self.player.item_holding or self.player.item_holding == self.item_holding):
            self.player.inventory.add_item(self.item_holding)
            self.player.item_holding = self.item_holding
            self.item_holding = None

    def update(self, dt: float) -> None:
        self.update_alarms()
        self.render_transport_ui()
        self.update_rotation()
        self.config_transport_dir()
        self.extract_item()