import pygame as pg

class Alarm:
    def __init__(
        self, 
        length: int, 
        function: callable=None, 
        auto: bool=False, 
        loop: bool=False, 
        track_percent: bool=False, 
        *args, 
        **kwargs
    ):
        self.length = length
        self.function = function
        self.loop = loop
        self.track_percent = track_percent
        if self.track_percent:
            self.percent = 0
        self.args = args
        self.kwargs = kwargs
        
        self.running = False
        if auto: 
            self.start()

    def start(self) -> None:
        self.running = True
        self.start_time = pg.time.get_ticks()

    def end(self) -> None:
        self.running = False
        self.start_time = 0

        if self.function:
            self.function(*self.args, **self.kwargs)

        if self.loop:
            self.start()

    def update(self) -> None:
        if self.running:
            progress = pg.time.get_ticks() - self.start_time

            if self.track_percent:
                self.percent = (progress / self.length) * 100
                
            if progress >= self.length:
                self.end()