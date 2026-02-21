from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from graphics_engine import Camera

import pygame as pg

from settings import TILE_SIZE

class InputManager:
    def __init__(self, cam: Camera):
        self.mouse = Mouse(cam)
        self.keyboard = Keyboard()

    def update(self, cam_offset: pg.Vector2) -> None:
        self.mouse.update(cam_offset)
        self.keyboard.update()
        

class Keyboard:
    def __init__(self):
        self.held_keys = None
        self.pressed_keys = None
        self.num_keys = {pg.K_0 + num for num in range(10)}
        self.key_map = {key: (key - pg.K_0 - 1) % 10 for key in self.num_keys} # maps the ascii value to the number pressed
        self.key_bindings = {
            'move left': pg.K_a,
            'move right': pg.K_d,
            'jump': pg.K_SPACE,
            'mine': pg.K_s,
            'expand inventory ui': pg.K_i,
            'toggle inventory ui': pg.K_j,
            'toggle craft window ui': pg.K_c,
            'toggle mini map ui': pg.K_m,
            'toggle HUD ui': pg.K_RSHIFT, # don't use h, reserved for rotating a pipe's transport direction horizontally
            'close ui window': pg.K_u,
            'stop holding item': pg.K_q,
            'drop item': pg.K_z,
            'rotate item': pg.K_r
        }

    def update(self) -> None:
        self.held_keys = pg.key.get_pressed()
        self.pressed_keys = pg.key.get_just_pressed()


class Mouse:
    def __init__(self, cam: Camera):
        self.cam = cam

        self.buttons_pressed, self.buttons_held = {'left': False, 'right': False}, {'left': False, 'right': False}
        self.moving = False
        self.xy_screen: pg.Vector2 = None
        self.xy_world: tuple[int, int] = None
        self.xy_world_tile: tuple[int, int] = None
    
    def update_movement(self, cam_offset: pg.Vector2) -> None:
        self.moving = pg.mouse.get_rel()
        if self.moving:
            self.xy_screen = pg.mouse.get_pos()
            self.xy_world = (int(self.xy_screen[0] + cam_offset.x), int(self.xy_screen[1] + cam_offset.y))
            self.xy_world_tile = (self.xy_world[0] // TILE_SIZE, self.xy_world[1] // TILE_SIZE)
    
    def update_click_states(self) -> None:
        self.buttons_held['left'] = self.buttons_held['right'] = self.buttons_pressed['left'] = self.buttons_pressed['right'] = False

        clicked = pg.mouse.get_just_pressed()
        if clicked[0]:
            self.buttons_pressed['left'] = True
        elif clicked[2]:
            self.buttons_pressed['right'] = True

        held = pg.mouse.get_pressed()
        if held[0]:
            self.buttons_held['left'] = True
        elif held[1]:
            self.buttons_held['right'] = True

        
    def update(self, cam_offset: pg.Vector2) -> None:
        self.update_movement(cam_offset)
        self.update_click_states()