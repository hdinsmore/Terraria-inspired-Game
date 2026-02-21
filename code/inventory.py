from __future__ import annotations
from typing import Sequence
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from input_manager import Keyboard
    from player import Player

import pygame as pg
from collections import defaultdict

from settings import TILES, TOOLS

class SpriteInventory:
    def __init__(self, parent_sprite: pg.sprite.Sprite, save_data: dict[str, any]=None, default_contents: dict[str, dict[str, int]]=None):
        self.parent_sprite = parent_sprite
        if save_data:
            self.contents = save_data['contents']
            self.index = save_data['index']
        else:
            if default_contents:
                self.contents = default_contents
                for i, item in enumerate(self.contents):
                    self.contents[item]['index'] = i
            else:
                self.contents = {}

            self.index = self.last_idx_with_item = 0

        self.num_slots = 50
        self.slot_capacity = defaultdict(lambda: 999)
        self.set_slot_capacity()
        
    def set_slot_capacity(self) -> None:
        for tile in TILES.keys():
            self.slot_capacity[tile] = 9999 

        for tool in TOOLS.keys():
            self.slot_capacity[tool] = 99   

    def add_item(self, item: str, amount: int=1) -> None:
        items = self.contents.keys()
        if item not in items:
            if self.last_idx_with_item < self.num_slots:
                self.last_idx_with_item += 1
                self.contents[item] = {'amount': amount, 'index': self.last_idx_with_item}
        else:
            max_amount = amount
            if item in self.slot_capacity.keys():
                max_amount = min(amount, self.slot_capacity['item'] - self.contents[item]['amount'])
            self.contents[item]['amount'] += max_amount

        if not self.parent_sprite.item_holding:
            self.parent_sprite.item_holding = item
            self.index = self.contents[item]['index']
            
    def remove_item(self, item: str=None, amount: int=1) -> None:
        if item is None:
            item = self.parent_sprite.item_holding
        if self.contents[item]['amount'] - amount >= 1:
            self.contents[item]['amount'] -= amount
        else:
            self.parent_sprite.item_holding = None
            del self.contents[item]
            for i, (name, data) in enumerate(self.contents.items()):
                data['index'] = i


class PlayerInventory(SpriteInventory):
    def __init__(self, parent_sprite: Player, save_data: dict[str, any]):
        super().__init__(parent_sprite, save_data, default_contents=None if save_data else {
            'wood': {'amount': 100}, 
            'copper': {'amount': 100}, 
            'stone pickaxe': {'amount': 1}, 
            'pipe 0': {'amount': 100}, 
            'burner inserter': {'amount': 10}, 
            'burner furnace': {'amount': 10}, 
            'assembler': {'amount': 10}, 
            'wood torch': {'amount': 99},
            'outlet pump': {'amount': 10},
            'burner drill': {'amount': 10}
        })
         
    def get_idx_selection(self, keyboard: Keyboard) -> None:
        for key in keyboard.num_keys:
            if keyboard.pressed_keys[key]:
                self.index = keyboard.key_map[key]
                items = list(self.contents.keys())
                self.parent_sprite.item_holding = items[self.index] if self.index < len(items) else None
                return