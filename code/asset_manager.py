import pygame as pg
from os import walk
from os.path import join
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class FolderDir:
    files: dict[str, pg.Surface | None] = field(default_factory=dict)
    subfolders: dict[str, "FolderDir"] = field(default_factory=dict)
    loaded: bool = False


class AssetManager:
    def __init__(self):
        self.graphics_folders_loaded_at_runtime = {'backgrounds', 'player', 'terrain', 'weather'} 
        self.image_lookup: dict[str, pg.Surface | None] = {}
        self.graphics_dir_root = Path('..') / 'graphics'
        self.graphics = {
            folder.name: self.load_subfolders(
                dir_path=folder, 
                load_files=folder.name in self.graphics_folders_loaded_at_runtime
            )
            for folder in self.graphics_dir_root.iterdir() if folder.is_dir()
        }
        
        self.fonts = {
            'default': pg.font.Font(join('..', 'graphics', 'fonts', 'Good Old DOS.ttf')), 
            'craft menu category': pg.font.Font(join('..', 'graphics', 'fonts', 'C&C.ttf'), size=14), 
            'item label': pg.font.Font(join('..', 'graphics', 'fonts', 'C&C.ttf'), size=16), 
            'item label small': pg.font.Font(join('..', 'graphics', 'fonts', 'C&C.ttf'), size=13), 
            'number': pg.font.Font(join('..', 'graphics', 'fonts', 'PKMN RBYGSC.ttf'), size=8)
        }

        self.colors = {
            'outline bg': 'gray18', 
            'text': 'ivory4', 
            'ui bg highlight': 'lavender', 
            'progress bar': 'gray18'
        } 

    @staticmethod
    def load_image(dir_path: str, alpha: bool=True) -> pg.Surface:
        return pg.image.load(dir_path).convert_alpha() if alpha else pg.image.load(dir_path).convert()
    
    def load_folder(self, dir_path: str) -> dict[str, pg.Surface]:
        images = {}
        for path, _, files in walk(dir_path):    
            for file_name in files:
                key = file_name.split('.')[0] # not reassigning 'file_name' because it needs the file extension when passed to load_image()
                images[int(key) if key.isnumeric() else key] = self.load_image(join(path, file_name))
        return images
    
    def load_frames(self, dir_path: str) -> list[pg.Surface]:
        frames = []
        # remove the file extension to sort from 0 to n
        for path, _, files in walk(dir_path):   
            for file in sorted(files, key=lambda name: int(name.split('.')[0])): 
                frames.append(self.load_image(join(path, file)))
        return frames

    def load_subfolders(self, dir_path: str, load_files: bool=False) -> FolderDir:
        folder_dir = FolderDir(loaded=load_files)
        if load_files:
            folder_dir.files = self.load_folder(dir_path)
        for folder in (f for f in dir_path.iterdir() if f.is_dir()):
            folder_dir.subfolders[folder.name] = self.load_subfolders(folder, load_files)
        return folder_dir

    def get_image(self, name: str) -> pg.Surface:
        if self.image_lookup.get(name, {}).get('image') is not None:
            return self.image_lookup[name]['image']
        else:
            self.image_lookup[name]['image'] = self.load_image(self.image_lookup[name]['dir path'])
            return self.image_lookup[name]['image']

    def get_folder(self, dir_path: str) -> FolderDir:
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)
        folders = dir_path.relative_to(self.graphics_dir_root).parts
        current_folder = self.graphics[folders[0]]
        for folder in folders[1:]: # excluding the current folder
            current_folder = current_folder.subfolders[folder]
        if not current_folder.loaded:
            current_folder.files = self.load_folder(dir_path)
            current_folder.loaded = True
        return current_folder