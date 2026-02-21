from __future__ import annotations
from typing import Sequence
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main
    from ui import UI
    from procgen import ProcGen
    from sprite_manager import SpriteManager
    from chunk_manager import ChunkManager
    from input_manager import Mouse
    from player import Player
    import numpy as np
    
import pygame as pg
from os import walk
from os.path import join
from math import ceil, floor, sin
from random import randint

from settings import *
from weather import Weather

class GraphicsEngine:
    def __init__(self, game_obj: Main):
        self.screen: pg.Surface = game_obj.screen
        self.cam: Camera = game_obj.cam
        self.graphics: dict[str, pg.Surface] = game_obj.asset_manager.assets['graphics']
        self.ui: UI = game_obj.ui
        self.chunk_manager: ChunkManager = game_obj.chunk_manager

        self.sprite_manager: SpriteManager = game_obj.sprite_manager 

        self.key_map: dict[int, int] = game_obj.input_manager.keyboard.key_map 

        self.player: Player = game_obj.player

        proc_gen: ProcGen = game_obj.proc_gen
        self.tile_map: np.ndarray = proc_gen.tile_map
        self.names_to_ids: dict[str, int] = proc_gen.names_to_ids
        self.ids_to_names: dict[int, str] = proc_gen.ids_to_names
        self.current_biome: str = proc_gen.current_biome
        self.biome_order: dict[str, int] = proc_gen.biome_order
         
        self.terrain_graphics = TerrainGraphics(game_obj)

        self.tool_animation = ToolAnimation(self.screen, self.render_item_held)

        self.weather = Weather(self.screen, game_obj.save_data['weather'] if game_obj.save_data else None)

        # only render an equipped item while the sprite is in a given state
        self.item_render_states = {
            'pickaxe': {'mining', 'fighting'},
            'axe': {'chopping', 'fighting'}
        }
        # self.sprite_manager.<sprite group> -> self.<sprite_group>
        for name, group in self.sprite_manager.all_groups.items():
            setattr(self, name, group)

    def animate_sprite(self, spr: pg.sprite.Sprite, dt: float) -> None:
        if spr.state not in {'idle', 'mining', 'chopping'}:
            spr.frame_index += spr.animation_speed[spr.state] * dt
            if self.flip_sprite_x(spr):
                spr.facing_left = not spr.facing_left
            spr.image = pg.transform.flip(spr.frames[spr.state][int(spr.frame_index % len(spr.frames[spr.state]))], not spr.facing_left, False)
        else:
            image = spr.frames['idle'][0]
            # added 'and sprite.facing_left' to prevent flipping left after lifting the right key
            spr.image = image if not self.flip_sprite_x(spr) and spr.facing_left else pg.transform.flip(image, True, False)
        
    @staticmethod
    def flip_sprite_x(sprite: pg.sprite.Sprite) -> bool:
        return sprite.facing_left and sprite.direction.x > 0 or not sprite.facing_left and sprite.direction.x < 0
        
    def render_sprites(self, dt: float) -> None:
        for spr in sorted(self.sprite_manager.get_sprites_in_radius(self.player.rect, self.all_sprites), key=lambda spr: spr.z): 
            self.screen.blit(spr.image, spr.rect.topleft - self.cam.offset)
            if groups := self.sprite_manager.get_sprite_groups(spr): # the sprite isn't just a member of all_sprites
                self.render_group_action(groups, spr, dt)
            
    def render_group_action(self, groups: set[pg.sprite.Group], sprite: pg.sprite.Sprite, dt: float) -> None:
        if self.animated_sprites in groups:
            self.animate_sprite(sprite, dt)
        # TODO: this may need to be updated if more sprites can also hold objects
        if self.colonist_sprites in groups:
            self.render_item_held(dt)

    def render_item_held(self, dt: float) -> None:
        # TODO: this is unfinished
        for sprite in self.colonist_sprites:
            if sprite.item_holding:
                item_category = self.get_item_category(sprite)
                if item_category:
                    if item_category in self.item_render_states.keys() and sprite.state in self.item_render_states[item_category]:
                        image = pg.transform.flip(self.graphics[item_category][sprite.item_holding], sprite.facing_left, False)
                        image_frame = self.get_item_animation(sprite, item_category, image, dt) # get the item's animation when in use
                        coords = sprite.rect.center - self.cam.offset + self.get_item_offset(item_category, sprite.facing_left)
                        rect = image_frame.get_rect(center = coords) if image_frame else image.get_rect(center = coords)
                        self.screen.blit(image_frame if image_frame else image, rect)

    @staticmethod
    def get_item_category(sprite: pg.sprite.Sprite) -> str:
        return sprite.item_holding.split()[-1] if ' ' in sprite.item_holding else None

    def get_item_animation(self, sprite: pg.sprite.Sprite, category: str, image: pg.Surface, dt: float) -> pg.Surface:
        match category:
            case 'pickaxe' | 'axe':
                if sprite.state in {'mining', 'chopping'}:
                    image = self.tool_animation.get_rotation(sprite, image, dt)
                    return image
        return image
    
    @staticmethod
    def get_item_offset(category, facing_left: bool) -> pg.Vector2:
        '''align the item with the sprite's arm'''
        match category:
            case 'pickaxe':
                return pg.Vector2(3 if facing_left else -3, 6) 
            case 'axe':
                return pg.Vector2(2 if facing_left else -2, -4)

    def update(self, dt: float) -> None:
        self.cam.update(pg.Vector2(self.player.rect.center))
        self.weather.update() # update the weather before the terrain to keep the sky behind the rest of the world
        self.terrain_graphics.update(self.player.current_biome)
        

