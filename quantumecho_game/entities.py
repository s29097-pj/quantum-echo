"""Obiekty świata gry i ich zachowanie."""

import math
import random
import pygame

from .config import (
    BLACK, BLUE, CYAN, GRAVITY, JUMP_FORCE, ORANGE, PLAYER_SPEED, RED, SCREEN_HEIGHT,
    SCREEN_WIDTH, WHITE, YELLOW, PURPLE, PLAYER_WIDTH, PLAYER_HEIGHT,
)
from .runtime import font_medium, font_small

class Player(pygame.sprite.Sprite):
    audio_callback = None

    @classmethod
    def set_audio_callback(cls, callback):
        """Podłącza odtwarzacz efektów bez uzależniania encji od app.py."""
        cls.audio_callback = callback

    @classmethod
    def play_sfx(cls, name):
        if cls.audio_callback:
            cls.audio_callback(name)

    def __init__(self, x, y, is_echo=False):
        super().__init__()
        self.image = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT))
        self.color = BLUE if not is_echo else CYAN
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

        # Fizyka
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False

        # Echo system
        self.is_echo = is_echo

        # Power-upy
        self.has_double_jump = False
        self.double_jump_used = False
        self.invincible = False
        self.invincible_timer = 0

        # Animacja
        self.animation_timer = 0
        self.pulse_effect = 0
        # Akumulator pozwala obsługiwać ułamkowe tempo bez zmiany stałej
        # częstotliwości pętli gry.  Echo zawsze pozostaje w skali 1.0.
        self.time_scale = 1.0
        self._motion_accumulator = 0.0

    # Aktualizacja gracza
    def update(self, platforms, hazards, collectibles, keys, history_pos=None,
               time_dilation_zones=(), paradox_switches=()):
        collision_result = None

        # Sprawdź kolizje tylko dla echa, jeśli jest aktywne
        if self.is_echo:
            if history_pos:
                self.rect.topleft = history_pos
            # Echo jest fizyczne dla przełączników, ale nie zużywa zasobów
            # gracza i nie przejmuje jego kolizji obrażeń/przedmiotów.
            for switch in paradox_switches:
                if not switch.pressed and self.rect.colliderect(switch.rect):
                    switch.activate()
                    collision_result = "paradox_switch"
        else:
            self.time_scale = min(
                (zone.factor for zone in time_dilation_zones
                 if self.rect.colliderect(zone.rect)), default=1.0
            )
            self._motion_accumulator += self.time_scale
            if self._motion_accumulator < 1.0:
                self._update_effects(self.time_scale)
                return None
            self._motion_accumulator -= 1.0
            self._apply_physics(platforms)
            collision_result = self._check_other_collisions(hazards, collectibles, keys)

        # Aktualizuj efekty wizualne dla obu
        self._update_effects(self.time_scale if not self.is_echo else 1.0)

        return collision_result

    # Obsługuje wejście gracza
    def handle_input(self, keys):
        # Ruch poziomy
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED

    # Obsługuje skok gracza
    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_FORCE
            self.on_ground = False
            self.double_jump_used = False
            self.play_sfx("jump")
            return True
        elif self.has_double_jump and not self.double_jump_used:
            self.vel_y = JUMP_FORCE * 0.8  # Drugi skok jest nieco słabszy
            self.double_jump_used = True
            self.play_sfx("jump")
            return True
        return False

    def _apply_physics(self, platforms):
        # Ruch poziomy i kolizje z platformami
        self.rect.x += self.vel_x
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_x > 0:
                    self.rect.right = platform.rect.left
                elif self.vel_x < 0:
                    self.rect.left = platform.rect.right

        # Ruch pionowy i kolizje z platformami
        self.vel_y += GRAVITY
        if self.vel_y > 20:
            self.vel_y = 20
        self.rect.y += self.vel_y
        self.on_ground = False

        # Sprawdź kolizje z platformami
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.on_ground = True
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0

        # Granice ekranu
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))

    def _check_other_collisions(self, hazards, collectibles, keys):
        # Kolizje z przeszkodami
        if not self.invincible:
            if pygame.sprite.spritecollideany(self, hazards):
                return "hit"

        # Kolizje z przedmiotami
        for collectible in collectibles[:]:
            if self.rect.colliderect(collectible.rect):
                collectible_type = collectible.type
                collectibles.remove(collectible)
                if collectible_type == "double_jump":
                    self.has_double_jump = True
                elif collectible_type == "shield":
                    self.invincible = True
                    self.invincible_timer = 600  # 10 sekund
                self.play_sfx(f"collect_{collectible_type}")
                return collectible_type

        # Kolizje z kluczami
        for key in keys[:]:
            if self.rect.colliderect(key.rect):
                keys.remove(key)
                self.play_sfx("collect_key")
                return "key_collected"

        # Sprawdź, czy spadł poza ekran
        if self.rect.y > SCREEN_HEIGHT:
            return "fell"

        return None

    # Aktualizuje efekty wizualne, takie jak pulsowanie i tarcza
    def _update_effects(self, time_scale=1.0):
        self.pulse_effect = (self.pulse_effect + 0.1 * time_scale) % (2 * math.pi)
        if self.invincible:
            self.invincible_timer -= time_scale
            if self.invincible_timer <= 0:
                self.invincible = False
        self.image.fill(self.color)

    # Klasa reprezentująca echa gracza
    def draw(self, surface):
        # Pulsująca poświata
        pulse_radius = self.rect.width // 2 + int(5 * math.sin(self.pulse_effect))
        glow_color = (*self.color, 50)

        # Użyj osobnej powierzchni dla poświaty, aby poprawnie obsłużyć alfę
        glow_surface = pygame.Surface((pulse_radius * 2, pulse_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, glow_color, (pulse_radius, pulse_radius), pulse_radius)
        surface.blit(glow_surface, (self.rect.centerx - pulse_radius, self.rect.centery - pulse_radius))

        # Ustaw przezroczystość dla echa
        if self.is_echo:
            self.image.set_alpha(100)
        else:
            self.image.set_alpha(255)

        # Tarcza ma własny, wyraźniejszy efekt
        if self.invincible:
            shield_radius = self.rect.width // 2 + 8
            shield_alpha = 100 + int(50 * math.sin(self.animation_timer * 2))
            shield_color = (*ORANGE, shield_alpha)
            pygame.draw.circle(surface, shield_color, self.rect.center, shield_radius, 2)

        # Rysowanie gracza
        surface.blit(self.image, self.rect)

# Klasy elementów poziomu
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, moving=False, move_range=100):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

        self._create_texture()

        # Ruchome platformy
        self.moving = moving
        self.move_range = move_range
        self.start_x = x
        self.direction = 1
        self.speed = 2

    def _create_texture(self):
        """Tworzy teksturę pixel art dla platformy z większymi 'pikselami' i różnymi odcieniami."""
        tile_size = 24  # Zwiększony rozmiar "piksela"
        dirt_palette = [
            (87, 56, 40),   # Ciemny brąz
            (70, 45, 32),   # Bardzo ciemny brąz
            (105, 67, 48),  # Jaśniejszy brąz
            (95, 60, 42)    # Inny odcień
        ]

        # Rysuj większe "piksele" o różnych odcieniach
        for x_pos in range(0, self.rect.width, tile_size):
            for y_pos in range(0, self.rect.height, tile_size):
                tile_color = random.choice(dirt_palette)
                pygame.draw.rect(self.image, tile_color, (x_pos, y_pos, tile_size, tile_size))

        # Dodaj trochę "szumu" dla lepszej tekstury
        for _ in range(int(self.rect.width * self.rect.height / 25)):
            px = random.randint(0, self.rect.width - 1)
            py = random.randint(0, self.rect.height - 1)
            base_pixel_color = self.image.get_at((px, py))
            color_mod = random.randint(-15, 15)
            dot_color = tuple(max(0, min(255, c + color_mod)) for c in base_pixel_color)
            self.image.set_at((px, py), dot_color)

        # Dodaj warstwę trawy na wierzchu
        grass_height = 5
        grass_color = (60, 140, 70)
        pygame.draw.rect(self.image, grass_color, (0, 0, self.rect.width, grass_height))
        for i in range(self.rect.width // 2):
            px = random.randint(0, self.rect.width - 1)
            py = random.randint(0, grass_height - 1)
            pygame.draw.rect(self.image, (grass_color[0]+20, grass_color[1]+20, grass_color[2]+20), (px, py, 1, 1))

    # Aktualizacja pozycji platformy, jeśli jest ruchoma
    def update(self):
        if self.moving:
            self.rect.x += self.speed * self.direction
            if abs(self.rect.x - self.start_x) > self.move_range:
                self.direction *= -1
    # Rysowanie platformy na powierzchni
    def draw(self, surface):
        surface.blit(self.image, self.rect)

# Klasa reprezentująca platformę czasową
class TemporalPlatform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, initial_state='solid', solid_time=180, phased_time=120):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)

        # Inicjalizacja stanu platformy
        self.state = initial_state
        self.solid_duration = solid_time
        self.phased_duration = phased_time
        self.timer = 0

        # Tekstury dla różnych stanów
        self.solid_texture = self._create_texture((40, 87, 56), (70, 140, 90))
        self.phased_texture = self._create_texture((30, 50, 90), (60, 90, 140))

    def _create_texture(self, base_color, top_color):
        """Tworzy teksturę na podstawie podanych kolorów z większymi 'pikselami'."""
        texture_surface = pygame.Surface(self.rect.size)
        tile_size = 24

        # Stwórz paletę na podstawie koloru bazowego
        color_palette = [
            base_color,
            tuple(max(0, min(255, c - 15)) for c in base_color),
            tuple(max(0, min(255, c + 15)) for c in base_color)
        ]

        # Rysuj większe "piksele" o różnych odcieniach
        for x_pos in range(0, self.rect.width, tile_size):
            for y_pos in range(0, self.rect.height, tile_size):
                tile_color = random.choice(color_palette)
                pygame.draw.rect(texture_surface, tile_color, (x_pos, y_pos, tile_size, tile_size))

        # Dodaj "szum"
        for _ in range(int(self.rect.width * self.rect.height / 25)):
            px = random.randint(0, self.rect.width - 1)
            py = random.randint(0, self.rect.height - 1)
            base_pixel_color = texture_surface.get_at((px, py))
            mod = random.randint(-10, 10)
            dot_color = tuple(max(0, min(255, c + mod)) for c in base_pixel_color)
            texture_surface.set_at((px, py), dot_color)

        # Dodaj warstwę trawy na wierzchu
        top_height = 5
        pygame.draw.rect(texture_surface, top_color, (0, 0, self.rect.width, top_height))
        return texture_surface

    # Aktualizacja stanu platformy
    def update(self):
        self.timer += 1
        if self.state == 'solid':
            if self.timer > self.solid_duration:
                self.state = 'phased'
                self.timer = 0
        else: # self.state == 'phased'
            if self.timer > self.phased_duration:
                self.state = 'solid'
                self.timer = 0

    # Rysowanie platformy na powierzchni
    def draw(self, surface):
        self.image.fill((0, 0, 0, 0))

        if self.state == 'solid':
            progress = self.timer / self.solid_duration
            alpha = int(255 - 155 * progress)
            self.solid_texture.set_alpha(alpha)
            self.image.blit(self.solid_texture, (0, 0))
        else:
            progress = self.timer / self.phased_duration
            alpha = int(30 + 70 * progress)
            self.phased_texture.set_alpha(alpha)
            self.image.blit(self.phased_texture, (0, 0))

        # Rysowanie platformy z przezroczystością
        surface.blit(self.image, self.rect)
        pygame.draw.rect(surface, (*CYAN, 50), self.rect, 1)


