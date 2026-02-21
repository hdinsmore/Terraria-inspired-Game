import pygame as pg

class Crafting:
    @staticmethod
    def craft_item(name: str, recipe: dict[str, int], sprite: pg.sprite.Sprite) -> None:
        inv = sprite.inventory
        recipe = recipe.items()
        if all(inv.contents.get(item, {}).get('amount', 0) >= amt for item, amt in recipe):
            for item, amt in recipe:
                inv.remove_item(item, amt)
            inv.add_item(name)