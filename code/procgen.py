from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Main

import pygame as pg
import numpy as np
import noise
from random import randint, choice
from dataclasses import dataclass

from settings import TILES, RAMP_TILES, TILE_SIZE, MAP_SIZE, CELL_SIZE, RES, BIOMES, BIOME_WIDTH, Z_LAYERS, PRODUCTION, \
ELECTRICITY, PIPE_TRANSPORT_DIRS, LOGISTICS, STORAGE, LIQUIDS
from helper_functions import load_image

# TODO: refine the ore distribution to generate clusters of a particular gemstone rather than randomized for each tile 
class ProcGen:
    def __init__(self, game_obj: Main):
        self.screen: pg.Surface = game_obj.screen
        self.cam_offset: pg.Vector2 = game_obj.cam.offset
        self.save_data: dict[str, any] = game_obj.save_data
        
        self.names_to_ids, self.ids_to_names, self.ramp_ids = self.get_tile_ids()

        if self.save_data:
            self.load_save_data()
        else:
            self.current_biome = 'forest'
            self.biome_order, self.idxs_to_biomes = self.order_biomes()
            self.terrain = TerrainGen(self)
            self.tile_map = self.terrain.tile_map
            self.height_map = self.terrain.height_map
            self.tree_map = self.terrain.tree_gen.map
            self.cave_maps = self.terrain.cave_gen.maps
            self.player_spawn_point = self.get_player_spawn_point()
        
    def load_save_data(self) -> None:
        self.tile_map = np.array(self.save_data['tile map'], dtype=np.uint8)
        self.height_map = np.array(self.save_data['height map'], dtype=np.float32)
        self.tree_map = self.save_data['tree map']
        self.cave_maps = self.save_data['cave maps']
        self.biome_order = self.save_data['biome order']
        self.idxs_to_biomes = {i: biome for biome, i in self.biome_order.items()}
        self.current_biome = self.save_data['current biome']

    @staticmethod
    def get_tile_ids() -> tuple[dict[str, int], dict[int, str], set]:
        names_to_ids = {'air': 0, 'item extended': 1} # invisible tiles
        ids_to_names = {0: 'air', 1: 'item extended'}
        ramp_ids = set()
        existing_ids = len(ids_to_names)
        for i, name in enumerate((
            *TILES.keys(), *RAMP_TILES, *[k for k in PRODUCTION if k != 'pipe'], *[f'pipe {i}' for i in range(len(PIPE_TRANSPORT_DIRS))], 
            *ELECTRICITY, *LOGISTICS, *STORAGE, *LIQUIDS, 'tree base' 
        )):
            id_num = existing_ids + i
            names_to_ids[name] = id_num
            ids_to_names[id_num] = name
            if 'ramp' in name:
                ramp_ids.add(id_num)
        return names_to_ids, ids_to_names, ramp_ids

    def get_tile_material(self, tile_id: int) -> str:
        name = self.ids_to_names[tile_id]
        return name.split(' ')[0] if tile_id in self.ramp_ids else name

    @staticmethod
    def order_biomes() -> tuple[dict[str, int], dict[int, str]]:
        # TODO: randomize this sequence
        order = {biome: i for i, biome in enumerate(list(BIOMES.keys())[:-1])} # excluding the underworld
        idxs_to_names = {i: biome for biome, i in order.items()}
        return order, idxs_to_names

    def get_player_spawn_point(self) -> tuple[int, int]:
        center_x = MAP_SIZE[0] // 2
        y = int(self.height_map[center_x])
        if self.terrain.valid_spawn_point(center_x, y): 
            return (center_x * TILE_SIZE, y * TILE_SIZE)
        else:
            valid_coords = []
            for x in range(1, MAP_SIZE[0] - 1):
                xy = (x, int(self.height_map[x]))
                if self.terrain.valid_spawn_point(*xy):
                    valid_coords.append(xy)
            if valid_coords:
                spawn_point = min(valid_coords, key=lambda coord: abs(coord[0] - center_x)) # take the closest coordinate to the map center
                return (spawn_point[0] * TILE_SIZE, spawn_point[1] * TILE_SIZE)
            else:
                return (center_x * TILE_SIZE, y * TILE_SIZE)

    def make_save(self) -> dict[str, list | dict]:
        return {
            'tile map': self.tile_map.tolist(),
            'height map': self.height_map.tolist(),
            'tree map': [list(xy) for xy in self.tree_map],
            'cave maps': {biome: arr if isinstance(arr, list) else arr.tolist() for biome, arr in self.cave_maps.items()},
            'biome order': self.biome_order,
        }


