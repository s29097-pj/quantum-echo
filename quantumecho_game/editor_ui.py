"""Komponenty ekranów edytora i przeglądarki poziomów.

Moduł jest bezstanowy względem głównej pętli: ``LevelEditor`` obsługuje tylko
zdarzenia i rysowanie jednej klatki, dzięki czemu nie tworzy drugiego okna ani
drugiej pętli Pygame.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pygame

from .config import BLACK, CYAN, GRAY, GREEN, ORANGE, PURPLE, RED, WHITE, YELLOW

CANVAS_WIDTH = 960
CANVAS_HEIGHT = 640
PANEL_WIDTH = 320
CELL_SIZE = 32
THUMBNAIL_SIZE = (320, 180)

TOOLS = [
    ("platform", "Platforma", (115, 75, 50)),
    ("temporal_platform", "Platforma czasowa", (45, 145, 180)),
    ("hazard", "Kolce", RED),
    ("collectible", "Klejnot", PURPLE),
    ("button", "Klucz", ORANGE),
    ("time_dilation_zone", "Dylatacja czasu", (120, 70, 210)),
    ("paradox_switch", "Przełącznik Echo", CYAN),
    ("paradox_door", "Przejście paradoksu", (180, 50, 180)),
    ("player", "Start gracza", (70, 155, 255)),
    ("meta", "Meta poziomu", YELLOW),
]


def empty_level() -> dict:
    return {
        "platforms": [], "temporal_platforms": [], "hazards": [],
        "collectibles": [], "buttons": [], "time_dilation_zones": [],
        "paradox_switches": [], "paradox_doors": [],
        "start": {"x": 32, "y": 32}, "end": {"x": 864, "y": 32},
    }


def read_level(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    result = empty_level()
    result.update(copy.deepcopy(data))
    return result


def thumbnail_path(level_path: Path) -> Path:
    return level_path.parent / "thumbnails" / f"{level_path.stem}.png"


def _draw_preview(surface: pygame.Surface, data: dict) -> None:
    surface.fill((18, 22, 38))
    scale_x = surface.get_width() / 1024
    scale_y = surface.get_height() / 720

    def rect_for(item, default=(32, 32)):
        return pygame.Rect(int(item.get("x", 0) * scale_x), int(item.get("y", 0) * scale_y),
                           max(2, int(item.get("width", default[0]) * scale_x)),
                           max(2, int(item.get("height", default[1]) * scale_y)))

    for item in data.get("platforms", []): pygame.draw.rect(surface, (115, 75, 50), rect_for(item))
    for item in data.get("temporal_platforms", []): pygame.draw.rect(surface, (45, 145, 180), rect_for(item))
    for item in data.get("hazards", []): pygame.draw.rect(surface, RED, rect_for(item))
    for item in data.get("collectibles", []): pygame.draw.circle(surface, PURPLE, rect_for(item).center, 6)
    for item in data.get("time_dilation_zones", data.get("slow_motion_zones", [])):
        pygame.draw.rect(surface, (110, 65, 180), rect_for(item), 2)
    for item in data.get("paradox_doors", data.get("locked_passages", [])):
        pygame.draw.rect(surface, (180, 50, 180), rect_for(item))
    for field, color in (("start", (70, 155, 255)), ("end", YELLOW)):
        item = data.get(field, {})
        pygame.draw.rect(surface, color, rect_for(item), 2)


def save_level(data: dict, path: Path) -> Path:
    """Atomowo zapisuje JSON i generuje miniaturę z ``pygame.Surface``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=4, ensure_ascii=False)
        stream.write("\n")
    thumbnail = pygame.Surface(THUMBNAIL_SIZE)
    _draw_preview(thumbnail, data)
    thumbnail_file = thumbnail_path(path)
    thumbnail_file.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(thumbnail, str(thumbnail_file))
    return thumbnail_file


def ensure_thumbnail(path: Path) -> Path:
    thumbnail = thumbnail_path(path)
    if not thumbnail.exists():
        preview = pygame.Surface(THUMBNAIL_SIZE)
        _draw_preview(preview, read_level(path))
        thumbnail.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(preview, str(thumbnail))
    return thumbnail


