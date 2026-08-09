"""Ostre efekty pixel-art, klasyczne niebo i lekkie cząsteczki."""

import math
import random

import pygame

from .config import SCREEN_HEIGHT


class Starfield:
    """Tło ekranów menu — niezależne od tła konkretnego poziomu."""

    def __init__(self, num_stars, width, height):
        self.stars = [[random.randint(0, width), random.randint(0, height),
                       random.uniform(0.1, 1.5)] for _ in range(num_stars)]
        self.width = width

    def update(self, player_vel_x):
        for star in self.stars:
            star[0] -= star[2] * (player_vel_x * 0.1 + 1)
            if star[0] < 0:
                star[0] = self.width
                star[1] = random.randint(0, SCREEN_HEIGHT)

    def draw(self, surface):
        for x, y, speed in self.stars:
            size = max(1, int(speed * 1.5))
            brightness = int(speed * 150)
            pygame.draw.rect(surface, (brightness, brightness, brightness),
                             (int(x), int(y), size, size))


class LevelBackground:
    """Czyste niebo z ostrymi prostokątnymi chmurami i gwiazdami."""

    PALETTES = (
        {"name": "Noc", "top": (9, 18, 48), "bottom": (27, 42, 78),
         "cloud": (34, 52, 83), "star": (220, 232, 255),
         "celestial": (225, 232, 210), "body": "moon"},
        {"name": "Świt", "top": (57, 57, 105), "bottom": (136, 126, 170),
         "cloud": (150, 111, 139), "star": (210, 210, 225),
         "celestial": (246, 190, 157), "body": "sun"},
        {"name": "Dzień", "top": (69, 137, 188), "bottom": (142, 190, 201),
         "cloud": (205, 218, 220), "star": (255, 255, 220),
         "celestial": (245, 216, 126), "body": "sun"},
        {"name": "Zachód", "top": (91, 49, 68), "bottom": (176, 91, 67),
         "cloud": (75, 45, 79), "star": (225, 205, 205),
         "celestial": (244, 158, 94), "body": "sun"},
    )

    def __init__(self, level_index, width, height):
        self.level_index = level_index
        self.width = width
        self.height = height
        palette = self.PALETTES[level_index % len(self.PALETTES)]
        self.time_of_day = palette["name"]
        self.sky_color = palette["top"]
        self.cloud_color = palette["cloud"]
        self.star_color = palette["star"]
        self.celestial_color = palette["celestial"]

        self.background_surface = self._create_gradient(palette["top"], palette["bottom"])
        self.clouds = [self._create_cloud(index) for index in range(random.randint(8, 14))]
        star_count = 0 if self.time_of_day == "Dzień" else (80 if self.time_of_day == "Świt" else 150)
        self.stars = [self._create_star() for _ in range(star_count)]
        self.celestial_surface = self._create_celestial(palette["body"])
        self.celestial_position = [int(width * 0.78), int(height * 0.18)]
        self.celestial_offset = [0.0, 0.0]

        # Publiczny opis warstw: wszystkie są powierzchniami pixel-artowymi,
        # bez filtrów i bez kosztownego przeliczania obrazu na piksel.
        self.layers = [
            {"name": "Layer 0 - Deep Space", "factor_x": 0.02, "factor_y": 0.02,
             "surface": self.background_surface},
            {"name": "Layer 1 - Stars", "factor_x": 0.05, "factor_y": 0.03,
             "surface": None},
            {"name": "Layer 2 - Clouds", "factor_x": 0.22, "factor_y": 0.16,
             "surface": None},
            {"name": "Layer 3 - Celestial Body", "factor_x": 0.03, "factor_y": 0.025,
             "surface": self.celestial_surface},
        ]

    def _create_gradient(self, top, bottom):
        surface = pygame.Surface((self.width, self.height))
        for y in range(self.height):
            ratio = y / max(1, self.height - 1)
            color = tuple(int(top[channel] * (1 - ratio) + bottom[channel] * ratio)
                          for channel in range(3))
            pygame.draw.line(surface, color, (0, y), (self.width, y))
        return surface

    def _create_cloud(self, index):
        """Pierwotny, charakterystyczny styl chmur Quantum Echo."""
        cloud_width = random.randint(20, 40)
        cloud_height = random.randint(10, 20)
        base_surface = pygame.Surface((cloud_width, cloud_height), pygame.SRCALPHA)

        # Kilka nachodzących na siebie kół dawało pierwotny, przyjemny kształt
        # chmur. Powiększenie nearest-neighbor zachowuje retro krawędzie.
        for _ in range(random.randint(4, 7)):
            radius = random.randint(max(2, cloud_height // 3), max(3, cloud_height // 2))
            x = random.randint(radius, max(radius, cloud_width - radius))
            y = random.randint(radius, max(radius, cloud_height - radius))
            color = tuple(max(0, min(255, channel + random.randint(-10, 10)))
                          for channel in self.cloud_color)
            pygame.draw.circle(base_surface, color, (x, y), radius)

        # Zwykłe scale zachowuje ostre krawędzie pixel-artu.
        scaled_surface = pygame.transform.scale(base_surface,
                                                 (cloud_width * 3, cloud_height * 3))
        return {"surface": scaled_surface,
                "pos": [random.randint(0, self.width), random.randint(20, int(self.height * 0.6))],
                "speed": random.uniform(0.2, 0.6),
                "factor_x": 0.12 + (index % 4) * 0.06,
                "factor_y": 0.08 + (index % 3) * 0.04}

    def _create_star(self):
        size = random.choice((1, 1, 2, 2, 3))
        return {"pos": [random.randint(0, self.width), random.randint(0, self.height)],
                "size": size, "alpha": random.randint(100, 255),
                "factor_x": random.uniform(0.025, 0.08),
                "factor_y": random.uniform(0.02, 0.06),
                "twinkle": random.uniform(0, math.pi * 2)}

    def _create_celestial(self, body):
        surface = pygame.Surface((96, 96), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*self.celestial_color, 42), (48, 48), 42)
        pygame.draw.circle(surface, self.celestial_color, (48, 48), 25)
        if body == "moon":
            pygame.draw.circle(surface, (*self.sky_color, 255), (59, 40), 23)
            for crater_x, crater_y, radius in ((34, 52, 4), (51, 63, 3), (42, 31, 2)):
                pygame.draw.rect(surface, (170, 180, 170),
                                 (crater_x, crater_y, radius * 2, radius))
        else:
            pygame.draw.rect(surface, (*self.celestial_color, 190), (45, 8, 6, 80))
            pygame.draw.rect(surface, (*self.celestial_color, 190), (8, 45, 80, 6))
        return surface

    def update(self, camera_delta_x=0.0, camera_delta_y=0.0):
        self.celestial_offset[0] = (self.celestial_offset[0] - camera_delta_x * 0.03) % self.width
        self.celestial_offset[1] = (self.celestial_offset[1] - camera_delta_y * 0.025) % self.height
        for cloud in self.clouds:
            cloud["pos"][0] -= cloud["speed"] + camera_delta_x * cloud["factor_x"]
            cloud["pos"][1] -= camera_delta_y * cloud["factor_y"]
            if cloud["pos"][0] < -cloud["surface"].get_width():
                cloud["pos"][0] = self.width
            cloud["pos"][1] %= self.height
        for star in self.stars:
            star["pos"][0] -= camera_delta_x * star["factor_x"]
            star["pos"][1] -= camera_delta_y * star["factor_y"]
            star["twinkle"] += 0.04
            star["alpha"] = max(80, min(255, int(180 + 75 * math.sin(star["twinkle"]))))
            star["pos"][0] %= self.width
            star["pos"][1] %= self.height

    def draw(self, surface):
        surface.blit(self.background_surface, (0, 0))
        celestial_x = self.celestial_position[0] + int(self.celestial_offset[0])
        celestial_y = self.celestial_position[1] + int(self.celestial_offset[1])
        surface.blit(self.celestial_surface, (celestial_x - 48, celestial_y - 48))
        for star in self.stars:
            color = (*self.star_color, star["alpha"])
            pygame.draw.rect(surface, color,
                             (int(star["pos"][0]), int(star["pos"][1]), star["size"], star["size"]))
        for cloud in self.clouds:
            surface.blit(cloud["surface"], (int(cloud["pos"][0]), int(cloud["pos"][1])))


class Particle:
    def __init__(self, x, y, color, velocity, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.vx, self.vy = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.lifetime -= 1

    def draw(self, surface):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            size = int(3 * (self.lifetime / self.max_lifetime))
            if size > 0:
                pygame.draw.circle(surface, (*self.color, alpha),
                                   (int(self.x), int(self.y)), size)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_burst(self, x, y, color, count=20):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 5)
            self.particles.append(Particle(x, y, color,
                                           (math.cos(angle) * speed, math.sin(angle) * speed),
                                           random.randint(20, 40)))

    def emit_trail(self, x, y, color):
        self.particles.append(Particle(x, y, color,
                                       (random.uniform(-0.5, 0.5), random.uniform(0.5, 1.5)),
                                       random.randint(15, 30)))

    def update(self):
        self.particles = [particle for particle in self.particles if particle.lifetime > 0]
        for particle in self.particles:
            particle.update()

    def draw(self, surface):
        for particle in self.particles:
            particle.draw(surface)
