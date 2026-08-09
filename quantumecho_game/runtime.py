"""Współdzielone zasoby Pygame."""

import os
import pygame

from .config import SCREEN_WIDTH, SCREEN_HEIGHT

# Mikser musi być gotowy przed pygame.init(), ponieważ app.py ładuje dźwięki
# podczas inicjalizacji współdzielonych zasobów.
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except pygame.error as error:
    print(f"Błąd inicjalizacji pygame.mixer: {error}")
pygame.init()
# Jeśli sterownik audio był chwilowo niedostępny przed pygame.init(), spróbuj
# jeszcze raz, zachowując ten sam jawny profil miksera.
if pygame.mixer.get_init() is None:
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error as error:
        print(f"Błąd ponownej inicjalizacji pygame.mixer: {error}")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Quantum Echo - Manipuluj Czasem!")
clock = pygame.time.Clock()

PACKAGE_DIR = os.path.dirname(__file__)
FONT_PATH = os.path.join(PACKAGE_DIR, "fonts", "VT323-Regular.ttf")
try:
    font_small = pygame.font.Font(FONT_PATH, 24)
    font_medium = pygame.font.Font(FONT_PATH, 40)
    font_large = pygame.font.Font(FONT_PATH, 80)
except (pygame.error, FileNotFoundError):
    print(f"Błąd: Nie można wczytać czcionki z '{FONT_PATH}'. Używam czcionki domyślnej.")
    font_small = pygame.font.Font(None, 24)
    font_medium = pygame.font.Font(None, 36)
    font_large = pygame.font.Font(None, 72)
