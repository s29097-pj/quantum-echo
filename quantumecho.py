# Quantum Echo - Manipuluj Czasem!
# Gra platformowa z elementami manipulacji czasem, pixel art i efektami wizualnymi

import pygame
import json
import math
import random
from enum import Enum
from collections import deque
import os

# Inicjalizacja
pygame.init()
pygame.mixer.init()

# Stałe
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60
GRAVITY = 0.8
PLAYER_SPEED = 5
JUMP_FORCE = -15

# Kolory
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (100, 149, 237)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (147, 0, 211)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)


# Stany gry
class GameState(Enum):
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    LEVEL_COMPLETE = 4
    GAME_OVER = 5
    INSTRUCTIONS = 6
    LEVEL_SELECT = 7
    GAME_COMPLETE = 8
    RANKING = 9
    TRAINING_COMPLETE = 10


# Inicjalizacja ekranu
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Quantum Echo - Manipuluj Czasem!")
clock = pygame.time.Clock()

# Ścieżka do czcionki
# Zakładam, że pełna nazwa pliku to 'VT323-Regular.ttf'
FONT_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'VT323-Regular.ttf')

# Czcionki w stylu pixel art
try:
    # Rozmiary dla czcionki VT323, można je dostosować w razie potrzeby
    font_small = pygame.font.Font(FONT_PATH, 24)
    font_medium = pygame.font.Font(FONT_PATH, 40)
    font_large = pygame.font.Font(FONT_PATH, 80)
except pygame.error:
    print(f"Błąd: Nie można wczytać czcionki z '{FONT_PATH}'. Używam czcionki domyślnej.")
    # Zastępcze czcionki, jeśli plik nie zostanie znaleziony
    font_small = pygame.font.Font(None, 24)
    font_medium = pygame.font.Font(None, 36)
    font_large = pygame.font.Font(None, 72)

# Klasa do generowania tła z gwiazdami
class Starfield:
    def __init__(self, num_stars, width, height):
        self.stars = []
        for _ in range(num_stars):
            x = random.randint(0, width)
            y = random.randint(0, height)
            speed = random.uniform(0.1, 1.5)
            self.stars.append([x, y, speed])
        self.width = width

    # Aktualizacja pozycji gwiazd z efektem paralaksy
    def update(self, player_vel_x):
        for star in self.stars:
            star[0] -= star[2] * (player_vel_x * 0.1 + 1) # Efekt paralaksy
            if star[0] < 0:
                star[0] = self.width
                star[1] = random.randint(0, SCREEN_HEIGHT)

    # Rysowanie gwiazd na powierzchni
    def draw(self, surface):
        for x, y, speed in self.stars:
            size = int(speed * 1.5)
            brightness = int(speed * 150)
            color = (brightness, brightness, brightness)
            pygame.draw.circle(surface, color, (int(x), int(y)), size)

