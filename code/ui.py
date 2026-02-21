from __future__ import annotations
from typing import Sequence
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from input_manager import InputManager
    from sprite_manager import SpriteManager
    from player import Player
    from procgen import ProcGen

import pygame as pg
from collections import defaultdict

from settings import TILE_SIZE, RES
from mini_map import MiniMap
from craft_window import CraftWindow
from inventory_ui import InventoryUI
from alarm import Alarm

class UI:
    def __init__(self, game_obj: Main):
        self.game_obj = game_obj

        self.screen: pg.Surface = game_obj.screen
        self.cam_offset: pg.Vector2 = game_obj.cam.offset
        assets = game_obj.asset_manager.assets
        self.assets, self.fonts, self.colors = assets, assets['fonts'], assets['colors']

        input_manager = game_obj.input_manager
        self.keyboard, self.mouse = input_manager.keyboard, input_manager.mouse

        self.player = game_obj.player
        self.inventory = self.player.inventory

        self.save_data = game_obj.save_data['ui'] if game_obj.save_data is not None else None

        self.mini_map = MiniMap(game_obj, self)
        self.mouse_grid = MouseGrid(self)
        self.inventory_ui = InventoryUI(self, input_manager, game_obj.sprite_manager)

        self.craft_window = CraftWindow(self, game_obj.sprite_manager.crafting.craft_item)

        self.HUD = HUD(self.screen, self.assets, self.craft_window.outline_rect.right, self.gen_outline, self.gen_bg)

        for key in ('expand inventory ui', 'toggle inventory ui', 'toggle craft window ui', 'toggle mini map ui', 'toggle HUD ui'):
            setattr(self, '_'.join(key.split(' ')), self.keyboard.key_bindings[key])
            
        self.active_item_names = []
    
    def get_craft_window_height(self) -> int:
        inv_grid_height = self.inventory_ui.slot_len * (self.inventory.num_slots // self.inventory_ui.num_cols)
        return inv_grid_height + self.mini_map.outline_h + self.mini_map.padding

    def gen_outline(
        self, 
        rect: pg.Rect, 
        color: str | tuple[int, int, int]='cyan', 
        width: int=1, 
        padding: int=1, 
        radius: int=0, 
        draw: bool=True, 
        return_outline: bool=False
    ) -> None | pg.Rect:
        outline = pg.Rect(
            rect.topleft - pg.Vector2(padding, padding), 
            (rect.width + (padding * 2), rect.height + (padding * 2))
        )
        if draw:
            pg.draw.rect(self.screen, color, outline, width, radius)
        if return_outline: # use the outline as the base rect for creating another outline
            return outline

    def gen_bg(
        self, 
        rect: pg.Rect, 
        color: str | tuple[int, int, int]='black', 
        alpha: int=200
        ) -> None:
        img = pg.Surface(rect.size)
        img.fill(color)
        img.set_alpha(alpha)
        self.screen.blit(img, rect)

    def render_inv_item_name(self, rect: pg.Rect, name: str) -> None:
        if rect.collidepoint(pg.mouse.get_pos()):
            font = self.assets['fonts']['item label'].render(name, True, self.assets['colors']['text'])
            self.screen.blit(font, font.get_rect(topleft = rect.bottomleft))

    def render_new_item_name(self, item_name: str, item_rect: pg.Rect, amount: int) -> None:
        color = self.assets['colors']['text']
        item_total = self.inventory.contents[item_name]['amount']
        world_coords = pg.Vector2(item_rect.midtop)
        self.active_item_names.append(
            ItemName(
                item_name, 
                color, 
                255, 
                self.assets['fonts']['item label'].render(f'+{amount} {item_name} ({item_total})', True, color),
                self.screen, 
                self.cam_offset, 
                world_coords, 
                Alarm(2000)
            )
        )

    def update_item_name_data(self) -> None:
        for index, cls in enumerate(self.active_item_names):
            cls.update(index)
        self.active_item_names = [cls for cls in self.active_item_names if cls.alarm.running]

    def get_scaled_image(self, image: pg.Surface, item_name: str, width: int, height: int, padding: int=0) -> pg.Surface:
        bounding_box = (width - (padding * 2), height - (padding * 2))
        aspect_ratio = min(image.width / bounding_box[0], image.height / bounding_box[1]) # avoid stretching an image too wide/tall
        scale = (min(bounding_box[0], image.width * aspect_ratio), min(bounding_box[1], image.height * aspect_ratio))
        return pg.transform.scale(self.assets['graphics'][item_name], scale)

    def get_grid_xy(self) -> pg.Vector2:
        return ((pg.Vector2(self.mouse.xy_world) // TILE_SIZE) * TILE_SIZE) - self.cam_offset
    
    def update_render_states(self) -> None:
        pressed_keys = self.keyboard.pressed_keys
        if pressed_keys[self.expand_inventory_ui]:
            self.inventory_ui.expand = not self.inventory_ui.expand
            self.inventory_ui.update_dimensions()

        elif pressed_keys[self.toggle_inventory_ui]:
            self.inventory_ui.render = not self.inventory_ui.render 

        elif pressed_keys[self.toggle_craft_window_ui]:
            self.craft_window.opened = self.inventory_ui.expand = not self.craft_window.opened
            self.inventory_ui.update_dimensions()
            self.HUD.shift_right = not self.HUD.shift_right

        elif pressed_keys[self.toggle_mini_map_ui]:
            self.mini_map.render = not self.mini_map.render

        elif pressed_keys[self.toggle_HUD_ui]:
            self.HUD.render = not self.HUD.render

    def render_item_amount(self, amount: int, coords: tuple[int, int], add_x_offset: bool=True) -> None:
        image = self.assets['fonts']['number'].render(str(amount), False, self.assets['colors']['text'])
        x_offset = 0
        if add_x_offset: # making it optional in case the amount will never reach a lengthy value
            num_digits = len(str(amount))
            x_offset = 5 * (num_digits - 2) if num_digits > 2 else 0 # move 3+ digit values to the left by 5px for every remaining digit 
        rect = image.get_rect(center = (coords[0] + x_offset, coords[1] - 2))
        self.gen_bg(rect)
        self.screen.blit(image, rect)

    def update(self) -> None:
        self.update_render_states()
        self.mouse_grid.update()
        self.HUD.update()
        self.mini_map.update()
        self.craft_window.update() # keep above the inventory ui otherwise item names may be rendered behind the window
        self.inventory_ui.update()
        self.update_item_name_data()
        

class MouseGrid:
    def __init__(self, ui: UI):
        self.mouse = ui.mouse
        self.screen = ui.screen
        self.cam_offset = ui.cam_offset
        self.get_grid_xy = ui.get_grid_xy

        self.tile_w = self.tile_h = 3

    def render_grid(self) -> None:
        if self.mouse.moving or self.mouse.buttons_pressed['left']:
            topleft = self.get_grid_xy()
            for x in range(self.tile_w):
                for y in range(self.tile_h):
                    cell_surf = pg.Surface((TILE_SIZE, TILE_SIZE), pg.SRCALPHA)
                    cell_surf.fill((0, 0, 0, 0))
                    pg.draw.rect(cell_surf, (255, 255, 255, 10), (0, 0, TILE_SIZE, TILE_SIZE), 1) # (0, 0) is relative to the topleft of cell_surf 
                    self.screen.blit(cell_surf, cell_surf.get_rect(topleft=topleft + pg.Vector2(x * TILE_SIZE, y * TILE_SIZE)))

    def update(self) -> None:
        self.render_grid()


class HUD:
    def __init__(self, screen: pg.Surface, assets: dict[str, dict[str, any]], craft_window_right: int, gen_outline: callable, gen_bg: callable):
        self.screen = screen
        self.assets = assets
        self.craft_window_right = craft_window_right
        self.gen_outline = gen_outline
        self.gen_bg = gen_bg

        self.colors = self.assets['colors']
        self.fonts = self.assets['fonts']

        self.height = TILE_SIZE * 3
        self.width = RES[0] // 2
        self.shift_right = False
        self.render = True

    def render_bg(self) -> None:
        self.image = pg.Surface((self.width, self.height))
        self.rect = self.image.get_rect(topleft = (self.get_left_point(), 0))
        self.gen_bg(self.rect)
        
        outline1 = self.gen_outline(self.rect, draw = False, return_outline = True)
        outline2 = self.gen_outline(outline1, draw = True)
        pg.draw.rect(self.screen, 'black', outline1, 1)

    def get_left_point(self) -> int:
        default = (RES[0] // 2) - (self.width // 2)
        if not self.shift_right:
            return default
        else:
            # center between the craft window's right border and the screen's right border
            padding = (RES[0] - self.craft_window_right) - self.width
            return self.craft_window_right + (padding // 2)
        
    def update(self) -> None:
        if self.render:
            self.render_bg()


class ItemName:
    def __init__(self, 
        name: str, 
        color: str, 
        alpha: int, 
        font: pg.Font, 
        screen: pg.Surface, 
        cam_offset: pg.Vector2, 
        world_coords: tuple[int, int], 
        alarm: Alarm
    ):
        self.name = name
        self.color = color
        self.alpha = alpha
        self.font = font
        self.screen = screen
        self.cam_offset = cam_offset
        self.world_coords = world_coords
        self.alarm = alarm

    def update(self, index: int) -> None:
        if not self.alarm.running:
            self.alarm.start()
            return
        self.alarm.update()    
        
        self.alpha = max(0, self.alpha - 2)
        self.font.set_alpha(self.alpha)
        screen_coords = self.world_coords - self.cam_offset
        self.screen.blit(self.font, self.font.get_rect(midbottom = screen_coords))
        self.world_coords[1] -= index + 1 # move north across the screen