class Camera:
    def __init__(self, center: pg.Vector2): 
        self.center = center
        self.offset = pg.Vector2()
        self.max_x, self.max_y = (MAP_SIZE[0] * TILE_SIZE) - (RES[0] // 2), (MAP_SIZE[1] * TILE_SIZE) - (RES[1] // 2)

    def update(self, target: pg.Vector2) -> None:
        self.center += (target - self.center) * 0.05
        self.center = pg.Vector2(max(RES[0] // 2, min(self.center.x, self.max_x)), min(self.center.y, self.max_y)) # not adding a minimum limit until the space biome (if one is to exist) is configured 
        self.offset.x, self.offset.y = round(self.center.x) - (RES[0] // 2), round(self.center.y) - (RES[1] // 2)


class TerrainGraphics:
    def __init__(self, game_obj: Main):
        self.screen: pg.Surface = game_obj.screen
        self.cam_offset: pg.Vector2 = game_obj.cam.offset
        self.graphics: dict[str, pg.Surface] = game_obj.asset_manager.assets['graphics']
        
        self.chunk_manager: ChunkManager = game_obj.chunk_manager

        proc_gen: ProcGen = game_obj.proc_gen
        self.tile_map = proc_gen.tile_map
        self.names_to_ids: dict[str, int] = proc_gen.names_to_ids
        self.ids_to_names: dict[int, str] = proc_gen.ids_to_names
        self.current_biome, self.biome_order = proc_gen.current_biome, proc_gen.biome_order 
        self.mining_map: dict[tuple[int, int], dict[str, int]] = game_obj.sprite_manager.mining.mining_map
        self.player: Player = game_obj.player

        self.biome_x_offsets = {biome: self.biome_order[biome] * BIOME_WIDTH * TILE_SIZE for biome in self.biome_order.keys()}
        self.biome_transition = BiomeTransition(self.graphics, self.render_bg_imgs)
        self.elev_data = self.get_elevation_data()

    def get_tile_type(self, x: int, y: int) -> str | None:
        name = self.ids_to_names.get(self.tile_map[x, y])
        if name == 'tree base':
            return 'dirt'
        return name if name in TILES.keys() | RAMP_TILES else None

    def get_terrain_type(self) -> str:
        '''just for getting a specific wall variant but could become more modular'''
        match self.current_biome:
            case 'highlands':
                return 'stone'

            case 'defiled':
                return 'defiled stone'

            case 'taiga':
                return 'dirt' if randint(0, 10) < 6 else 'stone'

            case 'desert':
                return 'sandstone'

            case 'underworld':
                return 'magma'

    def get_elevation_data(self) -> dict[str, int]:
        elev_params = BIOMES[self.current_biome]['elevation']
        top, bottom = elev_params['top'], elev_params['bottom']
        elev_data = {
            'range': (bottom - top) * TILE_SIZE,
            'underground span': (MAP_SIZE[1] * TILE_SIZE) - (bottom * TILE_SIZE), # minimum number of tiles from the bottom of the map to the surface
        }
        elev_data['landscape base'] = (bottom * TILE_SIZE) - (elev_data['range'] // 2.5)
        return elev_data

    def render_bg_imgs(self, bg_type: str, current_biome: str, imgs_folder: dict[int, pg.Surface] = None) -> None:
        base_y = self.elev_data['landscape base']
        if not imgs_folder: # only provided for biome transitions
            imgs_folder = self.graphics[self.current_biome][bg_type]
        num_layers = len(imgs_folder)
        biome_x_offset = self.biome_x_offsets[self.current_biome]

        for i in range(num_layers):
            img = imgs_folder[i]
            img_width, img_height = img.get_width(), img.get_height()
            num_imgs_x = ceil(RES[0] / img_width) + 2

            if bg_type == 'landscape':
                layer_idx = num_layers - i - 1
                layer_offset_y = ((img_height // 4) * layer_idx) + img_height
                parallax_factor = 1.0 if num_layers < 2 else (i + 1) / num_layers
                scroll_x = self.cam_offset.x * parallax_factor
                start_x = floor((scroll_x - biome_x_offset) / img_width)
                for x in range(start_x, start_x + num_imgs_x):
                    self.screen.blit(img, ((biome_x_offset + x * img_width) - scroll_x, base_y - layer_offset_y - self.cam_offset.y))  
            else: # underground
                start_x = floor((self.cam_offset.x - biome_x_offset) / img_width)
                dist_y = self.elev_data['underground span']
                layer_dist_y = ceil(dist_y / num_layers)
                num_imgs_y = ceil(layer_dist_y / img_height)
                for x in range(start_x, start_x + num_imgs_x):
                    for y in range(num_imgs_y):
                        self.screen.blit(img, (biome_x_offset + (img_width * x), base_y + (img_height * y)) - self.cam_offset)

    def render_tiles(self) -> None:
        air_id = self.names_to_ids['air']
        mining_map_keys = self.mining_map.keys()
        for coords in self.chunk_manager.update(): # all visible tile coordinates
            for (x, y) in coords: # individual tile coordinates
                # ensure that the tile is within the map borders & is a solid tile
                if 0 <= x < MAP_SIZE[0] and 0 <= y < MAP_SIZE[1] and self.tile_map[x, y] != air_id:
                    if tile := self.get_tile_type(x, y):
                        self.screen.blit(
                            self.get_mined_tile_image(x, y) if (x, y) in mining_map_keys else self.graphics[tile], 
                            pg.Vector2(x * TILE_SIZE, y * TILE_SIZE) - self.cam_offset
                        )
    
    def render_water(self) -> None:
        water_id = self.names_to_ids['water']
        for coords in self.chunk_manager.update():
            for (x, y) in coords:
                if 0 <= x < MAP_SIZE[0] and 0 <= y < MAP_SIZE[1] and self.tile_map[x, y] == water_id:
                    self.screen.blit(self.graphics['water'], pg.Vector2(x * TILE_SIZE, y * TILE_SIZE) - self.cam_offset)

    def get_mined_tile_image(self, x: int, y: int) -> None:
        '''reduce the opacity of a given tile as it's mined away'''
        tile_image = self.graphics[self.get_tile_type(x, y)].copy()
        tile_image.set_alpha(170) 
        return tile_image

    def get_biome_status(self, current_biome: str) -> None:
        if current_biome != self.current_biome:
            self.biome_transition.previous_biome = self.current_biome
            self.current_biome = current_biome
            self.biome_transition.active = True
            self.elev_data = self.get_elevation_data()

    def update(self, current_biome: str) -> None:
        self.get_biome_status(current_biome)
        if self.biome_transition.active:
            self.biome_transition.run(current_biome)
        else:
            self.render_bg_imgs('landscape', current_biome)
            self.render_bg_imgs('underground', current_biome)
        self.render_tiles()


class BiomeTransition:
    '''fade the new/old graphics in/out when crossing the border between biomes'''
    def __init__(self, graphics: dict[str, list[pg.Surface]], render_bg_imgs: callable):
        self.graphics = graphics
        self.render_bg_imgs = render_bg_imgs

        self.active = False
        self.previous_biome = None
        self.bg_types = ('landscape', 'underground')
        self.alphas_init = False
        self.alpha_factor = 3
        self.current_biome_min_alpha = 50
        
    def init_alphas(self, current_biome: str) -> None:
        for bg_type in self.bg_types:
            for img in self.graphics[self.previous_biome][bg_type].values():
                img.set_alpha(255) 

            for img in self.graphics[current_biome][bg_type].values():
                img.set_alpha(self.current_biome_min_alpha) 
            
            self.alphas_init = True

    def run(self, current_biome: str) -> None:
        if not self.alphas_init:
            self.init_alphas(current_biome)
            return
        
        for bg_type in self.bg_types:
            previous_biome_imgs = list(self.graphics[self.previous_biome][bg_type].values())
            current_biome_imgs = list(self.graphics[current_biome][bg_type].values())

            for img in previous_biome_imgs:
                new_alpha = max(0, img.get_alpha() - self.alpha_factor)
                img.set_alpha(new_alpha)
                self.active = new_alpha > 0 

            for img in current_biome_imgs:
                new_alpha = min(255, img.get_alpha() + self.alpha_factor)
                img.set_alpha(new_alpha)
                self.active = new_alpha < 255
            
            self.render_bg_imgs(bg_type, current_biome, previous_biome_imgs)
            self.render_bg_imgs(bg_type, current_biome, current_biome_imgs)

        if not self.active:
            self.alphas_init = False


class ToolAnimation:
    def __init__(self, screen: pg.Surface, render_item_held: callable):
        self.screen = screen
        self.render_item_held = render_item_held

    @staticmethod
    def get_rotation(sprite: pg.sprite.Sprite, image: pg.Surface, dt: float) -> pg.Surface:
        angle = 45 * sin(dt * 10)
        return pg.transform.rotate(image, -angle if not sprite.facing_left else angle) # negative angles rotate clockwise