# Klasa do generowania unikalnego tła dla każdego poziomu
class LevelBackground:
    """Generuje tło w stylu pixel art z pastelowym niebem, chmurami i migoczącymi gwiazdami."""
    def __init__(self, level_index, width, height):
        self.width = width
        self.height = height
        self.clouds = []
        self.stars = []

        # Predefiniowane pastelowe palety kolorów (niebo, chmura, gwiazda)
        # Każdy poziom otrzyma unikalną, ale stałą kombinację kolorów.
        palettes = [
            {'sky': (48, 33, 55), 'cloud': (80, 53, 85), 'star': (227, 220, 168)},    # Zmierzch fioletu
            {'sky': (13, 27, 68), 'cloud': (29, 52, 90), 'star': (210, 220, 240)},    # Głębia granatu
            {'sky': (60, 8, 30), 'cloud': (90, 28, 55), 'star': (240, 210, 210)},    # Kosmiczna czerwień
            {'sky': (8, 45, 50), 'cloud': (20, 70, 75), 'star': (200, 240, 230)},    # Turkusowa noc
        ]
        # Paleta dla tego poziomu (zawija się, jeśli jest więcej poziomów niż palet)
        palette = palettes[level_index % len(palettes)]
        self.sky_color = palette['sky']
        self.cloud_color = palette['cloud']
        self.star_color = palette['star']

        # Powierzchnia tła z jednolitym kolorem nieba
        self.background_surface = pygame.Surface((width, height))
        self.background_surface.fill(self.sky_color)

        # Generowanie chmur
        for _ in range(random.randint(5, 10)):
            self.clouds.append(self._create_cloud())

        # Generowanie gwiazd
        for _ in range(150):
            self.stars.append({
                'pos': (random.randint(0, width), random.randint(0, height)),
                'alpha': 0,
                'fade_speed': random.uniform(0.2, 0.8),
                'state': 'IDLE',
                'delay': random.randint(0, 500) # Opóźnienie przed pierwszym pojawieniem się
            })

    # Tworzy pojedynczą chmurę w stylu pixel art
    def _create_cloud(self):
        # Rysuj na małej powierzchni, aby uzyskać efekt pixel art po przeskalowaniu
        cloud_width = random.randint(20, 40)
        cloud_height = random.randint(10, 20)
        base_surf = pygame.Surface((cloud_width, cloud_height), pygame.SRCALPHA)

        # Chmura składa się z kilku nałożonych na siebie kół
        for _ in range(random.randint(4, 7)):
            r = random.randint(int(cloud_height/3), int(cloud_height/2))
            x = random.randint(r, cloud_width - r)
            y = random.randint(r, cloud_height - r)
            # Użyj koloru chmury z lekką wariacją jasności
            color = (
                min(255, self.cloud_color[0] + random.randint(-10, 10)),
                min(255, self.cloud_color[1] + random.randint(-10, 10)),
                min(255, self.cloud_color[2] + random.randint(-10, 10))
            )
            pygame.draw.circle(base_surf, color, (x, y), r)

        # Skaluj powierzchnię 3x bez wygładzania, aby uzyskać ostry, pixelowy wygląd
        scaled_surf = pygame.transform.scale(base_surf, (cloud_width * 3, cloud_height * 3))

        return {
            # Użyj powierzchni chmury z przeskalowanym rozmiarem
            'surface': scaled_surf,
            # Losowa pozycja początkowa chmury
            'pos': [random.randint(0, self.width), random.randint(0, int(self.height * 0.6))],
            # Losowa prędkość ruchu chmury
            'speed': random.uniform(0.2, 0.6)
        }

    def update(self, player_vel_x):
        # Aktualizuj pozycje chmur z efektem paralaksy
        parallax_factor = player_vel_x * 0.05
        # Przesuwaj chmury w lewo, z uwzględnieniem efektu paralaksy
        for cloud in self.clouds:
            cloud['pos'][0] -= (cloud['speed'] + parallax_factor)
            if cloud['pos'][0] < -cloud['surface'].get_width():
                cloud['pos'][0] = self.width

        # Aktualizuj stan gwiazd (migotanie)
        # Przechodzimy przez każdą gwiazdę i aktualizujemy jej stan
        for star in self.stars:
            if star['state'] == 'IDLE':
                star['delay'] -= 1
                if star['delay'] <= 0:
                    star['state'] = 'FADING_IN'
            # Zarządzanie stanami migotania gwiazd
            elif star['state'] == 'FADING_IN':
                star['alpha'] += star['fade_speed']
                if star['alpha'] >= 255:
                    star['alpha'] = 255
                    star['state'] = 'FADING_OUT'
            # Przechodzenie do stanu zanikania
            elif star['state'] == 'FADING_OUT':
                star['alpha'] -= star['fade_speed']
                if star['alpha'] <= 0:
                    star['alpha'] = 0
                    star['state'] = 'IDLE'
                    star['delay'] = random.randint(200, 800) # Czas do następnego mignięcia

    def draw(self, surface):
        # Narysuj jednolite tło nieba
        surface.blit(self.background_surface, (0, 0))

        # Narysuj gwiazdy
        for star in self.stars:
            if star['alpha'] > 0:
                # Użyj koloru gwiazdy z aktualną przezroczystością
                color = (*self.star_color, star['alpha'])
                # Stwórz tymczasową, małą powierzchnię dla pojedynczej gwiazdy
                star_surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                star_surf.fill(color)
                # Narysuj gwiazdę na powierzchni
                surface.blit(star_surf, star['pos'])

        # Narysuj chmury
        for cloud in self.clouds:
            surface.blit(cloud['surface'], cloud['pos'])


# System cząsteczek dla efektów wizualnych
class Particle:
    def __init__(self, x, y, color, velocity, lifetime): # Inicjalizacja cząsteczki
        self.x = x
        self.y = y
        self.color = color # Kolor cząsteczki
        self.vx, self.vy = velocity # Prędkość cząsteczki
        self.lifetime = lifetime # Czas życia cząsteczki
        self.max_lifetime = lifetime # Maksymalny czas życia cząsteczki

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # grawitacja dla cząsteczek
        self.lifetime -= 1 # Zmniejsz czas życia cząsteczki

    def draw(self, surface):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime)) # Oblicz przezroczystość
            size = int(3 * (self.lifetime / self.max_lifetime)) # Oblicz rozmiar cząsteczki
            if size > 0: # Upewnij się, że rozmiar jest większy niż 0
                # Ustaw kolor z przezroczystością
                pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), size)

