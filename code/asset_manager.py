import pygame as pg
from os.path import join, isfile, isdir
from os import walk, listdir

class AssetManager:
    def __init__(self):
        self.graphics_folders_loaded_at_runtime = {'backgrounds', 'player', 'terrain', 'weather'} 
        self.image_lookup: dict[str, pg.Surface | None] = {}
        self.graphics = {
            subfolder: self.load_subfolders(join('..', 'graphics', subfolder)) 
            for subfolder in listdir(join('..', 'graphics'))
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

    def load_subfolders(self, dir_path: str, load_files: bool=False) -> dict[str, pg.Surface | None]:
        graphics = {}
        for name in listdir(dir_path):
            path = join(dir_path, name)
            root_subfolder = dir_path.split('\\')[2] # get the name of the first subfolder within the graphics folder (index 2 from ['..', 'graphics', <name>, ...])
            if isdir(path):
                graphics[name] = self.load_subfolders(path, load_files=root_subfolder in self.graphics_folders_loaded_at_runtime)
            elif isfile(path):
                name = name.split('.')[0]
                if name.isnumeric():
                    name = int(name) # converting name to an int if it's numeric to loop through frames for animations
                graphics[name] = self.load_image(path) if load_files else None 
                self.image_lookup[name] = {'image': graphics[name], 'dir path': path}
        return graphics

    def get_image(self, name: str) -> pg.Surface:
        if self.image_lookup.get(name, {}).get('image') is not None:
            return self.image_lookup[name]['image']
        else:
            self.image_lookup[name]['image'] = self.load_image(self.image_lookup[name]['dir path'])
            return self.image_lookup[name]['image']

    def get_subfolder(self, dir_path: str) -> dict[str, pg.Surface]:
        path = dir_path.split('\\')[2:] # ignore '..' and 'graphics'
        target_folder = path[-1]
        root_folder = path[0]
        if root_folder not in self.graphics:
            self.graphics[root_folder] = {}
        else:
            if target_folder == root_folder:
                return self.graphics[root_folder]
        current_folder = self.graphics[root_folder]
        for folder_name in path:
            if folder_name == target_folder:
                if folder_name in current_folder:
                    if not isinstance(current_folder[folder_name], dict):
                        current_folder[folder_name] = self.load_folder(dir_path)
                    return current_folder[folder_name]
                else:
                    current_folder[folder_name] = self.load_folder(dir_path)
                    return current_folder[folder_name]
            else:
                if folder_name not in current_folder:
                    current_folder[folder_name] = {}
                current_folder = current_folder[folder_name]