class TimeDilationZone(pygame.sprite.Sprite):
    """Strefa, w której lokalny czas gracza płynie z połową prędkości."""

    def __init__(self, x, y, width, height, factor=0.5):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.factor = max(0.1, min(1.0, float(factor)))
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.image.fill((*PURPLE, 65))
        pygame.draw.rect(self.image, (*CYAN, 150), self.image.get_rect(), 2)

    def update(self):
        pass

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# Czytelna nazwa alternatywna dla edytora i starszych eksperymentów.
SlowMotionZone = TimeDilationZone


class ParadoxSwitch(pygame.sprite.Sprite):
    """Przełącznik, którego nie może aktywować zwykły gracz."""

    def __init__(self, x, y, width=48, height=16):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.pressed = False
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self._redraw()

    def _redraw(self):
        self.image.fill((0, 0, 0, 0))
        color = (70, 220, 255) if self.pressed else (210, 60, 220)
        pygame.draw.rect(self.image, color, self.image.get_rect(), border_radius=4)
        pygame.draw.rect(self.image, WHITE, self.image.get_rect(), 2, border_radius=4)

    def activate(self):
        if not self.pressed:
            self.pressed = True
            self._redraw()
            return True
        return False

    def update(self):
        pass

    def draw(self, surface):
        surface.blit(self.image, self.rect)