# System cząsteczek do efektów wybuchów i śladów
class ParticleSystem:
    def __init__(self): # Inicjalizacja systemu cząsteczek
        self.particles = [] # Lista cząsteczek

    # Dodaje wybuch cząsteczek w określonym miejscu
    def add_burst(self, x, y, color, count=20): # Dodaje wybuch cząsteczek
        for _ in range(count): # Dla każdej cząsteczki w wybuchu
            angle = random.uniform(0, 2 * math.pi) # Losowy kąt
            speed = random.uniform(1, 5) # Losowa prędkość
            vx = math.cos(angle) * speed # Oblicz prędkość w poziomie
            vy = math.sin(angle) * speed # Oblicz prędkość w pionie
            lifetime = random.randint(20, 40) # Losowy czas życia cząsteczki
            self.particles.append(Particle(x, y, color, (vx, vy), lifetime)) # Dodaj cząsteczkę do systemu

    # Emituje pojedynczą cząsteczkę do efektu śladu
    def emit_trail(self, x, y, color):
        vx = random.uniform(-0.5, 0.5) # Losowa prędkość w poziomie
        vy = random.uniform(0.5, 1.5) # Losowa prędkość w pionie
        lifetime = random.randint(15, 30) # Losowy czas życia cząsteczki
        self.particles.append(Particle(x, y, color, (vx, vy), lifetime)) # Dodaj cząsteczkę do systemu

    # Aktualizuje wszystkie cząsteczki w systemie
    def update(self):
        self.particles = [p for p in self.particles if p.lifetime > 0] # Usuń cząsteczki, które wygasły
        for particle in self.particles: # Dla każdej cząsteczki w systemie
            particle.update() # Zaktualizuj pozycję i czas życia cząsteczki

    def draw(self, surface): # Rysuje wszystkie cząsteczki na powierzchni
        for particle in self.particles: # Dla każdej cząsteczki w systemie
            particle.draw(surface) # Rysuj cząsteczkę na powierzchni

# Klasa gracza z systemem echa i fizyką
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, is_echo=False):
        super().__init__()
        self.image = pygame.Surface((40, 40))
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

    # Aktualizacja gracza
    def update(self, platforms, hazards, collectibles, keys, history_pos=None):
        collision_result = None

        # Sprawdź kolizje tylko dla echa, jeśli jest aktywne
        if self.is_echo:
            if history_pos:
                self.rect.topleft = history_pos
        else:
            # Zastosuj fizykę i sprawdź kolizje tylko dla gracza
            self._apply_physics(platforms)
            collision_result = self._check_other_collisions(hazards, collectibles, keys)

        # Aktualizuj efekty wizualne dla obu
        self._update_effects()

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
            return True
        elif self.has_double_jump and not self.double_jump_used:
            self.vel_y = JUMP_FORCE * 0.8  # Drugi skok jest nieco słabszy
            self.double_jump_used = True
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
                return collectible_type

        # Kolizje z kluczami
        for key in keys[:]:
            if self.rect.colliderect(key.rect):
                keys.remove(key)
                return "key_collected"

        # Sprawdź, czy spadł poza ekran
        if self.rect.y > SCREEN_HEIGHT:
            return "fell"

        return None

    # Aktualizuje efekty wizualne, takie jak pulsowanie i tarcza
    def _update_effects(self):
        self.pulse_effect = (self.pulse_effect + 0.1) % (2 * math.pi)
        if self.invincible:
            self.invincible_timer -= 1
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
            pygame.draw.rect(surface, frame_color, self.rect, frame_thickness, border_radius=3)

            # Wyświetl ikonę klucza i liczbę pozostałych
            icon_pos_x = self.rect.centerx - 25
            icon_pos_y = self.rect.centery - 8
            surface.blit(self.key_icon, (icon_pos_x, icon_pos_y))

            # Wyświetl liczbę pozostałych kluczy
            keys_text = font_medium.render(f"x {remaining_keys}", True, WHITE)
            text_rect = keys_text.get_rect(midleft=(icon_pos_x + 20, self.rect.centery))
            surface.blit(keys_text, text_rect)
        else:
            # Rysuj aktywną ramę i wirujący portal
            active_frame_color = (150, 150, 180)
            inner_rect = self.rect.inflate(-frame_thickness * 2, -frame_thickness * 2)
            pygame.draw.rect(surface, BLACK, inner_rect) # Czarne tło dla portalu
            pygame.draw.rect(surface, active_frame_color, self.rect, frame_thickness, border_radius=3)

            # Rysuj cząsteczki portalu
            for x, y, radius, lifetime in self.portal_particles:
                alpha = int(255 * (lifetime / 60))
                color = (*CYAN, alpha)
                temp_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, color, (radius, radius), radius)
                surface.blit(temp_surf, (x - radius, y - radius), special_flags=pygame.BLEND_RGBA_ADD)

