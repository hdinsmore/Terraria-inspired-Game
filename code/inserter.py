from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from input_manager import InputManager
    from player import Player

import pygame as pg
import math

from settings import TILE_SIZE, MAP_SIZE, INSERTER_TRANSPORT_DIRS
from transport_sprite_base import TransportSprite
from pipe import Pipe
from furnaces import Furnace
from alarm import Alarm

class Inserter(TransportSprite):
    def __init__(
        self, 
        xy: tuple[int, int], 
        image: pg.Surface, 
        z: dict[str, int], 
        sprite_groups: list[pg.sprite.Group], 
        screen: pg.Surface, 
        cam_offset: pg.Vector2, 
        input_manager: InputManager,
        player: Player, 
        assets: dict[str, dict[str, any]], 
        tile_map: np.ndarray, 
        obj_map: np.ndarray, 
        speed_factor: int=1
    ):
        super().__init__(xy, image, z, sprite_groups, screen, cam_offset, input_manager, player, assets, tile_map, obj_map)
        self.speed_factor = speed_factor

        self.tile_borders = {
            'x axis': [(self.tile_xy[0] + dx, self.tile_xy[1]) for dx in (-1, 1) if 0 <= self.tile_xy[0] + dx < MAP_SIZE[0]],
            'y axis': [(self.tile_xy[0], self.tile_xy[1] + dy) for dy in (-1, 1) if 0 <= self.tile_xy[1] + dy < MAP_SIZE[1]],
        }
        self.receive_dir, self.send_dir = None, None
        self.obj_receive_from, self.obj_send_to = None, None
        self.rotated_over = False
        self.adj_sprites = {dxy: None for dxy in self.tile_borders}
        self.transport_idx = 0
        self.item_holding = None
        self.rotate_speed = 1250
        self.rotate_dir = None
        self.original_img = self.image
        self.alarms = {
            'transfer': Alarm(length=self.rotate_speed / self.speed_factor, fn=self.transfer, auto=True, loop=True),
            'receive item': Alarm(length=200, fn=self.receive_item, auto=False, loop=False),
            'send item': Alarm(length=100, function=self.send_item, auto=False, loop=False),
        }
        
    def config_transport_dir(self) -> None:
        if self.keyboard.pressed_keys[pg.K_LSHIFT] and self.rect.collidepoint(self.mouse.world_xy):
            self.transport_idx = (self.transport_idx + 1) % len(INSERTER_TRANSPORT_DIRS)
            self.receive_dir, self.send_dir = INSERTER_TRANSPORT_DIRS[self.transport_idx]
   
    def transfer(self) -> None: # TODO: will have to make this more modular depending on whether the receiving object is a furnace/inserter/lab/etc.
        x, y = self.tile_xy
        if self.receive_dir and self.send_dir and all(self.obj_map[x + dx, y + dy] is not None for dx, dy in (self.receive_dir, self.send_dir)):
            if not self.item_holding:
                self.obj_receive_from = self.obj_map[x + self.receive_dir[0], y + self.receive_dir[1]] 
                if not self.rotated_over:
                    self.rotate(self.obj_receive_from)
                self.alarms['receive item'].start()
            else:
                self.obj_send_to = self.obj_map[x + self.send_dir[0], y + self.send_dir[1]]
                if not self.rotated_over:
                    self.rotate(self.obj_send_to)
                self.alarms['send item'].start()

    def receive_item(self) -> None:
        if not isinstance(self.obj_receive_from, Pipe):
            if hasattr(self.obj_receive_from, 'output') and self.obj_receive_from.output['item']:
                self.item_holding = self.obj_receive_from.output['item']
                self.obj_receive_from.output['amount'] -= 1
                if not self.obj_receive_from.output['amount']:
                    self.obj_receive_from.output['item'] = None
                self.rotate(self.obj_receive_from, reset=True)
        else:
            if self.obj_receive_from.item_holding:
                self.item_holding = self.obj_receive_from.item_holding
                self.obj_receive_from.item_holding = None
                self.rotate(self.obj_receive_from, reset=True)

    def send_item(self) -> None:
        if not isinstance(self.obj_send_to, Pipe):
            if self.obj_send_to.fuel_input['item'] in {None, self.item_holding}:
                if self.obj_send_to.fuel_input['item'] is None:
                    self.obj_send_to.fuel_input['item'] = self.item_holding
                self.obj_send_to.fuel_input['amount'] += 1
                self.item_holding = None  
                self.rotate(self.obj_send_to, reset=True)
        else:
            if not self.obj_send_to.item_holding:
                self.obj_send_to.item_holding = self.item_holding
                self.item_holding = None
                self.rotate(self.obj_send_to, reset=True)
                    
    def rotate(self, target_obj: pg.sprite.Sprite, reset: bool=False) -> None:
        if not reset:
            dxy = pg.Vector2(self.rect.center) - pg.Vector2(target_obj.rect.center)
            angle = -math.degrees(math.atan2(dxy.y, dxy.x)) + 135 # negative since rotozoom rotates counterclockwise
            self.image = pg.transform.rotozoom(self.original_img, angle, 1) 
            center = self.rect.center # preserve the original center
            self.rect = self.image.get_rect(center=center)
        else:
            center = self.rect.center
            self.image = self.original_img
            self.rect = self.image.get_rect(center=center)
        self.rotated_over = not self.rotated_over

    def render_transport_ui(self) -> None:
        if self.receive_dir and self.send_dir:
            dirs = self.xy_to_cardinal[self.transport_idx]
            receive_dir_surf = self.dir_ui[dirs[self.receive_dir]]
            self.screen.blit(receive_dir_surf, receive_dir_surf.get_frect(midbottom=self.rect.midtop - self.cam_offset))
            send_dir_surf = self.dir_ui[dirs[self.send_dir]]
            self.screen.blit(send_dir_surf, send_dir_surf.get_frect(midtop=self.rect.midbottom - self.cam_offset))
        if self.item_holding:
            item_surf = self.graphics[self.item_holding]
            self.screen.blit(item_surf, item_surf.get_rect(center=self.rect.midtop - self.cam_offset))

    def update(self, dt: float) -> None:
        self.update_alarms()
        self.render_transport_ui()
        self.config_transport_dir()


