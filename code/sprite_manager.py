from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import numpy as np
    from player import Player
    from physics_engine import PhysicsEngine
    from input_manager import InputManager
    from sprite_base import SpriteBase
    from procgen import ProcGen

import pygame as pg
from os.path import join
from random import choice, randint
from itertools import islice

from helper_functions import load_image, cls_name_to_str
from settings import TILE_SIZE, TILES, TILE_REACH_RADIUS, TOOLS, FPS, Z_LAYERS, MAP_SIZE, RES, TREE_BIOMES, PRODUCTION, LOGISTICS, ITEMS_CAN_FLIP
from player import Player
from mining import Mining
from crafting import Crafting
from wood_gathering import WoodGathering
from nature_sprites import Tree, Cloud
from furnaces import BurnerFurnace, ElectricFurnace
from drills import BurnerDrill, ElectricDrill
from pipe import Pipe
from inserter import BurnerInserter, ElectricInserter, LongHandedInserter
from assembler import Assembler
from pumps import InletPump, OutletPump

class SpriteManager:
    def __init__(self, game_obj: Main):
        self.game_obj = game_obj

        self.screen: pg.Surface = game_obj.screen
        self.cam_offset: pg.Vector2 = game_obj.cam.offset

        self.assets: dict[str, dict[str, pg.Surface]] = game_obj.asset_manager.assets
        self.graphics: dict[str, pg.Surface] = self.assets['graphics']

        proc_gen: ProcGen = game_obj.proc_gen
        self.tile_map = proc_gen.tile_map
        self.tree_map = proc_gen.tree_map
        self.height_map = proc_gen.height_map
        self.current_biome = proc_gen.current_biome
        self.names_to_ids, self.ids_to_names = proc_gen.names_to_ids, proc_gen.ids_to_names
        self.get_tile_material = proc_gen.get_tile_material

        physics_engine: PhysicsEngine = game_obj.physics_engine
        self.sprite_movement = physics_engine.sprite_movement
        self.collision_map = physics_engine.collision_map

        input_manager = game_obj.input_manager
        self.keyboard, self.mouse = input_manager.keyboard, input_manager.mouse

        self.save_data: dict[str, any] | None = game_obj.save_data

        self.all_sprites = pg.sprite.Group()
        self.active_sprites = pg.sprite.Group() # has an update method
        self.animated_sprites = pg.sprite.Group()
        self.player_sprite = pg.sprite.GroupSingle()
        self.colonist_sprites = pg.sprite.Group()
        self.mech_sprites = pg.sprite.Group()
        self.nature_sprites = pg.sprite.Group()
        self.cloud_sprites = pg.sprite.Group()
        self.tree_sprites = pg.sprite.Group()
        self.item_sprites = pg.sprite.Group()
        self.sprites_with_ui = pg.sprite.Group()
        self.all_groups = {k: v for k, v in vars(self).items() if isinstance(v, pg.sprite.Group)}

        self.mining = Mining(self)

        self.crafting = Crafting()

        self.init_trees()

        self.items_init_when_placed = {
            cls_name_to_str(cls): cls for cls in (
                BurnerFurnace, ElectricFurnace, BurnerDrill, ElectricDrill, Pipe, BurnerInserter, 
                ElectricInserter, Assembler, InletPump, OutletPump
            )
        }

        self.ui = self.item_placement = self.player = None # not initialized until after the sprite manager
    
    def init_trees(self) -> None:
        if self.current_biome in TREE_BIOMES:
            image_folder = self.graphics[self.current_biome]['trees']
            tree_map = self.tree_map if not self.save_data else self.save_data['tree map']
            for i, xy in enumerate(tree_map): 
                Tree(
                    xy=(pg.Vector2(xy) * TILE_SIZE) - self.cam_offset, 
                    image=choice(image_folder), 
                    sprite_groups=[self.all_sprites, self.nature_sprites, self.tree_sprites], 
                    z=Z_LAYERS['bg'], 
                    tree_map_xy=xy,
                    sprite_manager=self,
                    save_data=self.save_data['sprites']['tree'][i] if self.save_data is not None else None
                )

        self.wood_gathering = WoodGathering(self)

    def init_placed_items(self) -> None:
        for item, tiles_covered in self.item_placement.items(): 
            for xy in tiles_covered:
               self.items_init_when_placed[item](**self.get_cls_init_params(name, xy))

    def update_clouds(self, player: pg.sprite.Sprite) -> None:
        if not self.cloud_sprites:
            surface_lvl = self.height_map[player.rect.x // TILE_SIZE]
            if player.rect.y // TILE_SIZE < surface_lvl:
                img_folder = self.graphics['clouds']
                for i in range(randint(10, 15)):
                    Cloud(
                        pg.Vector2(player.rect.x + RES[0] + (50 * (i + 1)), surface_lvl + randint(-2000, -1500)),
                        img_folder[randint(0, len(img_folder) - 1)],
                        Z_LAYERS['clouds'],
                        [self.all_sprites, self.nature_sprites, self.cloud_sprites],
                        randint(1, 3),
                        player,
                        self.rect_in_sprite_radius
                    )

    @staticmethod
    def get_tool_strength(sprite: pg.sprite.Sprite) -> int:
        if sprite.item_holding:
            material, tool = sprite.item_holding.split()
            return TOOLS[tool][material]['strength']
        return sprite.arm_strength
    
    @staticmethod
    def end_action(sprite: pg.sprite.Sprite) -> None:
        sprite.state = 'idle'
        idle_img = sprite.frames['idle'][0]
        sprite.image = idle_img if sprite.facing_left else pg.transform.flip(idle_img, True, False)

    def pick_up_item(self, obj: object, name: str, amount: int=1) -> None:
        for sprite in self.get_sprites_in_radius(obj.rect, self.human_sprites):
            inv = sprite.inventory
            if sprite.rect.colliderect(obj.rect) and not (name in inv.contents.keys() and inv.contents[name]['amount'] == inv.slot_capacity[name]):
                inv.add_item(name, amount)
                self.ui.render_new_item_name(name, obj.rect, amount)
                obj.kill()
                return

    def get_sprites_in_radius(self, rect: pg.Rect, group: pg.sprite.Group, x_dist: int=(RES[0] // 2), y_dist: int=(RES[1] // 2)) -> list[pg.sprite.Sprite]:
        return [spr for spr in group if self.rect_in_sprite_radius(spr, rect, x_dist, y_dist)]
    
    def rect_in_sprite_radius(
        self, 
        spr: pg.sprite.Sprite, 
        rect: pg.Rect, 
        x_dist: int=(RES[0] // 2), 
        y_dist: int=(RES[1] // 2), 
        spr_world_space: bool=True, 
        rect_world_space: bool=True
    ) -> bool:
        spr_xy = spr.rect.center if spr_world_space else spr.rect.center + self.cam_offset
        rect_xy = rect.center if rect_world_space else rect.center + self.cam_offset
        return abs(spr_xy[0] - rect_xy[0]) < x_dist and abs(spr_xy[1] - rect_xy[1]) < y_dist
    
    def get_sprite_groups(self, sprite: pg.sprite.Sprite) -> set[pg.sprite.Group]:
        return set(group for group in self.all_groups.values() if sprite in group)

    def check_dir_flip(self, sprite: pg.sprite.Sprite) -> None:
        if sprite.rect.collidepoint(self.mouse.xy_world) and self.keyboard.pressed_keys[self.keyboard.key_bindings['rotate item']]:
            sprite.image = pg.transform.flip(sprite.image, True, False)
            sprite.direction = 'left' if sprite.direction in {'right', None} else 'right'

    def get_cls_init_params(
        self, 
        name: str, 
        tiles_covered: list[tuple[int, int]] | tuple[int, int], 
        save_idx: int=None
    ) -> dict[str, any]:
        tile_x, tile_y = tiles_covered if isinstance(tiles_covered, tuple) else tiles_covered[0] # only extract the topleft coordinate for multi-tile items
        params = {
            'save_data': self.save_data['sprites'][name][save_idx] if self.save_data else None,
            'xy': (tile_x * TILE_SIZE, tile_y * TILE_SIZE), 
            'image': self.assets['graphics'][name], 
            'sprite_groups': [self.all_sprites, self.active_sprites, self.mech_sprites, self.sprites_with_ui], 
            'game_obj': self.game_obj,
        }
        if 'pipe' in name:
            params['variant_idx'] = int(name[-1])
        else:
            params['ui'] = self.ui
            if name in ITEMS_CAN_FLIP:
                params['direction'] = self.player.item_flip_dir
        return params

    def update(self, player: pg.sprite.Sprite, dt: float) -> None:
        for sprite in self.active_sprites:
            sprite.update(dt)

        self.mining.update(dt)
        self.wood_gathering.update(player, self.mouse.buttons_held, self.mouse.xy_world)
        self.update_clouds(player)

    def update_ui(self): # separate from the update function to let the graphics engine draw the sprites first to not overlap with the ui
        for sprite in self.sprites_with_ui:
            sprite.ui.render()