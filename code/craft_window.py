from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui import UI

import pygame as pg
from math import ceil

from settings import TILE_SIZE, TOOLS, MATERIALS, ELECTRICITY, PRODUCTION, LOGISTICS, RESEARCH, STORAGE, DECOR

class CraftWindow:
    def __init__(self, ui: UI, craft_item: callable):
        self.screen = ui.screen
        self.cam_offset = ui.cam_offset
        self.graphics = ui.assets['graphics']
        self.fonts = ui.assets['fonts']
        self.colors = ui.assets['colors']

        self.mouse = ui.mouse
        self.player = ui.player

        self.inventory_ui = ui.inventory_ui

        self.gen_outline = ui.gen_outline
        self.gen_bg = ui.gen_bg
        self.render_inv_item_name = ui.render_inv_item_name
        self.get_scaled_image = ui.get_scaled_image

        self.height = ui.get_craft_window_height()
        self.width = int(self.inventory_ui.outline_width * 1.3)
        self.padding = 5
        self.outline_rect = pg.Rect(
            self.inventory_ui.outline_rect_closed.right + self.padding, self.padding, self.width, self.height # the right side is the same with either outline rect
        )
        
        self.cell_height = self.cell_width = TILE_SIZE * 2 # for the grid of items comprising a given category
        self.category_grid = CategoryGrid(self)
        self.item_grid = ItemGrid(
            self, 
            self.outline_rect.top + (self.category_grid.row_height * self.category_grid.num_rows) + self.padding, 
            craft_item
        )
        
        self.opened = False

    def render(self) -> None:
        self.gen_outline(self.outline_rect, color='black')
        self.gen_bg(pg.Rect(self.outline_rect.topleft, self.outline_rect.size))

    def update(self) -> None:
        if self.opened:
            self.render()
            self.category_grid.opened = self.opened
            self.category_grid.update()
            self.item_grid.selected_category = self.category_grid.selected_category
            self.item_grid.update()


