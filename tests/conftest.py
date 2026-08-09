"""Konfiguracja testów uruchamianych bez monitora."""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest
import pygame


@pytest.fixture(autouse=True)
def reset_pygame_state():
    """Zapewnia aktywną inicjalizację Pygame dla każdego testu."""
    pygame.init()
    yield
    pygame.event.clear()