def load_thumbnail(path: Path) -> pygame.Surface | None:
    thumbnail = thumbnail_path(path)
    if not thumbnail.exists():
        ensure_thumbnail(path)
    try:
        return pygame.image.load(str(thumbnail)).convert()
    except (pygame.error, OSError):
        return None


def delete_level(path: Path, custom_root: Path) -> bool:
    """Usuwa wyłącznie poziom użytkownika i jego miniaturę."""
    try:
        path.resolve().relative_to(custom_root.resolve())
    except ValueError:
        return False
    if not path.is_file():
        return False
    path.unlink()
    thumbnail = thumbnail_path(path)
    if thumbnail.is_file():
        thumbnail.unlink()
    return True


class LevelEditor:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.data = empty_level()
        self.level_name = ""
        self.selected_tool = "platform"
        self.dragging = False
        self.last_cell = None
        self.name_active = False
        self.status = "LPM: rysuj | PPM: usuń | S: zapisz | ESC: menu"
        self.name_rect = pygame.Rect(CANVAS_WIDTH + 16, 52, PANEL_WIDTH - 32, 34)

    def load(self, path: Path | None = None) -> None:
        self.data = read_level(path) if path else empty_level()
        self.level_name = path.stem if path else ""
        self.status = "Poziom wczytany."

    def _cell(self, pos):
        x, y = pos
        if not (0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT):
            return None
        return x // CELL_SIZE, y // CELL_SIZE

    def _remove(self, cell):
        x, y = cell[0] * CELL_SIZE, cell[1] * CELL_SIZE
        hit = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        fields = ("platforms", "temporal_platforms", "hazards", "collectibles", "buttons",
                  "time_dilation_zones", "paradox_switches", "paradox_doors")
        for field in fields:
            self.data[field] = [item for item in self.data.get(field, []) if not hit.colliderect(
                pygame.Rect(item["x"], item["y"], item.get("width", CELL_SIZE), item.get("height", CELL_SIZE)))]

    def _add(self, field, item):
        if not any(old.get("x") == item["x"] and old.get("y") == item["y"] for old in self.data[field]):
            self.data[field].append(item)

    def _place(self, cell):
        x, y = cell[0] * CELL_SIZE, cell[1] * CELL_SIZE
        tool = self.selected_tool
        if tool == "player": self.data["start"] = {"x": x, "y": y}
        elif tool == "meta": self.data["end"] = {"x": x, "y": y}
        elif tool in ("platform",): self._add("platforms", {"x": x, "y": y, "width": CELL_SIZE, "height": CELL_SIZE})
        elif tool == "temporal_platform": self._add("temporal_platforms", {"x": x, "y": y, "width": CELL_SIZE, "height": CELL_SIZE, "initial_state": "solid"})
        elif tool == "hazard": self._add("hazards", {"x": x, "y": y, "width": CELL_SIZE, "height": CELL_SIZE, "type": "spike"})
        elif tool == "collectible": self._add("collectibles", {"x": x, "y": y, "type": "gem"})
        elif tool == "button": self._add("buttons", {"x": x, "y": y})
        elif tool == "time_dilation_zone": self._add("time_dilation_zones", {"x": x, "y": y, "width": CELL_SIZE * 3, "height": CELL_SIZE * 3, "factor": 0.5})
        elif tool == "paradox_switch": self._add("paradox_switches", {"x": x, "y": y})
        elif tool == "paradox_door": self._add("paradox_doors", {"x": x, "y": y, "width": CELL_SIZE, "height": CELL_SIZE * 3})

    def handle_event(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: return "menu"
            if event.key == pygame.K_s:
                safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in self.level_name).strip()
                path = self.output_dir / f"{'_'.join(safe.split()) or 'nowy_poziom'}.json"
                save_level(self.data, path)
                self.status = f"Zapisano {path.stem}.json i miniaturę PNG"
            elif event.key == pygame.K_BACKSPACE and self.name_active: self.level_name = self.level_name[:-1]
            elif event.key == pygame.K_RETURN and self.name_active:
                self.name_active = False; pygame.key.stop_text_input()
            else:
                for index, (kind, *_rest) in enumerate(TOOLS):
                    if event.key == pygame.K_1 + index: self.selected_tool = kind
        elif event.type == pygame.TEXTINPUT and self.name_active and len(self.level_name) < 40:
            self.level_name += event.text
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.name_rect.collidepoint(event.pos):
                self.name_active = True; pygame.key.start_text_input(); return None
            if event.pos[0] >= CANVAS_WIDTH:
                for index, (kind, *_rest) in enumerate(TOOLS):
                    if pygame.Rect(CANVAS_WIDTH + 16, 100 + index * 48, PANEL_WIDTH - 32, 40).collidepoint(event.pos):
                        self.selected_tool = kind
                return None
            cell = self._cell(event.pos)
            if cell:
                self.dragging = True; self.last_cell = cell
                self._remove(cell) if event.button == 3 else self._place(cell)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False; self.last_cell = None
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            cell = self._cell(event.pos)
            if cell and cell != self.last_cell:
                self.last_cell = cell
                self._remove(cell) if pygame.mouse.get_pressed()[2] else self._place(cell)
        return None

    def draw(self, surface: pygame.Surface, font) -> None:
        surface.fill((20, 24, 38))
        for x in range(0, CANVAS_WIDTH + 1, CELL_SIZE): pygame.draw.line(surface, (43, 51, 72), (x, 0), (x, CANVAS_HEIGHT))
        for y in range(0, CANVAS_HEIGHT + 1, CELL_SIZE): pygame.draw.line(surface, (43, 51, 72), (0, y), (CANVAS_WIDTH, y))
        colors = {kind: color for kind, _label, color in TOOLS}
        fields = (("platforms", "platform"), ("temporal_platforms", "temporal_platform"), ("hazards", "hazard"),
                  ("collectibles", "collectible"), ("buttons", "button"), ("time_dilation_zones", "time_dilation_zone"),
                  ("paradox_switches", "paradox_switch"), ("paradox_doors", "paradox_door"))
        for field, kind in fields:
            for item in self.data.get(field, []):
                rect = pygame.Rect(item["x"], item["y"], item.get("width", CELL_SIZE), item.get("height", CELL_SIZE))
                pygame.draw.rect(surface, colors[kind], rect, border_radius=3)
        for field, kind in (("start", "player"), ("end", "meta")):
            item = self.data[field]; pygame.draw.rect(surface, colors[kind], (item["x"], item["y"], CELL_SIZE, CELL_SIZE), 2)
        pygame.draw.rect(surface, (28, 32, 50), (CANVAS_WIDTH, 0, PANEL_WIDTH, surface.get_height()))
        surface.blit(font.render("EDYTOR POZIOMU", True, WHITE), (CANVAS_WIDTH + 16, 14))
        pygame.draw.rect(surface, (15, 18, 30), self.name_rect); pygame.draw.rect(surface, CYAN if self.name_active else GRAY, self.name_rect, 2)
        surface.blit(font.render(self.level_name or "Nazwa poziomu...", True, WHITE), (self.name_rect.x + 8, self.name_rect.y + 8))
        for index, (kind, label, color) in enumerate(TOOLS):
            rect = pygame.Rect(CANVAS_WIDTH + 16, 100 + index * 48, PANEL_WIDTH - 32, 40)
            pygame.draw.rect(surface, (55, 65, 90) if kind == self.selected_tool else (38, 44, 65), rect)
            pygame.draw.rect(surface, color, (rect.x + 6, rect.y + 6, 28, 28))
            surface.blit(font.render(f"{index + 1}: {label}", True, WHITE), (rect.x + 42, rect.y + 10))
        surface.blit(font.render(self.status, True, CYAN), (10, CANVAS_HEIGHT + 8))


def discover_levels(level_dir: Path) -> list[Path]:
    return sorted((path for path in level_dir.rglob("*.json") if path.is_file()), key=lambda p: str(p).lower())