class BurnerInserter(Inserter):
    def __init__(
        self, 
        xy: tuple[int, int], 
        image: dict[str, dict[str, pg.Surface]], 
        z: dict[str, int], 
        sprite_groups: list[pg.sprite.Group], 
        screen: pg.Surface, 
        cam_offset: pg.Vector2,
        input_manager: InputManager,
        player: Player, 
        assets: dict[str, dict[str, any]], 
        tile_map: np.ndarray, 
        obj_map: np.ndarray
    ):
        super().__init__(xy, image, z, sprite_groups, screen, cam_offset, input_manager, player, assets, tile_map, obj_map)
        self.tile_reach_radius = 1
        self.fuel_sources = {'coal': {'capacity': 50, 'burn speed': 6000}}


class ElectricInserter(Inserter):
    def __init__(
        self, 
        xy: tuple[int, int], 
        image: dict[str, dict[str, pg.Surface]], 
        z: dict[str, int], 
        sprite_groups: list[pg.sprite.Group], 
        screen: pg.Surface,
        cam_offset: pg.Vector2, 
        input_manager: InputManager,
        player: Player, 
        assets: dict[str, dict[str, any]], 
        tile_map: np.ndarray, 
        obj_map: np.ndarray
    ):
        speed_factor = 1.5
        super().__init__(xy, image, z, sprite_groups, screen, cam_offset, input_manager, player, assets, tile_map, obj_map, speed_factor)
        self.tile_reach_radius = 1
        self.fuel_sources = {'electricity': {}}


class LongHandedInserter(Inserter):
    def __init__(
        self, 
        xy: tuple[int, int], 
        image: dict[str, dict[str, pg.Surface]], 
        z: dict[str, int], 
        sprite_groups: list[pg.sprite.Group], 
        screen: pg.Surface,
        cam_offset: pg.Vector2, 
        input_manager: InputManager,
        player: Player, 
        assets: dict[str, dict[str, any]], 
        tile_map: np.ndarray, 
        obj_map: np.ndarray
    ):
        speed_factor = 1.25
        super().__init__(xy, image, z, sprite_groups, screen, cam_offset, mouse, keyboard, player, assets, tile_map, obj_map, speed_factor)
        self.tile_reach_radius = 2
        self.fuel_sources = {'electricity': {}}