ParadoxButton = ParadoxSwitch


class ParadoxDoor(Platform):
    """Przejście materializujące się jako przeszkoda do czasu aktywacji Echo."""

    def __init__(self, x, y, width, height, initially_locked=True):
        super().__init__(x, y, width, height, moving=False)
        self.locked = bool(initially_locked)
        self.image.set_alpha(210)

    def open(self):
        self.locked = False
        self.image.set_alpha(0)

    def draw(self, surface):
        if self.locked:
            super().draw(surface)


# Klasa reprezentująca niebezpieczeństwa (np. kolce)
class Hazard(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, hazard_type="spike"):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.type = hazard_type

        # Animacja
        self.animation_timer = random.uniform(0, 2 * math.pi)

    def update(self):
        self.animation_timer += 0.1
        # Efekt pulsowania dla niebezpieczeństw
        pulse = int(200 + 55 * math.sin(self.animation_timer))
        self.image.fill((pulse, 0, 0))

    def draw(self, surface):
        # Rysuj kolce jako trójkąty
        if self.type == "spike":
            points = [
                (self.rect.centerx, self.rect.top),
                (self.rect.left, self.rect.bottom),
                (self.rect.right, self.rect.bottom)
            ]
            pygame.draw.polygon(surface, self.image.get_at((0, 0)), points)
        else:
            surface.blit(self.image, self.rect)