class TerrainGen:
    def __init__(self, proc_gen: ProcGen):
        self.names_to_ids: dict[str, int] = proc_gen.names_to_ids
        self.biome_order: dict[str, int] = proc_gen.biome_order 
        self.idxs_to_biomes: dict[int, str] = proc_gen.idxs_to_biomes
        self.current_biome: str = proc_gen.current_biome
        
        self.biome_names = list(self.biome_order.keys())
        self.seed = 3638 # TODO: add the option to enter a custom seed
        self.tile_map = np.zeros(MAP_SIZE, dtype=int)
        self.height_map = self.gen_height_map()
        self.surface_lvls = np.array(self.height_map).astype(int)
        self.depth_lvls = [0.1, 0.2, 0.3, 0.4]
        self.max_depth_lvl = len(self.depth_lvls)
        self.tile_probs_max_idxs = { # limits what tiles may appear per each depth level by only slicing the tile probs dictionary up to a given index
            'highlands': {'depth 0': 2, 'depth 1': 5, 'depth 2': 6},
            'desert': {'depth 0': 2, 'depth 1': 5, 'depth 2': 6},
            'forest': {'depth 0': 2, 'depth 1': 3, 'depth 2': 5},
            'taiga': {'depth 0': 2, 'depth 1': 3, 'depth 2': 4},
            'tundra': {'depth 0': 2, 'depth 1': 3, 'depth 2': 5},
        } 
        for biome in self.tile_probs_max_idxs:
            self.tile_probs_max_idxs[biome]['depth 3'] = len(BIOMES[biome]['tile probs']) # all biome-specific tiles are available at this level
    
        self.cave_gen = CaveGen(self)
        self.place_tiles()
        self.lake_gen = LakeGen(self, proc_gen)
        self.tree_gen = TreeGen(self, proc_gen)

    def gen_height_map(self) -> np.ndarray:
        height_map = np.zeros(MAP_SIZE[0], dtype=np.float32)
        lerp_range = BIOME_WIDTH // 5
        idx_2nd_to_last = len(self.biome_names) - 2
        for i, biome in self.idxs_to_biomes.items():
            start = i * BIOME_WIDTH
            end = start + BIOME_WIDTH
            map_slice = np.arange(start, end)
            elevs = self.get_biome_elevations(map_slice, biome)
            next_biome_elevs = None
            if i <= idx_2nd_to_last:
                next_biome_elevs = self.get_biome_elevations(map_slice, self.idxs_to_biomes[i + 1])
            for biome_x, world_x in enumerate(map_slice):
                if biome_x < BIOME_WIDTH - lerp_range or next_biome_elevs is None: # outside the transition zone/edge of the world
                    height_map[world_x] = elevs[biome_x]
                else:
                    rel_pos = (biome_x - (BIOME_WIDTH - lerp_range)) / lerp_range # what % of the way x is to the end of the biome transition zone
                    height_map[world_x] = ((1 - rel_pos) * elevs[biome_x]) + (rel_pos * next_biome_elevs[biome_x])   
        return height_map

    def get_biome_elevations(self, map_slice: np.ndarray, biome: str) -> np.ndarray:
        params = BIOMES[biome]['height map']
        noise_array = np.array([
            noise.pnoise1(
                x / params['scale'], 
                params['octaves'], 
                params['persistence'], 
                params['lacunarity'], 
                base=self.seed
            ) for x in map_slice
        ], dtype=np.float32)

        params = BIOMES[biome]['elevation']
        mid_lvl = (params['bottom'] - params['top']) / 2
        return params['top'] + mid_lvl + (noise_array * mid_lvl)
            
    @staticmethod
    def get_biome_tile(current_biome: str) -> str:
        match current_biome:
            case 'forest':
                return 'dirt' if randint(0, 10) < 8 else 'stone'

            case 'taiga':
                return 'stone' if randint(0, 10) < 6 else 'dirt'

            case 'desert':
                return 'sand'

            case 'highlands':
                return 'stone' if randint(0, 10) < 7 else 'dirt'

            case 'tundra':
                return 'ice' if randint(0, 10) < 6 else 'dirt'

    def place_tiles(self) -> None:
        surface_tiles = np.array([self.names_to_ids[self.get_biome_tile(self.biome_names[x // BIOME_WIDTH])] for x in range(MAP_SIZE[0])])
        self.tile_map[np.arange(MAP_SIZE[0]), self.surface_lvls] = surface_tiles
        self.place_ramps()
        self.place_underground_tiles(surface_tiles) 

    def place_ramps(self) -> None:
        elev_diffs = np.diff(self.surface_lvls)
        r_ramp_x = np.where(elev_diffs > 0)[0]
        l_ramp_x = np.where(elev_diffs < 0)[0] + 1
        self.tile_map[r_ramp_x, self.surface_lvls[r_ramp_x]] = np.array([
            self.names_to_ids[f'{self.get_biome_tile(self.biome_names[x // BIOME_WIDTH])} ramp right'] for x in r_ramp_x
        ])
        self.tile_map[l_ramp_x, self.surface_lvls[l_ramp_x]] = np.array([
            self.names_to_ids[f'{self.get_biome_tile(self.biome_names[x // BIOME_WIDTH])} ramp left'] for x in l_ramp_x
        ])

    def place_underground_tiles(self, surface_tiles: np.ndarray) -> None:
        x_axis = np.arange(MAP_SIZE[0]).reshape(MAP_SIZE[0], 1)
        y_axis = np.arange(MAP_SIZE[1]).reshape(1, MAP_SIZE[1])
        surface_lvls = self.surface_lvls.reshape(MAP_SIZE[0], 1)
        rel_depth = (y_axis.astype(float) - surface_lvls) / float(MAP_SIZE[1])
        underground_mask = y_axis > surface_lvls
        tile_probs = {biome: BIOMES[biome]['tile probs'] for biome in self.biome_names}
        tile_names = {biome: np.array([self.names_to_ids[tile] for tile in tile_probs[biome].keys()]) for biome in self.biome_names}
        for biome, idx in self.biome_order.items(): 
            biome_cols = (x_axis // BIOME_WIDTH == idx)
            for depth_idx, mask in enumerate(self.get_depth_masks(rel_depth, underground_mask)):
                depth_mask = mask & biome_cols 
                if not depth_mask.any(): # doesn't represent the current depth
                    continue
                biome_tile_probs = list(tile_probs[biome].values())
                biome_tile_names = tile_names[biome]
                if depth_idx != self.max_depth_lvl: # certain tiles will be excluded
                    max_idx = self.tile_probs_max_idxs[biome][f'depth {depth_idx}']
                    biome_tile_probs = biome_tile_probs[:max_idx]
                    biome_tile_names = biome_tile_names[:max_idx]
                biome_tile_probs = [p / sum(biome_tile_probs) for p in biome_tile_probs] # scale the values to sum to 1, otherwise np.random.choice() will throw an error
                self.tile_map[depth_mask] = np.random.choice(biome_tile_names, size=depth_mask.sum(), p=biome_tile_probs)
                
    def get_depth_masks(self, rel_depth: np.ndarray, underground_tiles: np.ndarray) -> list[np.ndarray]:
        masks = []
        if self.current_biome not in self.cave_gen.maps.keys():
            self.cave_gen.gen_map(self.current_biome)

        for i, v in enumerate(self.depth_lvls):
            below_max = rel_depth < v
            above_min = rel_depth >= (0 if i == 0 else self.depth_lvls[i - 1])
            cave_mask = self.cave_gen.maps[self.current_biome]
            masks.append(below_max & above_min & underground_tiles & ~cave_mask)
        return masks

    def valid_spawn_point(self, x: int, y: int) -> bool:
        air_id, water_id = self.names_to_ids['air'], self.names_to_ids['water']
        return all(self.tile_map[x + dx, y] not in {air_id, water_id} for dx in (-1, 0, 1)) and \
        all(self.tile_map[x + dx, y + dy] == air_id for dx, dy in ((-1, -1), (0, -1), (1, -1)))

    @staticmethod
    def scale_tile_probs(probs: list[int], biome: str, max_idx: int) -> list[float]:
        return [p / sum(probs) for p in probs] # default values increase with fewer available tiles to select from


class CaveGen:
    def __init__(self, terrain: TerrainGen):
        self.tile_map, self.height_map = terrain.tile_map, terrain.height_map
        self.seed = terrain.seed
        self.current_biome = terrain.current_biome

        self.maps = {}
        self.gen_map(self.current_biome)

    def gen_map(self, biome: str) -> None:
        cave_map = np.zeros(MAP_SIZE, dtype=bool)
        params = BIOMES[biome]['cave map']
        screen_tiles_y = RES[1] // TILE_SIZE
        min_y = randint(screen_tiles_y // 2, screen_tiles_y) # out of view until you dig 1 tile down at minimum
        for x in range(MAP_SIZE[0]):
            surface_level = int(self.height_map[x])
            for y in range(surface_level + min_y, MAP_SIZE[1]):
                n = noise.pnoise2(
                    x / params['scale'], 
                    y / params['scale'], 
                    params['octaves'], 
                    params['persistence'], 
                    params['lacunarity'], 
                    repeatx=-1, 
                    repeaty=-1, 
                    base=self.seed
                )
                cave_map[x, y] = (n + 1) / 2 > params['threshold'] # convert to a range of 0-1 before comparing
        self.maps[biome] = cave_map


@dataclass(slots=True)
class MapSlice:
    start_x: int
    start_y: int
    end_x: int
    end_y: int

class LakeGen:
    def __init__(self, terrain: TerrainGen, proc_gen: ProcGen):
        self.tile_map, self.surface_lvls, self.seed = terrain.tile_map, terrain.surface_lvls, terrain.seed
        self.biome_order, self.idxs_to_biomes, self.names_to_ids = proc_gen.biome_order, proc_gen.idxs_to_biomes, proc_gen.names_to_ids
        self.ramp_ids = {self.names_to_ids[k] for k in self.names_to_ids if 'ramp' in k}
        self.map = np.zeros(MAP_SIZE, dtype=bool)
        
        self.min_width, self.max_width = 8, (RES[0] // TILE_SIZE) // 2 
        self.min_depth, self.max_depth = 4, 16
        self.lake_biomes = [b for b in self.biome_order if 'lake prob' in BIOMES[b]]
        self.gen_map()
        self.tile_map[self.map == True] = self.names_to_ids['water']

    def gen_map(self) -> None:
        for map_slice in self.get_valley_locations():
            fill_peak = max(map_slice.start_y, map_slice.end_y)
            if self.tile_map[map_slice.start_x if fill_peak == map_slice.start_y else map_slice.end_x, fill_peak] in self.ramp_ids: 
                fill_peak += 1  # only fill the lake up to the next highest tile
            floor = fill_peak + randint(self.min_depth, self.max_depth)
            for x in range(map_slice.start_x, map_slice.end_x):
                self.map[x, fill_peak:floor] = True  
                self.tile_map[x, :fill_peak] = self.names_to_ids['air']

    def get_valley_locations(self) -> list[MapSlice]:
        valleys = []
        for biome in self.lake_biomes:
            start_x = self.biome_order[biome] * BIOME_WIDTH
            end_x = start_x + BIOME_WIDTH
            start_y = self.surface_lvls[start_x]
            for x in range(start_x + 1, end_x):
                y = self.surface_lvls[x]
                if x - start_x > self.max_width:
                    start_x, start_y = x, y # skip the valley, too wide
                    continue
                if y < start_y: 
                    if x - start_x >= self.min_width and randint(0, 100) < BIOMES[biome]['lake prob']:
                        prev_val = None if not valleys else valleys[-1]
                        if prev_val is None or start_x - prev_val.end_x >= prev_val.end_x - prev_val.start_x: # small lakes can be close together but larger lakes get spaced out
                            valleys.append(MapSlice(start_x, start_y, x, y))
                    start_x, start_y = x, y
                    continue
        return valleys
            

class TreeGen:
    def __init__(self, terrain: TerrainGen, proc_gen: ProcGen):
        self.tile_map, self.height_map = terrain.tile_map, terrain.height_map
        self.valid_spawn_point = terrain.valid_spawn_point
        self.names_to_ids = proc_gen.names_to_ids
        self.biome_order = proc_gen.biome_order

        self.map = set()
        self.get_tree_locations()

    def get_tree_locations(self) -> None:
        for name, idx in ((k, i) for k, i in self.biome_order.items() if 'tree probs' in BIOMES[k].keys()):
            start_x = idx * BIOME_WIDTH
            for x in range(start_x, start_x + BIOME_WIDTH):
                y = int(self.height_map[x]) # surface level
                if self.valid_spawn_point(x, y) and not self.get_tree_neighbors(x, y, 2, True, True) and randint(0, 100) <= self.get_tree_prob(name, x, y):
                    self.map.add((x, y))
                    self.tile_map[x, y] = self.names_to_ids['tree base']
    
    def get_tree_prob(self, current_biome: str, x: int, y: int) -> int:
        default_prob = BIOMES[current_biome]['tree probs']
        scale_factor = default_prob // 10
        return default_prob + scale_factor * self.get_tree_neighbors(x, y, 10, True, False)
        
    def get_tree_neighbors(self, x: int, y: int, sample_size: int, check_left: bool=True, check_right: bool=True) -> int:
        num_neighbors = 0
        if check_left: # search a given number of tiles left of the starting point
            num_neighbors += sum(1 for dx in range(1, sample_size + 1) if (x - dx, y) in self.map)
        if check_right:
            num_neighbors += sum(1 for dx in range(1, sample_size + 1) if (x + dx, y) in self.map)
        return num_neighbors