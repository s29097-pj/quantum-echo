"""Wczytywanie i reprezentacja poziomów."""

import pygame

from .config import SCREEN_HEIGHT, SCREEN_WIDTH
from .effects import LevelBackground
from .entities import (
    Collectible, ExitZone, Hazard, Key, Platform, Player, TemporalPlatform,
    TimeDilationZone, ParadoxSwitch, ParadoxDoor,
)

class Level:
    def __init__(self, level_data, level_index):
        self.platforms = pygame.sprite.Group()
        self.temporal_platforms = pygame.sprite.Group()
        self.hazards = pygame.sprite.Group()
        self.collectibles = []
        self.keys = []  # Zamiast przycisków
        self.time_dilation_zones = pygame.sprite.Group()
        self.paradox_switches = pygame.sprite.Group()
        self.paradox_doors = pygame.sprite.Group()
        self.exit_zone = None
        self._solid_platforms_cache = None
        self._solid_platforms_signature = None

        # Wczytujemy dane poziomu z pliku JSON
        self.background = LevelBackground(level_index, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Wczytujemy platformy, przeszkody, przedmioty i strefę wyjścia
        for platform_data in level_data.get('platforms', []):
            p = Platform(platform_data['x'], platform_data['y'], platform_data['width'], platform_data['height'],
                         platform_data.get('moving', False), platform_data.get('move_range', 100))
            self.platforms.add(p)

        # Wczytujemy platformy czasowe
        for platform_data in level_data.get('temporal_platforms', []):
            p = TemporalPlatform(platform_data['x'], platform_data['y'], platform_data['width'], platform_data['height'],
                                 platform_data.get('initial_state', 'solid'),
                                 platform_data.get('solid_time', 180),
                                 platform_data.get('phased_time', 120))
            self.temporal_platforms.add(p)

        # Nowe elementy są opcjonalne, więc stare poziomy pozostają poprawne.
        zone_data = level_data.get('time_dilation_zones',
                                   level_data.get('slow_motion_zones', []))
        for data in zone_data:
            self.time_dilation_zones.add(TimeDilationZone(
                data['x'], data['y'], data['width'], data['height'],
                data.get('factor', 0.5)))

        for data in level_data.get('paradox_switches',
                                   level_data.get('paradox_buttons', [])):
            self.paradox_switches.add(ParadoxSwitch(
                data['x'], data['y'], data.get('width', 48), data.get('height', 16)))

        for data in level_data.get('paradox_doors',
                                   level_data.get('locked_passages', [])):
            self.paradox_doors.add(ParadoxDoor(
                data['x'], data['y'], data['width'], data['height'],
                data.get('locked', data.get('initially_locked', True))))

        # Wczytujemy niebezpieczeństwa (np. kolce)
        for hazard_data in level_data.get('hazards', []):
            h = Hazard(hazard_data['x'], hazard_data['y'], hazard_data['width'], hazard_data['height'])
            self.hazards.add(h)

        # Wczytujemy przedmioty do zbierania
        for collectible_data in level_data.get('collectibles', []):
            c = Collectible(collectible_data['x'], collectible_data['y'], collectible_data.get('type', 'gem'))
            self.collectibles.append(c)

        # Wczytujemy klucze (używając starego pola 'buttons' z JSON dla kompatybilności)
        for key_data in level_data.get('buttons', []):
            self.keys.append(Key(key_data['x'], key_data['y']))

        # Wczytujemy strefę wyjścia
        self.start_pos = (level_data['start']['x'], level_data['start']['y'])

        end_data = level_data.get('end', {})
        self.exit_zone = ExitZone(end_data.get('x', 900), end_data.get('y', 100))
        # Wyjście jest zablokowane, jeśli na poziomie są jakiekolwiek klucze
        self.exit_zone.locked = bool(self.keys) or bool(end_data.get('locked', False))

    # Jeśli nie ma kluczy, odblokuj wyjście
    def get_solid_platforms(self):
        """Zwraca cache'owaną listę kolizji; nie alokuje grupy co klatkę."""
        signature = tuple(p.state for p in self.temporal_platforms) + tuple(
            door.locked for door in self.paradox_doors)
        if signature != self._solid_platforms_signature:
            self._solid_platforms_cache = list(self.platforms)
            self._solid_platforms_cache.extend(
                p for p in self.temporal_platforms if p.state == 'solid')
            self._solid_platforms_cache.extend(
                door for door in self.paradox_doors if door.locked)
            self._solid_platforms_signature = signature
        return self._solid_platforms_cache

    def get_time_scale(self, actor):
        factors = [zone.factor for zone in self.time_dilation_zones
                   if actor.rect.colliderect(zone.rect)]
        return min(factors, default=1.0)

    # Aktualizacja stanu poziomu
    def update(self, player_vel_x, player_vel_y=0):
        previous_temporal_states = tuple(p.state for p in self.temporal_platforms)
        self.background.update(player_vel_x, player_vel_y)
        self.platforms.update()
        self.temporal_platforms.update()
        self.time_dilation_zones.update()
        self.paradox_switches.update()
        self.paradox_doors.update()
        self.hazards.update()
        for collectible in self.collectibles:
            collectible.update()
        for key in self.keys:
            key.update()
        self.exit_zone.update()

        # Odblokuj wyjście, jeśli wszystkie klucze zostały zebrane
        if self.exit_zone.locked and not self.keys:
            self.exit_zone.locked = False
            Player.play_sfx("gate_open")

        for switch in self.paradox_switches:
            if switch.pressed:
                for door in self.paradox_doors:
                    door.open()
        current_temporal_states = tuple(p.state for p in self.temporal_platforms)
        if current_temporal_states != previous_temporal_states:
            self._solid_platforms_signature = None

    # Sprawdź, czy gracz zebrał wszystkie przedmioty
    def draw(self, surface, draw_background=True):
        if draw_background:
            self.background.draw(surface)
        for platform in self.platforms:
            platform.draw(surface)
        for platform in self.temporal_platforms:
            platform.draw(surface)
        for zone in self.time_dilation_zones:
            zone.draw(surface)
        for hazard in self.hazards:
            hazard.draw(surface)
        for collectible in self.collectibles:
            collectible.draw(surface)
        for key in self.keys:
            key.draw(surface)
        for switch in self.paradox_switches:
            switch.draw(surface)
        for door in self.paradox_doors:
            door.draw(surface)
        self.exit_zone.draw(surface, remaining_keys=len(self.keys))