# Klasa reprezentująca przedmioty do zbierania (np. klejnoty, power-upy)
class Collectible(pygame.sprite.Sprite):
    def __init__(self, x, y, collectible_type="gem"):
        super().__init__()
        self.type = collectible_type
        self.size = 30
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA) # Przezroczysta powierzchnia

        # Różne kolory dla różnych typów
        colors = {
            "gem": YELLOW,
            "double_jump": PURPLE,
            "shield": ORANGE
        }
        # Rysowanie kształtu w zależności od typu
        self.color = colors.get(collectible_type, WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

        # Animacja
        self.float_offset = random.uniform(0, 2 * math.pi)
        self.original_y = y
        self.rotation = 0

    def update(self):
        # Efekt unoszenia
        self.float_offset += 0.05
        self.rect.y = self.original_y + int(10 * math.sin(self.float_offset))

        # Rotacja
        self.rotation += 3

    # Rysowanie kształtu w zależności od typu
    def draw(self, surface):
            center = (self.rect.centerx, self.rect.centery)

            # Efekt poświaty
            glow_radius = self.size // 2 + 5
            glow_alpha = 100 + int(50 * math.sin(self.float_offset * 2))
            glow_color = (*self.color, glow_alpha)

            # Użyj osobnej powierzchni dla poświaty, aby poprawnie obsłużyć alfę
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
            surface.blit(glow_surface, (center[0] - glow_radius, center[1] - glow_radius))

            # Rysuj różne kształty dla różnych typów
            if self.type == "gem":
                points = []
                for i in range(5):
                    angle = math.radians(self.rotation + i * 72)
                    outer_point = (center[0] + self.size/2 * math.cos(angle), center[1] + self.size/2 * math.sin(angle))
                    angle += math.radians(36)
                    inner_point = (center[0] + self.size/4 * math.cos(angle), center[1] + self.size/4 * math.sin(angle))
                    points.extend([outer_point, inner_point])
                pygame.draw.polygon(surface, self.color, points)

            # Rysowanie innych typów przedmiotów
            elif self.type == "double_jump":
                pygame.draw.circle(surface, self.color, center, self.size // 3)
                pygame.draw.circle(surface, WHITE, center, self.size // 3, 2)
                angle1 = math.radians(self.rotation)
                angle2 = math.radians(self.rotation + 180)
                y_offset = self.size / 2.5
                pygame.draw.line(surface, self.color, (center[0], center[1] - y_offset), (center[0] + 10 * math.cos(angle1), center[1] - y_offset + 10 * math.sin(angle1)), 3)
                pygame.draw.line(surface, self.color, (center[0], center[1] + y_offset), (center[0] + 10 * math.cos(angle2), center[1] + y_offset + 10 * math.sin(angle2)), 3)

            # Rysowanie tarczy
            elif self.type == "shield":
                pygame.draw.rect(surface, self.color, self.rect, 4, border_radius=5)
                pygame.draw.line(surface, WHITE, self.rect.topleft, self.rect.bottomright, 2)

# Klasa reprezentująca klucz do odblokowania wyjścia
class Key(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.size = 40
        self.image = self._create_image()
        self.rect = self.image.get_rect(center=(x + self.size // 2, y + self.size // 2))

        # Animacja
        self.float_offset = random.uniform(0, 2 * math.pi)
        self.original_y = y

    def _create_image(self):
        """Tworzy obraz klucza w stylu pixel art."""
        surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        key_color = (255, 223, 0)  # Złoty żółty
        darker_key_color = (200, 160, 0)

        # Główka klucza
        pygame.draw.circle(surface, darker_key_color, (self.size // 2, 10), 8)
        pygame.draw.circle(surface, key_color, (self.size // 2, 10), 6)
        pygame.draw.rect(surface, (40, 40, 40), (self.size // 2 - 2, 8, 4, 4)) # Otwór

        # Trzon klucza
        pygame.draw.rect(surface, darker_key_color, (self.size // 2 - 3, 18, 6, 18))
        pygame.draw.rect(surface, key_color, (self.size // 2 - 2, 18, 4, 17))

        # Ząbki klucza
        pygame.draw.rect(surface, darker_key_color, (self.size // 2 + 3, 24, 6, 4))
        pygame.draw.rect(surface, darker_key_color, (self.size // 2 + 3, 32, 8, 4))

        # Lekko obrócony dla lepszego wyglądu
        return pygame.transform.rotate(surface, -45)

    def update(self):
        # Efekt unoszenia się
        self.float_offset += 0.05
        self.rect.y = self.original_y + int(8 * math.sin(self.float_offset))

    def draw(self, surface):
        # Poświata dla lepszej widoczności
        center = self.rect.center
        glow_radius = self.size // 2 + 3
        glow_alpha = 100 + int(50 * math.sin(self.float_offset * 2))
        glow_color = (*YELLOW, glow_alpha)

        # Użyj osobnej powierzchni dla poświaty, aby poprawnie obsłużyć alfę
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (center[0] - glow_radius, center[1] - glow_radius))

        # Rysowanie klucza
        surface.blit(self.image, self.rect)

# Klasa reprezentująca strefę wyjścia
class ExitZone(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 80, 80)
        self.animation_timer = 0
        self.locked = True
        self.key_icon = self._create_key_icon()
        self.portal_particles = []

        # --- Pre-renderowanie statycznej kamiennej struktury ---
        self.gate_structure_surface, self.gate_pos = self._create_gate_structure()

    def _create_key_icon(self):
        """Tworzy małą, prostą ikonę klucza."""
        icon_surf = pygame.Surface((15, 15), pygame.SRCALPHA)
        key_color = YELLOW
        pygame.draw.circle(icon_surf, key_color, (5, 5), 4, 2)
        pygame.draw.line(icon_surf, key_color, (5, 9), (5, 13), 2)
        pygame.draw.line(icon_surf, key_color, (5, 11), (8, 11), 2)
        return icon_surf

    def _create_gate_structure(self):
        """Tworzy dopracowaną, statyczną powierzchnię dla kamiennej bramy."""
        pillar_width = 16  # Użyjmy wielokrotności 8 dla łatwiejszego rysowania bloków
        pillar_height = self.rect.height
        arch_thickness = 24
        arch_rect_width = self.rect.width + 2 * pillar_width
        arch_rect_height = 40

        # Oblicz całkowitą szerokość i wysokość struktury
        total_width = arch_rect_width
        total_height = arch_rect_height + pillar_height

        # Stwórz powierzchnię dla struktury bramy
        structure_surf = pygame.Surface((total_width, total_height), pygame.SRCALPHA)

        # Paleta z predefiniowanymi rolami dla cieniowania
        stone_base = (110, 110, 120)
        stone_shadow = (80, 80, 90)
        stone_highlight = (140, 140, 150)
        stone_dark_outline = (50, 50, 60)
        block_size = 8

        def draw_stone_block(surf, x, y, size):
            """Rysuje pojedynczy kamienny blok z efektem 3D."""
            # Główny kolor
            pygame.draw.rect(surf, stone_base, (x, y, size, size))
            # Podświetlenie (góra i lewo)
            pygame.draw.line(surf, stone_highlight, (x, y), (x + size - 1, y))
            pygame.draw.line(surf, stone_highlight, (x, y), (x, y + size - 1))
            # Cień (dół i prawo)
            pygame.draw.line(surf, stone_shadow, (x, y + size - 1), (x + size - 1, y + size - 1))
            pygame.draw.line(surf, stone_shadow, (x + size - 1, y), (x + size - 1, y + size - 1))
            # Ciemny kontur
            pygame.draw.rect(surf, stone_dark_outline, (x, y, size, size), 1)

        # --- Rysowanie filarów z bloków ---
        for i in range(2):  # Lewy i prawy filar
            pillar_x = i * (total_width - pillar_width)
            for y_offset in range(arch_rect_height, total_height, block_size):
                for x_offset in range(pillar_x, pillar_x + pillar_width, block_size):
                    draw_stone_block(structure_surf, x_offset, y_offset, block_size)

        # --- Rysowanie łuku z bloków ---
        arch_bounding_rect = pygame.Rect(0, 0, total_width, arch_rect_height)
        h, k = arch_bounding_rect.centerx, arch_bounding_rect.bottom
        a_outer, b_outer = arch_bounding_rect.width / 2, arch_bounding_rect.height
        a_inner, b_inner = a_outer - arch_thickness, b_outer - arch_thickness

        for x in range(0, total_width, block_size):
            for y in range(0, arch_bounding_rect.bottom, block_size):
                bx, by = x + block_size / 2, y + block_size / 2
                # Sprawdzenie, czy środek bloku znajduje się wewnątrz elipsy tworzącej łuk
                if ((bx - h)**2 / a_outer**2 + (by - k)**2 / b_outer**2 <= 1 and
                    (bx - h)**2 / a_inner**2 + (by - k)**2 / b_inner**2 >= 1):
                    draw_stone_block(structure_surf, x, y, block_size)

        # --- Napis "EXIT" na łuku ---
        exit_text_surf = font_small.render("EXIT", True, (230, 230, 240))
        text_rect = exit_text_surf.get_rect(center=(arch_bounding_rect.centerx, arch_bounding_rect.centery + 8))
        shadow_surf = font_small.render("EXIT", True, (20, 20, 20))
        structure_surf.blit(shadow_surf, (text_rect.x + 2, text_rect.y + 2))
        structure_surf.blit(exit_text_surf, text_rect)

        # Kryształy i runy nadają bramie charakter zamiast płaskiego kamiennego
        # prostokąta. Są częścią wyłącznie warstwy wizualnej.
        for crystal_x in (pillar_width // 2, total_width - pillar_width // 2):
            pygame.draw.polygon(structure_surf, (80, 220, 235),
                                [(crystal_x, arch_rect_height + 18),
                                 (crystal_x + 5, arch_rect_height + 26),
                                 (crystal_x, arch_rect_height + 34),
                                 (crystal_x - 5, arch_rect_height + 26)])
            pygame.draw.line(structure_surf, (210, 255, 255),
                             (crystal_x, arch_rect_height + 20),
                             (crystal_x, arch_rect_height + 30), 2)
        for rune_x in range(pillar_width + 8, total_width - pillar_width, 16):
            pygame.draw.line(structure_surf, (125, 90, 205),
                             (rune_x, 8), (rune_x + 4, 18), 2)

        # --- Pozycja bramy ---
        gate_pos = (self.rect.left - pillar_width, self.rect.top - arch_rect_height)
        return structure_surf, gate_pos

    # Klasa reprezentująca strefę wyjścia z animacją portalu
    def update(self):
        self.animation_timer += 0.1
        if not self.locked:
            # Generuj nowe cząsteczki portalu
            if len(self.portal_particles) < 50:
                p_x = self.rect.centerx + random.uniform(-self.rect.width/3, self.rect.width/3)
                p_y = self.rect.centery + random.uniform(-self.rect.height/3, self.rect.height/3)
                p_radius = random.uniform(1, 5)
                p_lifetime = random.randint(20, 60)
                self.portal_particles.append([p_x, p_y, p_radius, p_lifetime])

            # Aktualizuj istniejące cząsteczki
            for p in self.portal_particles:
                p[3] -= 1 # Zmniejsz czas życia
            self.portal_particles = [p for p in self.portal_particles if p[3] > 0]

    def draw(self, surface, remaining_keys=0):
        # --- Rysowanie gotowej, statycznej struktury bramy ---
        surface.blit(self.gate_structure_surface, self.gate_pos)

        # --- Rysowanie ramy portalu i efektów wewnątrz bramy ---
        frame_color = (80, 80, 90)
        frame_thickness = 5

        if self.locked:
            # Rysuj solidną, nieaktywną ramę
            inner_rect = self.rect.inflate(-frame_thickness * 2, -frame_thickness * 2)
            pygame.draw.rect(surface, (20, 20, 30), inner_rect) # Ciemne tło wewnątrz
            pygame.draw.rect(surface, (75, 65, 95), self.rect, frame_thickness, border_radius=6)
            pygame.draw.line(surface, (170, 70, 105), self.rect.topleft, self.rect.bottomright, 2)

            # Wyświetl ikonę klucza i liczbę pozostałych
            icon_pos_x = self.rect.centerx - 25
            icon_pos_y = self.rect.centery - 8
            surface.blit(self.key_icon, (icon_pos_x, icon_pos_y))

            # Wyświetl liczbę pozostałych kluczy
            keys_text = font_medium.render(f"x {remaining_keys}", True, WHITE)
            text_rect = keys_text.get_rect(midleft=(icon_pos_x + 20, self.rect.centery))
            surface.blit(keys_text, text_rect)
            pygame.draw.circle(surface, (220, 80, 105), (self.rect.centerx, self.rect.bottom - 12), 3)
        else:
            # Rysuj aktywną ramę i wirujący portal
            active_frame_color = (150, 150, 180)
            inner_rect = self.rect.inflate(-frame_thickness * 2, -frame_thickness * 2)
            glow = pygame.Surface((self.rect.width + 32, self.rect.height + 32), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (60, 220, 255, 45), glow.get_rect(), 8)
            surface.blit(glow, (self.rect.x - 16, self.rect.y - 16))
            pygame.draw.rect(surface, (8, 12, 32), inner_rect, border_radius=8)
            pygame.draw.rect(surface, active_frame_color, self.rect, frame_thickness, border_radius=7)
            pygame.draw.arc(surface, CYAN, inner_rect.inflate(-8, -4), self.animation_timer,
                            self.animation_timer + math.pi * 1.35, 3)
            pygame.draw.arc(surface, PURPLE, inner_rect.inflate(-14, -10),
                            -self.animation_timer, -self.animation_timer + math.pi * 1.4, 3)

            # Rysuj cząsteczki portalu
            for x, y, radius, lifetime in self.portal_particles:
                alpha = int(255 * (lifetime / 60))
                color = (*CYAN, alpha)
                temp_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, color, (radius, radius), radius)
                surface.blit(temp_surf, (x - radius, y - radius), special_flags=pygame.BLEND_RGBA_ADD)
