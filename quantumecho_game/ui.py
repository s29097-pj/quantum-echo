"""Renderowanie elementów interfejsu gry."""

import pygame

from .config import GRAY, GREEN, PURPLE, RED, WHITE, YELLOW, CYAN, SCREEN_WIDTH
from .runtime import font_small, font_medium

def draw_text(text, font, color, surface, x, y, center=False):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)


def draw_hud_icon(surface, kind, center):
    """Rysuje małe ikony HUD bez assetów graficznych."""
    x, y = center
    if kind == "gem":
        pygame.draw.polygon(surface, YELLOW,
                            [(x, y - 8), (x + 7, y), (x, y + 8), (x - 7, y)])
        pygame.draw.line(surface, (255, 245, 150), (x, y - 6), (x + 3, y), 2)
    elif kind == "life":
        pygame.draw.circle(surface, RED, (x - 4, y - 3), 5)
        pygame.draw.circle(surface, RED, (x + 4, y - 3), 5)
        pygame.draw.polygon(surface, RED,
                            [(x - 9, y - 1), (x + 9, y - 1), (x, y + 9)])
    elif kind == "time":
        pygame.draw.circle(surface, WHITE, (x, y), 8, 2)
        pygame.draw.line(surface, WHITE, (x, y), (x, y - 5), 2)
        pygame.draw.line(surface, WHITE, (x, y), (x + 4, y + 3), 2)
    elif kind == "quantum":
        pygame.draw.circle(surface, PURPLE, (x, y), 8, 2)
        pygame.draw.arc(surface, CYAN, (x - 10, y - 5, 20, 10), 0.2, 2.9, 2)
        pygame.draw.circle(surface, CYAN, (x + 7, y - 3), 2)
    else:
        pygame.draw.circle(surface, GRAY, (x, y), 5, 1)

# Rysowanie HUD (Heads-Up Display)
def draw_hud(surface, player, collectibles_left, second_life_available, level_time, swap_cooldown,
             lives=None, arcade_level=None):
    # Jedna lista linii eliminuje kolizje współrzędnych Y. Każda informacja
    # otrzymuje własny wiersz i jest wyrównana do lewej strony.
    lines = [("gem", f"Klejnoty: {collectibles_left}", WHITE)]
    seconds = level_time // 60
    lines.append(("time", f"Czas: {seconds}s", WHITE))
    level_text = f"Arcade {arcade_level}" if arcade_level is not None else "Kampania"
    lines.append(("level", f"Poziom: {level_text}", CYAN))
    if lives is not None:
        life_text = "∞" if lives == float("inf") else str(lives)
        lines.append(("life", f"Życia: {life_text}", CYAN))

    # Statusy mechanik także mają własne, bezpieczne wiersze.
    if player.has_double_jump:
        lines.append(("power", "Podwójny skok: TAK", GREEN))
    if player.invincible:
        shield_time = player.invincible_timer // 60
        lines.append(("power", f"Tarcza: {shield_time}s", YELLOW))
    life_color = GREEN if second_life_available else RED
    life_text = "DOSTĘPNE" if second_life_available else "ZUŻYTE"
    lines.append(("life", f"Drugie życie: {life_text}", life_color))
    if swap_cooldown > 0:
        cooldown_sec = (swap_cooldown // 60) + 1
        lines.append(("quantum", f"Zamiany [Q]: {cooldown_sec}s", GRAY))
    else:
        lines.append(("quantum", "Zamiany [Q]: GOTOWA", PURPLE))

    line_height = 27
    padding_x, padding_y = 16, 12
    hud_height = padding_y * 2 + line_height * len(lines)
    hud_surface = pygame.Surface((360, hud_height), pygame.SRCALPHA)
    hud_surface.fill((8, 10, 20, 205))
    hud_surface.set_alpha(205)
    for index, (icon, text, color) in enumerate(lines):
        line_y = padding_y + index * line_height + line_height // 2
        draw_hud_icon(hud_surface, icon, (padding_x + 9, line_y))
        draw_text(text, font_small, color, hud_surface, padding_x + 25,
                  padding_y + index * line_height)
    surface.blit(hud_surface, (10, 10))


class SettingsMenu:
    """Mały, niezależny model ustawień obsługiwany przez klawiaturę i pad."""

    LIFE_OPTIONS = (1, 3, 5, "infinite")

    def __init__(self, settings, on_change=None):
        self.settings = settings
        self.selected = 0
        self.on_change = on_change

    @property
    def items(self):
        return ("lives", "music_volume", "sfx_volume")

    def move(self, direction):
        self.selected = (self.selected + direction) % len(self.items)

    def adjust(self, direction):
        key = self.items[self.selected]
        if key == "lives":
            current = self.settings.get(key, 3)
            index = self.LIFE_OPTIONS.index(current) if current in self.LIFE_OPTIONS else 1
            self.settings[key] = self.LIFE_OPTIONS[(index + direction) % len(self.LIFE_OPTIONS)]
        else:
            self.settings[key] = max(0.0, min(1.0, round(self.settings.get(key, 0.7) + direction * 0.1, 1)))
        if self.on_change:
            self.on_change(self.settings)

    def activate(self):
        self.adjust(1)

    def handle_key(self, key):
        if key in (pygame.K_UP, pygame.K_w): self.move(-1)
        elif key in (pygame.K_DOWN, pygame.K_s): self.move(1)
        elif key in (pygame.K_LEFT, pygame.K_a): self.adjust(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d): self.adjust(1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE): self.activate()
        elif key == pygame.K_ESCAPE: return "back"
        return None

    def draw(self, surface):
        surface.fill((8, 8, 25))
        draw_text("USTAWIENIA", font_medium, CYAN, surface, SCREEN_WIDTH // 2, 110, center=True)
        labels = {"lives": "Liczba żyć", "music_volume": "Głośność muzyki", "sfx_volume": "Głośność SFX"}
        for index, key in enumerate(self.items):
            y = 240 + index * 90
            color = CYAN if index == self.selected else WHITE
            value = self.settings[key]
            if key == "lives": value = "∞" if value == "infinite" else str(value)
            else: value = f"{int(value * 100)}%"
            draw_text(f"{labels[key]}: {value}", font_medium, color, surface, SCREEN_WIDTH // 2, y, center=True)
            if key != "lives":
                pygame.draw.rect(surface, GRAY, (SCREEN_WIDTH // 2 - 180, y + 30, 360, 12), 2)
                pygame.draw.rect(surface, color, (SCREEN_WIDTH // 2 - 176, y + 34, int(352 * self.settings[key]), 4))
        draw_text("Strzałki/D-pad: wybór i zmiana | Enter/A: zmień | Esc/Back: zapisz", font_small,
                  WHITE, surface, SCREEN_WIDTH // 2, 620, center=True)

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

# Funkcja do rysowania wirtualnej klawiatury
def draw_virtual_keyboard(surface, letters, selected_index, font, x, y, cell_size, selected_color, default_color):
    rows = len(letters)
    for row_idx, row_letters in enumerate(letters):
        cols = len(row_letters)
        for col_idx, letter in enumerate(row_letters):
            color = selected_color if selected_index == (row_idx, col_idx) else default_color
            # Oblicz pozycję na podstawie środka siatki
            letter_x = x - (cols * cell_size) / 2 + (col_idx * cell_size) + cell_size / 2
            letter_y = y + row_idx * cell_size
            draw_text(letter, font, color, surface, letter_x, letter_y, center=True)
