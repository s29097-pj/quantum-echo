"""Prosty wizualny edytor poziomów Quantum Echo.

Uruchomienie::

    python editor.py
    python editor.py --level quantumecho_game/levels/level1.json

Edytor zapisuje ten sam format JSON, którego używa ``quantumecho_game.level``.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import pygame


CELL_SIZE = 32
WORLD_WIDTH = 1024
WORLD_HEIGHT = 768
TOOLBAR_HEIGHT = 64
PANEL_WIDTH = 256
WINDOW_SIZE = (WORLD_WIDTH + PANEL_WIDTH, WORLD_HEIGHT + TOOLBAR_HEIGHT)
LEVEL_DIR = Path(__file__).resolve().parent / "quantumecho_game" / "levels"
CUSTOM_LEVEL_DIR = LEVEL_DIR / "custom_levels"

TOOLS = {
    pygame.K_1: ("player", "Gracz", (80, 170, 255)),
    pygame.K_2: ("wall", "Ściana", (135, 90, 60)),
    pygame.K_3: ("platform", "Platforma", (80, 190, 100)),
    pygame.K_4: ("meta", "Meta", (255, 220, 40)),
    pygame.K_5: ("hazard", "Kolce", (235, 65, 65)),
    pygame.K_6: ("collectible", "Klejnot", (190, 90, 245)),
    pygame.K_7: ("temporal_platform", "Platforma czasowa", (50, 180, 210)),
    pygame.K_8: ("button", "Klucz", (245, 150, 45)),
}
TOOL_ORDER = [value[0] for value in TOOLS.values()]


def empty_level() -> dict:
    """Zwraca minimalny, ale w pełni kompatybilny poziom."""
    return {
        "platforms": [],
        "temporal_platforms": [],
        "hazards": [],
        "collectibles": [],
        "buttons": [],
        "start": {"x": 32, "y": 32},
        "end": {"x": 928, "y": 32},
    }


def load_level(path: Path) -> dict:
    """Wczytuje poziom bez zmieniania jego istniejących pól."""
    with path.open(encoding="utf-8") as level_file:
        data = json.load(level_file)
    result = empty_level()
    result.update(copy.deepcopy(data))
    return result


class LevelEditor:
    def __init__(self, level_data: dict | None = None, output_path: Path | None = None):
        self.data = copy.deepcopy(level_data or empty_level())
        self.output_path = output_path
        self.level_name = ""
        self.selected_tool = "platform"
        self.status = "Wybierz element z palety. LPM: dodaj, PPM: usuń, S: zapisz"
        self.dragging = False
        self.last_cell = None
        self.name_active = False
        self.palette_rect = pygame.Rect(WORLD_WIDTH, 0, PANEL_WIDTH, WORLD_HEIGHT + TOOLBAR_HEIGHT)
        self.name_rect = pygame.Rect(WORLD_WIDTH + 16, 52, PANEL_WIDTH - 32, 34)

        if output_path is not None:
            self.level_name = output_path.stem

    @staticmethod
    def _cell_from_pos(pos: tuple[int, int]) -> tuple[int, int] | None:
        x, y = pos
        if not (0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT):
            return None
        return x // CELL_SIZE, y // CELL_SIZE

    @staticmethod
    def _position(cell: tuple[int, int]) -> tuple[int, int]:
        return cell[0] * CELL_SIZE, cell[1] * CELL_SIZE

    def _remove_at(self, cell: tuple[int, int]) -> None:
        x, y = self._position(cell)
        hit = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        for field in ("platforms", "temporal_platforms", "hazards", "collectibles", "buttons"):
            self.data[field] = [
                item for item in self.data.get(field, [])
                if not hit.colliderect(pygame.Rect(item["x"], item["y"], item.get("width", CELL_SIZE), item.get("height", CELL_SIZE)))
            ]
        for field in ("start", "end"):
            point = self.data.get(field, {})
            if hit.collidepoint(point.get("x", -1), point.get("y", -1)):
                self.data[field] = {"x": 0, "y": 0}

    def _place_at(self, cell: tuple[int, int]) -> None:
        x, y = self._position(cell)
        tool = self.selected_tool
        if tool == "player":
            self.data["start"] = {"x": x, "y": y}
        elif tool == "meta":
            self.data["end"] = {"x": x, "y": y}
        elif tool in ("wall", "platform"):
            self._add_unique("platforms", {"x": x, "y": y, "width": CELL_SIZE, "height": CELL_SIZE})
        elif tool == "temporal_platform":
            self._add_unique("temporal_platforms", {"x": x, "y": y, "width": CELL_SIZE, "height": CELL_SIZE, "initial_state": "solid"})
        elif tool == "hazard":
            self._add_unique("hazards", {"x": x, "y": y, "width": CELL_SIZE, "height": CELL_SIZE, "type": "spike"})
        elif tool == "collectible":
            self._add_unique("collectibles", {"x": x, "y": y, "type": "gem"})
        elif tool == "button":
            self._add_unique("buttons", {"x": x, "y": y})

    def _add_unique(self, field: str, item: dict) -> None:
        if not any(old.get("x") == item["x"] and old.get("y") == item["y"] for old in self.data.setdefault(field, [])):
            self.data[field].append(item)

    def save(self) -> None:
        if self.output_path is None:
            safe_name = "".join(char if char.isalnum() or char in "-_ " else "_" for char in self.level_name).strip()
            safe_name = "_".join(safe_name.split()) or "mój_poziom"
            self.output_path = CUSTOM_LEVEL_DIR / f"{safe_name}.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as level_file:
            json.dump(self.data, level_file, indent=4, ensure_ascii=False)
            level_file.write("\n")
        self.status = f"Zapisano poziom „{self.level_name or self.output_path.stem}”"

    def _select_palette_tool(self, pos: tuple[int, int]) -> bool:
        if not self.palette_rect.collidepoint(pos):
            return False
        if self.name_rect.collidepoint(pos):
            self.name_active = True
            pygame.key.start_text_input()
            return True
        self.name_active = False
        pygame.key.stop_text_input()
        for index, kind in enumerate(TOOL_ORDER):
            rect = pygame.Rect(WORLD_WIDTH + 16, 120 + index * 58, PANEL_WIDTH - 32, 48)
            if rect.collidepoint(pos):
                self.selected_tool = kind
                return True
        return True

    def _draw_item(self, surface: pygame.Surface, item: dict, color: tuple[int, int, int], size: tuple[int, int] = (CELL_SIZE, CELL_SIZE)) -> None:
        rect = pygame.Rect(item["x"], item["y"], *size)
        pygame.draw.rect(surface, color, rect, border_radius=3)
        pygame.draw.rect(surface, (245, 245, 245), rect, 1)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        surface.fill((20, 24, 38))
        for x in range(0, WORLD_WIDTH + 1, CELL_SIZE):
            pygame.draw.line(surface, (43, 51, 72), (x, 0), (x, WORLD_HEIGHT))
        for y in range(0, WORLD_HEIGHT + 1, CELL_SIZE):
            pygame.draw.line(surface, (43, 51, 72), (0, y), (WORLD_WIDTH, y))

        for item in self.data.get("platforms", []): self._draw_item(surface, item, (115, 75, 50), (item.get("width", CELL_SIZE), item.get("height", CELL_SIZE)))
        for item in self.data.get("temporal_platforms", []): self._draw_item(surface, item, (45, 145, 180), (item.get("width", CELL_SIZE), item.get("height", CELL_SIZE)))
        for item in self.data.get("hazards", []): self._draw_item(surface, item, (220, 55, 55), (item.get("width", CELL_SIZE), item.get("height", CELL_SIZE)))
        for item in self.data.get("collectibles", []): self._draw_item(surface, item, (185, 80, 230))
        for item in self.data.get("buttons", []): self._draw_item(surface, item, (235, 145, 40))
        self._draw_item(surface, self.data.get("start", {"x": 0, "y": 0}), (70, 155, 255))
        self._draw_item(surface, self.data.get("end", {"x": 0, "y": 0}), (255, 215, 35))

        pygame.draw.rect(surface, (15, 17, 27), (0, WORLD_HEIGHT, WORLD_WIDTH, TOOLBAR_HEIGHT))
        selected_label = next(label for kind, label, _ in TOOLS.values() if kind == self.selected_tool)
        text = f"Wybrane: {selected_label} | LPM dodaj  PPM usuń | S zapisz | ESC wyjście"
        surface.blit(font.render(text, True, (235, 235, 235)), (10, WORLD_HEIGHT + 8))
        surface.blit(font.render(self.status, True, (145, 210, 220)), (10, WORLD_HEIGHT + 35))

        pygame.draw.rect(surface, (28, 32, 50), self.palette_rect)
        pygame.draw.line(surface, (75, 85, 115), (WORLD_WIDTH, 0), (WORLD_WIDTH, WORLD_HEIGHT + TOOLBAR_HEIGHT), 2)
        title = pygame.font.Font(None, 28).render("PALETA POZIOMU", True, (240, 240, 250))
        surface.blit(title, (WORLD_WIDTH + 16, 14))
        pygame.draw.rect(surface, (15, 18, 30), self.name_rect, border_radius=4)
        pygame.draw.rect(surface, (80, 210, 220) if self.name_active else (100, 105, 130), self.name_rect, 2, border_radius=4)
        name_text = self.level_name or "Nazwa poziomu..."
        name_color = (245, 245, 245) if self.level_name else (135, 140, 155)
        surface.blit(font.render(name_text, True, name_color), (self.name_rect.x + 8, self.name_rect.y + 8))

        palette_font = pygame.font.Font(None, 22)
        for index, (kind, label, color) in enumerate(TOOLS.values()):
            rect = pygame.Rect(WORLD_WIDTH + 16, 120 + index * 58, PANEL_WIDTH - 32, 48)
            selected = kind == self.selected_tool
            pygame.draw.rect(surface, (55, 65, 90) if selected else (38, 44, 65), rect, border_radius=5)
            pygame.draw.rect(surface, color, (rect.x + 8, rect.y + 8, 32, 32), border_radius=4)
            shortcut = str(index + 1)
            surface.blit(palette_font.render(f"{shortcut}  {label}", True, (245, 245, 250)), (rect.x + 48, rect.y + 13))

        hint = ["Kliknij nazwę i wpisz tytuł.", "Zapisane poziomy trafiają", "do menu treningów."]
        for index, line in enumerate(hint):
            surface.blit(font.render(line, True, (155, 165, 185)), (WORLD_WIDTH + 16, 600 + index * 22))

    def run(self) -> None:
        pygame.init()
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Quantum Echo — Edytor poziomów")
        font = pygame.font.Font(None, 21)
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in TOOLS:
                        self.selected_tool = TOOLS[event.key][0]
                    elif event.key == pygame.K_s:
                        self.save()
                    elif event.key == pygame.K_BACKSPACE and self.name_active:
                        self.level_name = self.level_name[:-1]
                    elif event.key == pygame.K_RETURN and self.name_active:
                        self.name_active = False
                        pygame.key.stop_text_input()
                elif event.type == pygame.TEXTINPUT and self.name_active:
                    if len(self.level_name) < 40:
                        self.level_name += event.text
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self._select_palette_tool(event.pos):
                        if self.palette_rect.collidepoint(event.pos):
                            continue
                    cell = self._cell_from_pos(event.pos)
                    if cell is not None:
                        self.dragging = True
                        self.last_cell = cell
                        self._remove_at(cell) if event.button == 3 else self._place_at(cell)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False
                    self.last_cell = None
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    cell = self._cell_from_pos(event.pos)
                    if cell is not None and cell != self.last_cell:
                        self.last_cell = cell
                        buttons = pygame.mouse.get_pressed()
                        self._remove_at(cell) if buttons[2] else self._place_at(cell)
            self.draw(screen, font)
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Wizualny edytor poziomów Quantum Echo")
    parser.add_argument("--level", type=Path, help="opcjonalny poziom JSON do wczytania")
    parser.add_argument("--output", type=Path, help="plik wyjściowy; domyślnie quantumecho_game/levels/new_level.json")
    args = parser.parse_args()
    data = load_level(args.level) if args.level else empty_level()
    LevelEditor(data, args.output).run()


if __name__ == "__main__":
    main()
