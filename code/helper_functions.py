import pygame as pg
from os import walk
from os.path import join
import re

def load_image(dir_path: str, alpha: bool=True) -> pg.Surface:
    return pg.image.load(dir_path).convert_alpha() if alpha else pg.image.load(dir_path).convert()

def load_folder(dir_path: str) -> dict[str, pg.Surface]:
    images = {}
    for path, _, files in walk(dir_path):    
        for file_name in files:
            key = file_name.split('.')[0] # not reassigning 'file_name' because it needs the file extension when passed to load_image()
            images[int(key) if key.isnumeric() else key] = load_image(join(path, file_name))
    return images

def load_subfolders(dir_path: str) -> dict[str, dict[str, pg.Surface]]:
    images = {}
    for _, subfolders, __ in walk(dir_path):
        for folder in subfolders:
            path = join(dir_path, folder)
            images[folder] = load_folder(path)    
    return images

def load_frames(dir_path: str) -> list[pg.Surface]:
    frames = []
    # remove the file extension to sort from 0 to n
    for path, _, files in walk(dir_path):   
        for file in sorted(files, key = lambda name: int(name.split('.')[0])): 
            frames.append(load_image(join(path, file)))
    return frames

def cls_name_to_str(cls: pg.sprite.Sprite) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', cls.__name__ if isinstance(cls, type) else cls.__class__.__name__).lower()