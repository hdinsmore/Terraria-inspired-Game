import pygame as pg
import numpy as np

from settings import RES
from alarm import Alarm

class Weather:
    def __init__(self, screen: pg.Surface, save_data: dict[str, any]) -> None:
        self.sky = Sky(screen, save_data)

    def update(self) -> None:
        self.sky.update()

class Sky:
    def __init__(self, screen: pg.Surface, save_data: dict[str, any]) -> None:
        self.screen = screen

        self.image = pg.Surface(RES)
        self.rgb = np.array(save_data['sky rgb'] if save_data else [150, 200, 255], dtype=int)
        self.max_rgb = [150, 200, 255]
        self.min_rgb = np.array([0, 0, 20], dtype=int)
        self.rgb_update = save_data['sky rgb update'] if save_data else -1
        self.rgb_tint_ranges = np.array([[50, 100], [125, 175]], dtype=int) # apply the tint in the morning & evening
        self.tint_alpha = save_data['sky tint alpha'] if save_data else 0
        self.tint_update = save_data['sky tint update'] if save_data else 1
        
        self.alarms = {
            'day/night cycle': Alarm(length=10_000, function=self.day_night_cycle, auto_start=True, loop=True),
            'tint update': Alarm(length=1000, function=self.update_tint, auto_start=False, loop=True)
        }

    def day_night_cycle(self) -> None:
        np.clip(np.add(self.rgb, self.rgb_update, out=self.rgb), self.min_rgb, self.max_rgb, out=self.rgb)
        if np.array_equal(self.rgb, self.max_rgb) or np.array_equal(self.rgb, self.min_rgb):
            self.rgb_update *= -1

    def render_tint(self) -> None:
        min_range, max_range = self.rgb_tint_ranges[0 if self.rgb_update > 0 else 1]
        if min_range < self.rgb[2] < max_range: # checking the 2nd index since it's the last to reach min_range
            if not self.alarms['tint update'].running:
                self.alarms['tint update'].start()
            tint_image = pg.Surface(RES)
            tint_image.fill((255, 100, 100))
            tint_image.set_alpha(self.tint_alpha)
            self.screen.blit(tint_image, (0, 0), special_flags=pg.BLEND_RGBA_ADD)

    def update_tint(self) -> None:
        if (self.tint_alpha == 0 and self.tint_update == -1) or (self.tint_alpha == 255 and self.tint_update == 1):
            self.tint_update *= -1
        else:
            self.tint_alpha += self.tint_update

    def render(self) -> None:
        self.image.fill(self.rgb)
        self.screen.blit(self.image, (0, 0))
        self.render_tint()
        
    def update(self) -> None:
        self.render()
        for alarm in self.alarms.values():
            alarm.update()

    def make_save(self) -> dict[str, list|int]:
        return {'sky rgb': self.rgb.tolist(), 'sky rgb update': self.rgb_update, 'sky tint alpha': self.tint_alpha, 'sky tint update': self.tint_update}