# Klasa reprezentująca poziom gry
class Level:
    def __init__(self, level_data, level_index):
        self.platforms = pygame.sprite.Group()
        self.temporal_platforms = pygame.sprite.Group()
        self.hazards = pygame.sprite.Group()
        self.collectibles = []
        self.keys = []  # Zamiast przycisków
        self.exit_zone = None

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
                                 platform_data.get('initial_state', 'solid'))
            self.temporal_platforms.add(p)

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
        self.exit_zone.locked = bool(self.keys)

    # Jeśli nie ma kluczy, odblokuj wyjście
    def get_solid_platforms(self):
        solid_group = pygame.sprite.Group()
        solid_group.add(self.platforms.sprites())
        for p in self.temporal_platforms:
            if p.state == 'solid':
                solid_group.add(p)
        return solid_group

    # Aktualizacja stanu poziomu
    def update(self, player_vel_x):
        self.background.update(player_vel_x)
        self.platforms.update()
        self.temporal_platforms.update()
        self.hazards.update()
        for collectible in self.collectibles:
            collectible.update()
        for key in self.keys:
            key.update()
        self.exit_zone.update()

        # Odblokuj wyjście, jeśli wszystkie klucze zostały zebrane
        if self.exit_zone.locked and not self.keys:
            self.exit_zone.locked = False

    # Sprawdź, czy gracz zebrał wszystkie przedmioty
    def draw(self, surface):
        self.background.draw(surface)
        for platform in self.platforms:
            platform.draw(surface)
        for platform in self.temporal_platforms:
            platform.draw(surface)
        for hazard in self.hazards:
            hazard.draw(surface)
        for collectible in self.collectibles:
            collectible.draw(surface)
        for key in self.keys:
            key.draw(surface)
        self.exit_zone.draw(surface)

# Funkcja pomocnicza do rysowania tekstu na powierzchni
def draw_text(text, font, color, surface, x, y, center=False):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)

