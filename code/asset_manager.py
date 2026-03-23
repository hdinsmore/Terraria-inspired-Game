import pygame as pg
from os.path import join, isfile, isdir
from os import walk, listdir

class AssetManager:
    def __init__(self):
        self.graphics_folders_loaded_at_runtime = {'backgrounds', 'player', 'terrain', 'weather'} 
        self.graphics = {
            subfolder: self.load_subfolders(join('..', 'graphics', subfolder)) 
            for subfolder in listdir(join('..', 'graphics'))
        }
        print(self.graphics)

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
                graphics[int(name) if name.isnumeric() else name] = self.load_image(path) if load_files else None # converting name to an int if it's numeric to loop through frames for animations
        return graphics
        
    def get_image(self, file_name: str) -> pg.Surface:
        pass

    def get_folder(self, dir_path: str) -> dict[str, pg.Surface]:
        pass