class CategoryGrid:
    def __init__(self, craft_window: CraftWindow):
        self.screen = craft_window.screen
        self.cam_offset = craft_window.cam_offset
        self.graphics = craft_window.graphics
        self.fonts = craft_window.fonts
        self.colors = craft_window.colors 

        self.mouse = craft_window.mouse
        
        self.window_outline_rect = craft_window.outline_rect
        self.padding = craft_window.padding

        self.gen_outline = craft_window.gen_outline
        self.gen_bg = craft_window.gen_bg

        self.inv_ui = craft_window.inventory_ui

        self.opened = False

        self.categories = {
            'tools': {**TOOLS},
            'materials': {k: v for k, v in MATERIALS.items() if v['recipe'] is not None}, # ignore items like wood that can't be crafted 
            'electricity': {**ELECTRICITY},
            'production': {**PRODUCTION},
            'logistics': {**LOGISTICS},
            'research': {**RESEARCH},
            'storage': {**STORAGE},
            'decor': {**DECOR}
        }
        self.selected_category = None
        self.open_subcategory = False
        self.category_keys = list(self.categories.keys())
        self.num_categories = len(self.category_keys)
        
        self.num_cols = 2
        self.col_width = self.window_outline_rect.width // self.num_cols
        self.num_rows = self.num_categories // self.num_cols
        self.row_height = (self.window_outline_rect.height // 2) // self.num_rows
        self.image_padding = 10
        self.outline_padding = 2
        self.borders = self.precompute_borders()

    def precompute_borders(self) -> dict[str, list[tuple[int, int]]]:
        borders = {'x': [], 'y': []}
        padding = 2 # account for the outline width
        for col in range(1, self.num_cols + 1):
            borders['x'].append((
                self.window_outline_rect.left, 
                self.window_outline_rect.left + (self.col_width * col) + self.outline_padding
            ))
        for row in range(1, self.num_rows + 1):
            borders['y'].append((
                self.window_outline_rect.top, 
                self.window_outline_rect.top + (self.row_height * row) + self.outline_padding
            ))
        return borders

    def render_grid(self) -> None:
        for col in range(self.num_cols):
            left = self.window_outline_rect.left + (self.col_width * col)
            col_rect = pg.Rect(left, self.window_outline_rect.top, self.col_width, self.row_height * self.num_rows)
            self.gen_outline(col_rect)
            pg.draw.rect(self.screen, 'black', col_rect, 1)
            for row in range(self.num_rows):
                top = self.window_outline_rect.top + (self.row_height * row)
                row_rect = pg.Rect(
                    self.window_outline_rect.left, top, 
                    self.window_outline_rect.width - self.outline_padding, self.row_height
                )
                pg.draw.rect(self.screen, 'black', row_rect, 1)
                category = self.category_keys[col + (row * self.num_cols)]
                self.render_category_images(category, col, row)
                self.render_category_names((left, top), category)

    def render_category_images(self, category: str, col: int, row: int) -> None:
        image = self.graphics['icons'][category].copy()
        if category != self.selected_category:
            image.set_alpha(150)
        # get the space between the border of the image and the cell containing it
        padding_x = self.col_width - image.get_width()
        padding_y = self.row_height - image.get_height()
        # center the image within a given cell
        offset = pg.Vector2(
            (col * self.col_width) + (padding_x // 2), 
            (row * self.row_height) + (padding_y // 2) + self.image_padding
        ) 
        image_rect = image.get_rect(topleft = self.window_outline_rect.topleft + offset)
        self.screen.blit(image, image_rect)

    def render_category_names(self, topleft: tuple[int, int], category: str) -> None:
        text = self.fonts['craft menu category'].render(category, True, self.colors['text'])
        border = pg.Rect(
            topleft + pg.Vector2(self.outline_padding, self.outline_padding), 
            text.size + pg.Vector2(self.outline_padding * 2, self.outline_padding * 2)
        )
        self.gen_bg(border)
        self.gen_outline(border, color='black')
        text_rect = text.get_rect(topleft=topleft + pg.Vector2(self.outline_padding * 2, self.outline_padding * 2))
        self.screen.blit(text, text_rect)

    def select_category(self) -> None:
        if self.opened:
            if self.mouse_on_grid() and self.mouse.buttons_pressed['left']:
                col, row = self.get_category_overlap()
                self.selected_category = self.category_keys[col + (row * self.num_cols)]
        else:
            self.selected_category = None

    def mouse_on_grid(self) -> bool:
        x, y = self.mouse.xy_screen
        return self.window_outline_rect.left < x < self.window_outline_rect.right and \
        self.window_outline_rect.top < y < self.window_outline_rect.top + (self.num_rows * self.row_height)

    def get_category_overlap(self) -> list[int]:
        x, y = self.mouse.xy_screen
        return [
            next((i for i, (x0, x1) in enumerate(self.borders['x']) if x0 <= x < x1), None),
            next((i for i, (y0, y1) in enumerate(self.borders['y']) if y0 <= y < y1), None)
        ]

    def update(self) -> None:
        self.render_grid()
        self.select_category()


class ItemGrid:
    def __init__(self, craft_window: CraftWindow, top_pt: int, craft_item: callable):
        self.craft_window = craft_window
        self.mouse = craft_window.mouse
        self.screen = craft_window.screen
        self.graphics = craft_window.graphics
        self.window_outline_rect = craft_window.outline_rect
        self.categories = craft_window.category_grid.categories
        self.player = craft_window.player
        self.gen_outline = craft_window.gen_outline
        self.render_inv_item_name = craft_window.render_inv_item_name
        self.get_scaled_image = craft_window.get_scaled_image
        self.craft_item = craft_item
        self.top_pt = top_pt
        
        self.cell_width = self.cell_height = TILE_SIZE * 2
        self.x_cells = self.window_outline_rect.width // self.cell_width
        self.left_padding = (self.window_outline_rect.width - (self.x_cells * self.cell_width)) // 2
        self.left = self.window_outline_rect.left + self.left_padding

    def render_item_slots(self) -> None: # not defining these in __init__ since they rely on the selected category
        self.num_slots = len(self.categories[self.selected_category])
        for x in range(self.x_cells):
            for y in range(ceil(self.num_slots / self.x_cells)):
                index = x + (y * self.x_cells)
                if index < self.num_slots:
                    cell = pg.Rect(
                        self.left + (self.cell_width * x), self.top_pt + (self.cell_height * y), 
                        self.cell_width - 1, self.cell_height - 1
                    )
                    rect = pg.draw.rect(self.screen, 'black', cell, 1)
                    self.render_item_images(index, x, y)

    def render_item_images(self, index: int, x: int, y: int) -> None:
        item_name = list(self.categories[self.selected_category].keys())[index]
        if item_name == 'pipe':
            item_name += ' 0' # add the default pipe index
        try:
            if not isinstance(self.graphics[item_name], dict):
                image = self.graphics[item_name]
                padding = 2
                scaled_image = self.get_scaled_image(image, item_name, self.cell_width, self.cell_height, padding)
                rect = scaled_image.get_rect(center = (
                    self.left + (self.cell_width * x) + (self.cell_width // 2), 
                    self.top_pt + (self.cell_height * y) + (self.cell_height // 2)
                ))
                self.screen.blit(scaled_image, rect)
                self.render_inv_item_name(rect, item_name)
                self.get_selected_item(rect, item_name)
        except KeyError:
            pass
    
    def get_selected_item(self, rect: pg.Rect, item_name: str) -> None:
        if rect.collidepoint(self.mouse.xy_screen) and self.mouse.buttons_pressed['left']:
            item_data = self.categories[self.selected_category][item_name]
            self.craft_item(item_name, item_data['recipe'], self.player)

    def update(self) -> None:
        if self.selected_category:
            self.render_item_slots()