# Funkcja do ładowania poziomu z pliku JSON
def load_level(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Błąd: Nie można znaleźć pliku poziomu: {filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"Błąd: Niepoprawny format pliku JSON '{filename}': {e}")
        return None
    except Exception as e:
        print(f"Niespodziewany błąd podczas ładowania poziomu '{filename}': {e}")
        return None

# Funkcje do ładowania i zapisywania rankingu w formacie JSON
def load_ranking(filename):
    """Wczytuje ranking z pliku JSON."""
    try:
        with open(filename, 'r') as f:
            # Sortuj od razu po wczytaniu
            data = json.load(f)
            return sorted(data, key=lambda x: x['score'], reverse=True)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Funkcja do zapisywania rankingu do pliku JSON
def save_ranking(filename, ranking_data):
    """Zapisuje posortowaną listę 10 najlepszych wyników do pliku JSON."""
    sorted_ranking = sorted(ranking_data, key=lambda x: x['score'], reverse=True)
    with open(filename, 'w') as f:
        json.dump(sorted_ranking[:7], f, indent=4)

# Rysowanie HUD (Heads-Up Display)
def draw_hud(surface, player, collectibles_left, second_life_available, level_time, swap_cooldown):
    # Tło HUD
    hud_surface = pygame.Surface((320, 130), pygame.SRCALPHA)
    hud_surface.fill((0, 0, 0, 180))
    pygame.draw.rect(hud_surface, WHITE, hud_surface.get_rect(), 2)

    # Informacje o graczu
    draw_text(f"Klejnoty: {collectibles_left}", font_small, WHITE, hud_surface, 10, 10)

    # Power-upy
    if player.has_double_jump:
        draw_text("Podwójny skok: TAK", font_small, GREEN, hud_surface, 10, 35)

    # Tarcza
    if player.invincible:
        shield_time = player.invincible_timer // 60
        draw_text(f"Tarcza: {shield_time}s", font_small, YELLOW, hud_surface, 10, 60)

    # Status drugiego życia
    life_color = GREEN if second_life_available else RED
    life_text = "DOSTĘPNE" if second_life_available else "ZUŻYTE"
    draw_text(f"Drugie życie: {life_text}", font_small, life_color, hud_surface, 160, 10)

    # Czas
    seconds = level_time // 60
    draw_text(f"Czas: {seconds}s", font_small, WHITE, hud_surface, 160, 35)

    # Status Zamiany Kwantowej
    if swap_cooldown > 0:
        cooldown_sec = (swap_cooldown // 60) + 1
        draw_text(f"Zamiana [Q]: {cooldown_sec}s", font_small, GRAY, hud_surface, 10, 85)
    else:
        draw_text("Zamiana [Q]: GOTOWA", font_small, PURPLE, hud_surface, 10, 85)

    # Liczba Zamian
    surface.blit(hud_surface, (10, 10))

# Rysowanie tekstu w stylu pixel art (bez antyaliasingu) z cieniem
def draw_pixel_text(surface, text, font, center_pos, text_color, shadow_color, shadow_offset=(3, 3)):
    # Renderuj tekst bez wygładzania krawędzi (antyaliasingu)
    text_surf = font.render(text, False, text_color)
    shadow_surf = font.render(text, False, shadow_color)

    # Ustawienie pozycji tekstu i cienia
    text_rect = text_surf.get_rect(center=center_pos)
    shadow_rect = shadow_surf.get_rect(center=(center_pos[0] + shadow_offset[0], center_pos[1] + shadow_offset[1]))

    # Rysowanie cienia i tekstu na powierzchni
    surface.blit(shadow_surf, shadow_rect)
    surface.blit(text_surf, text_rect)
    return text_rect


# Główna funkcja gry
def main():
    # Kolejność poziomów i plik rankingu
    LEVEL_ORDER = [
        "levels/level1.json",
        "levels/level2.json",
        "levels/level3.json",
        "levels/level4.json"
    ]
    RANKING_FILE = "ranking.json"

    # Zmienne gry
    state = GameState.MENU
    current_level_index = -1
    current_level = None
    current_level_filename = None
    player = None
    echo = None
    particle_system = ParticleSystem()
    starfield = Starfield(200, SCREEN_WIDTH, SCREEN_HEIGHT) # Inicjalizacja tła gwiazd
    is_training_mode = False # Tryb treningowy (dla poziomów 1-4)

    # Statystyki całej gry
    level_time = 0
    score = 0
    deaths = 0
    restart_penalty = 0
    swap_count = 0
    total_swap_count = 0

    # Ranking i wprowadzanie nazwy gracza
    ranking = load_ranking(RANKING_FILE)
    player_name = ""
    input_active = False

    # Zmienne dla systemu drugiego życia
    is_on_second_life = False
    player_history = deque()
    ECHO_DELAY_FRAMES = 600

    # Zmienne dla Zamiany Kwantowej
    swap_cooldown = 0
    SWAP_COOLDOWN_FRAMES = 180

    # Inicjalizacja Pygame
    def start_level(level_filename, level_idx, training=False):
        nonlocal current_level, player, echo, is_on_second_life, player_history, level_time, state, swap_cooldown, current_level_filename, is_training_mode, swap_count
        script_dir = os.path.dirname(__file__)
        level_path = os.path.join(script_dir, level_filename)
        level_data = load_level(level_path)
        is_training_mode = training

        # Sprawdź, czy dane poziomu zostały poprawnie wczytane
        if level_data:
            current_level_filename = level_filename
            current_level = Level(level_data, level_idx)
            player = Player(current_level.start_pos[0], current_level.start_pos[1])
            echo = Player(current_level.start_pos[0], current_level.start_pos[1], is_echo=True)
            is_on_second_life = False
            player_history.clear()
            level_time = 0
            swap_cooldown = 0
            swap_count = 0
            state = GameState.PLAYING
        else:
            state = GameState.MENU
            nonlocal current_level_index
            current_level_index = -1

    running = True
    while running:
        # --- Obsługa zdarzeń ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Obsługa zdarzeń klawiatury
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == GameState.PLAYING:
                        state = GameState.PAUSED
                    elif state in [GameState.PAUSED, GameState.INSTRUCTIONS, GameState.LEVEL_SELECT, GameState.GAME_OVER, GameState.RANKING, GameState.LEVEL_COMPLETE, GameState.TRAINING_COMPLETE]:
                        state = GameState.MENU
                    elif state == GameState.MENU:
                        running = False

                # Jeśli wprowadzanie nazwy gracza jest aktywne
                elif event.key == pygame.K_r and state == GameState.GAME_OVER:
                    if current_level_filename:
                        if not is_training_mode:
                            restart_penalty += 50
                        start_level(current_level_filename, current_level_index, training=is_training_mode)

                # Jeśli wprowadzanie nazwy gracza jest aktywne
                elif event.key == pygame.K_SPACE:
                    if state == GameState.MENU:
                        current_level_index = 0
                        score, deaths, restart_penalty, total_swap_count = 0, 0, 0, 0
                        start_level(LEVEL_ORDER[current_level_index], current_level_index, training=False)
                    elif state == GameState.PAUSED:
                        state = GameState.PLAYING
                    elif state == GameState.LEVEL_COMPLETE:
                        current_level_index += 1
                        if current_level_index < len(LEVEL_ORDER):
                            start_level(LEVEL_ORDER[current_level_index], current_level_index, training=False)
                        else:
                            state = GameState.GAME_COMPLETE
                            input_active = True
                    elif state == GameState.PLAYING and player:
                        player.jump()

                # Obsługa innych klawiszy
                elif event.key == pygame.K_q and state == GameState.PLAYING:
                    if player and echo and swap_cooldown == 0 and not is_on_second_life:
                        player.rect, echo.rect = echo.rect, player.rect
                        swap_cooldown = SWAP_COOLDOWN_FRAMES
                        swap_count += 1
                        particle_system.add_burst(player.rect.centerx, player.rect.centery, PURPLE, 40)
                        particle_system.add_burst(echo.rect.centerx, echo.rect.centery, PURPLE, 40)

                # Obsługa przełączania stanu gry
                elif event.key == pygame.K_i and state == GameState.MENU:
                    state = GameState.INSTRUCTIONS

                elif event.key == pygame.K_l and state == GameState.MENU:
                    state = GameState.LEVEL_SELECT

                elif event.key == pygame.K_r and state == GameState.MENU:
                    state = GameState.RANKING

                # Obsługa stanu pauzy
                elif state == GameState.LEVEL_SELECT:
                    new_index = -1
                    if event.key == pygame.K_1: new_index = 0
                    elif event.key == pygame.K_2: new_index = 1
                    elif event.key == pygame.K_3: new_index = 2
                    elif event.key == pygame.K_4: new_index = 3
                    if new_index != -1:
                        current_level_index = new_index
                        start_level(LEVEL_ORDER[current_level_index], current_level_index, training=True)

                # Obsługa stanu instrukcji
                elif state == GameState.TRAINING_COMPLETE:
                    if event.key == pygame.K_l:
                        state = GameState.LEVEL_SELECT
                    elif event.key == pygame.K_ESCAPE:
                        state = GameState.MENU

                # Obsługa wprowadzania nazwy gracza
                elif state == GameState.GAME_COMPLETE and input_active:
                    if event.key == pygame.K_RETURN:
                        if player_name:
                            final_score = score - restart_penalty
                            ranking.append({'name': player_name, 'score': final_score})
                            save_ranking(RANKING_FILE, ranking)
                            input_active = False
                            state = GameState.RANKING
                    elif event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                    elif len(player_name) < 12:
                        player_name += event.unicode

        # --- Aktualizacja logiki gry ---
        player_vel_x_for_parallax = 0
        if state == GameState.PLAYING and player and current_level:
            level_time += 1 # Aktualizuj czas poziomu
            if swap_cooldown > 0: # Zmniejsz czas odnowienia Zamiany Kwantowej
                swap_cooldown -= 1 # Zmniejsz cooldown

            keys = pygame.key.get_pressed() # Pobierz aktualny stan klawiszy
            player.handle_input(keys) # Obsługa wejścia gracza
            player_vel_x_for_parallax = player.vel_x # Przechowuj prędkość gracza dla efektu paralaksy

            solid_platforms = current_level.get_solid_platforms() # Pobierz solidne platformy
            result = player.update(solid_platforms, current_level.hazards, # Aktualizacja gracza
                                               current_level.collectibles, current_level.keys)

            # Sprawdź, czy gracz ma drugie życie
            if not is_on_second_life:
                player_history.append(player.rect.topleft)

            # Sprawdź kolizje i efekty
            if result == "hit" or result == "fell":
                if not is_on_second_life and echo:
                    # Gracz ma drugie życie - przełącza się na Echo
                    is_on_second_life = True
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, CYAN, 50)

                    # Przenieś statusy (power-upy, itp.) do Echa
                    echo.has_double_jump = player.has_double_jump
                    echo.invincible = player.invincible
                    echo.invincible_timer = player.invincible_timer

                    # Echo staje się nowym graczem
                    player, echo = echo, player
                    player.is_echo = False
                    player.color = BLUE
                    player.image.fill(player.color)

                    # Usuń echo, aby zniknęło z ekranu
                    echo = None
                else:
                    # Ostateczna śmierć gracza
                    if not is_training_mode:
                        deaths += 1
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, RED, 30)
                    state = GameState.GAME_OVER

            # Sprawdź, czy gracz zebrał przedmioty
            elif result == "gem":
                if not is_training_mode: score += 100
                particle_system.add_burst(player.rect.centerx, player.rect.centery, YELLOW, 15)

            # Sprawdź, czy gracz zebrał podwójny skok
            elif result == "double_jump":
                if not is_training_mode: score += 50
                particle_system.add_burst(player.rect.centerx, player.rect.centery, PURPLE, 20)

            # Sprawdź, czy gracz ma tarczę
            elif result == "shield":
                particle_system.add_burst(player.rect.centerx, player.rect.centery, ORANGE, 25)

            current_level.update(player_vel_x_for_parallax)

            # Aktualizacja Echa, jeśli istnieje
            if echo:
                history_pos = None
                if len(player_history) > ECHO_DELAY_FRAMES:
                    history_pos = player_history[len(player_history) - ECHO_DELAY_FRAMES - 1]
                echo.update(solid_platforms, [], [], [], history_pos=history_pos)

            particle_system.update()

            # Sprawdź, czy gracz dotarł do strefy wyjścia
            if player.rect.colliderect(current_level.exit_zone.rect) and not current_level.exit_zone.locked:
                            if is_training_mode:
                                state = GameState.TRAINING_COMPLETE
                            else:
                                state = GameState.LEVEL_COMPLETE
                                score += 1000
                                total_swap_count += swap_count
                                particle_system.add_burst(player.rect.centerx, player.rect.centery, GREEN, 100)
        else:
            starfield.update(1)

        # --- Rysowanie ---
        screen.fill(BLACK)

        if state == GameState.PLAYING:
            if current_level: current_level.draw(screen)
            if player: player.draw(screen)
            if echo: echo.draw(screen)
            particle_system.draw(screen)
            gems_left = len([c for c in current_level.collectibles if c.type == "gem"])
            draw_hud(screen, player, gems_left, not is_on_second_life, level_time, swap_cooldown)

        elif state == GameState.MENU:
            starfield.draw(screen)

            # Kolory dla tekstu w stylu pixel art
            text_color = (230, 230, 240)
            shadow_color = (40, 40, 50)
            highlight_color = CYAN

            # Tytuł gry
            draw_pixel_text(screen, "Quantum Echo", font_large, (SCREEN_WIDTH // 2, 200), PURPLE, shadow_color)
            draw_pixel_text(screen, "Manipuluj czasem!", font_medium, (SCREEN_WIDTH // 2, 280), highlight_color, shadow_color)

            # Opcje menu
            draw_pixel_text(screen, "SPACE - Rozpocznij grę", font_medium, (SCREEN_WIDTH // 2, 400), text_color, shadow_color)
            draw_pixel_text(screen, "I - Instrukcje", font_medium, (SCREEN_WIDTH // 2, 450), text_color, shadow_color)
            draw_pixel_text(screen, "L - Wybór poziomu (trening)", font_medium, (SCREEN_WIDTH // 2, 500), text_color, shadow_color)
            draw_pixel_text(screen, "R - Ranking", font_medium, (SCREEN_WIDTH // 2, 550), text_color, shadow_color)
            draw_pixel_text(screen, "ESC - Wyjście", font_medium, (SCREEN_WIDTH // 2, 600), text_color, shadow_color)

            # Informacja o produkcji
            draw_pixel_text(screen, "Produkcja: Cybermich 2025", font_small, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40), GRAY, shadow_color)


        # Instrukcje
        elif state == GameState.INSTRUCTIONS:
            starfield.draw(screen)
            # Definiujemy kolory, których będziemy używać
            text_color = (230, 230, 240)
            shadow_color = (40, 40, 50)
            highlight_color = CYAN  # Kolor do wyróżnienia nagłówków

            # Używamy draw_pixel_text dla spójnego wyglądu z cieniem
            draw_pixel_text(screen, "Instrukcje", font_large, (SCREEN_WIDTH // 2, 100), YELLOW, shadow_color)

            instructions = [
                "Sterowanie:", "A/D lub Strzałki - Ruch", "SPACJA - Skok", "",
                "Mechaniki Kwantowe:",
                "Q - Zamiana z Echem. Użyj jej, by uciec z opresji!",
                "Twoje Echo podąża za Tobą z 10-sekundowym opóźnieniem.",
                "Gdy zginiesz, przejmiesz nad nim kontrolę!", "",
                "ESC - Powrót do menu"
            ]
            y = 220
            for line in instructions:
                # Wybierz kolor w zależności od treści linii
                if line in ["Sterowanie:", "Mechaniki Kwantowe:"]:
                    current_color = highlight_color
                elif line == "ESC - Powrót do menu":
                    current_color = ORANGE  # Specjalny kolor dla tej linii
                else:
                    current_color = text_color

                # Rysuj tekst, ale tylko jeśli linia nie jest pusta
                if line:
                    draw_pixel_text(screen, line, font_small, (SCREEN_WIDTH // 2, y), current_color, shadow_color)

                y += 35

        # Wybór poziomu
        elif state == GameState.LEVEL_SELECT:
            starfield.draw(screen)
            draw_text("Wybierz poziom:", font_large, GREEN, screen, SCREEN_WIDTH // 2, 100, center=True)
            draw_text("Tryb Treningowy pozwala na naukę mechanik gry", font_medium, GRAY, screen, SCREEN_WIDTH // 2, 150, center=True)
            draw_text("1 Poziom: Pierwsze kroki", font_medium, WHITE, screen, SCREEN_WIDTH // 2, 250, center=True)
            draw_text("2 Poziom: Wyzwanie", font_medium, WHITE, screen, SCREEN_WIDTH // 2, 300, center=True)
            draw_text("3 Poziom: Wspinaczka", font_medium, WHITE, screen, SCREEN_WIDTH // 2, 350, center=True)
            draw_text("4 Poziom: Kwantowa Studnia", font_medium, WHITE, screen, SCREEN_WIDTH // 2, 400, center=True)
            draw_text("ESC - Powrót do menu", font_small, ORANGE, screen, SCREEN_WIDTH // 2, 550, center=True)

        elif state == GameState.PAUSED:
            if current_level: current_level.draw(screen)
            if player: player.draw(screen)
            if echo: echo.draw(screen)
            particle_system.draw(screen)
            gems_left = len([c for c in current_level.collectibles if c.type == "gem"]) if current_level else 0
            if player: draw_hud(screen, player, gems_left, not is_on_second_life, level_time, swap_cooldown)

            pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); pause_overlay.set_alpha(180); pause_overlay.fill(BLACK)
            screen.blit(pause_overlay, (0, 0))
            draw_text("PAUZA", font_large, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, center=True)
            draw_text("SPACJA - Kontynuuj", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
            draw_text("ESC - Wyjdź do Menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, center=True)

        elif state == GameState.GAME_OVER:
            starfield.draw(screen)
            draw_text("KONIEC GRY", font_large, RED, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, center=True)
            if is_training_mode:
                draw_text("Tryb Treningowy", font_medium, CYAN, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
                draw_text("R - Restart Poziomu", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 150, center=True)
            else:
                draw_text(f"Wynik: {score - restart_penalty}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
                draw_text(f"Śmierci: {deaths}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, center=True)
                draw_text("R - Restart Poziomu (-50 pkt)", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 150, center=True)
            draw_text("ESC - Menu Główne", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 200, center=True)

        elif state == GameState.LEVEL_COMPLETE:
            starfield.draw(screen)
            y_pos = SCREEN_HEIGHT // 2 - 150
            draw_text("POZIOM UKOŃCZONY!", font_large, GREEN, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 80
            draw_text(f"Wynik: {score - restart_penalty}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text(f"Czas: {level_time // 60}s", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text(f"Użyte zamiany: {swap_count}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            if restart_penalty > 0:
                y_pos += 50
                draw_text(f"Kara za restarty: -{restart_penalty} pkt", font_medium, RED, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 40
            draw_text("SPACE - Następny poziom", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text("ESC - Wyjdź do Menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)

        elif state == GameState.TRAINING_COMPLETE:
            starfield.draw(screen)
            draw_text("TRENING UKOŃCZONY", font_large, GREEN, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, center=True)
            draw_text("L - Wybierz inny poziom", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, center=True)
            draw_text("ESC - Powrót do menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100, center=True)

        elif state == GameState.GAME_COMPLETE:
            starfield.draw(screen)
            y_pos = SCREEN_HEIGHT // 2 - 200
            draw_text("GRATULACJE!", font_large, GREEN, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 80
            draw_text("Ukończyłeś wszystkie poziomy!", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 80
            final_score = score - restart_penalty
            draw_text(f"Ostateczny wynik: {final_score}", font_medium, YELLOW, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text(f"Suma śmierci: {deaths}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text(f"Suma zamian: {total_swap_count}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 80
            draw_text("Wpisz swoje imię:", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            input_box_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, y_pos, 300, 50)
            pygame.draw.rect(screen, WHITE, input_box_rect, 2)
            draw_text(player_name, font_medium, WHITE, screen, input_box_rect.centerx, input_box_rect.centery, center=True)
            y_pos += 80
            draw_text("Naciśnij ENTER, aby zapisać", font_small, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)

        elif state == GameState.RANKING:
            starfield.draw(screen)
            y_pos = 100
            draw_text("NAJLEPSZE WYNIKI", font_large, YELLOW, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 100
            if not ranking:
                draw_text("Brak zapisanych wyników.", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            else:
                for i, entry in enumerate(ranking):
                    rank_text = f"{i + 1}. {entry['name']}"
                    score_text = f"{entry['score']}"
                    draw_text(rank_text, font_medium, WHITE, screen, SCREEN_WIDTH // 2 - 150, y_pos)
                    draw_text(score_text, font_medium, WHITE, screen, SCREEN_WIDTH // 2 + 150, y_pos)
                    y_pos += 50
            draw_text("ESC - Powrót do menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100, center=True)

        pygame.display.flip() # Odśwież ekran
        clock.tick(FPS) # Ustaw liczbę klatek na sekundę

    pygame.quit()

if __name__ == "__main__":
    main()
