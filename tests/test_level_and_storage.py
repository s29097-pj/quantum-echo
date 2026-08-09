import json

import pygame

from quantumecho_game.level import Level
from quantumecho_game.storage import load_level, load_ranking, save_ranking


def test_load_level_creates_world_objects(tmp_path):
    level_file = tmp_path / "level.json"
    level_file.write_text(
        json.dumps(
            {
                "platforms": [{"x": 0, "y": 700, "width": 200, "height": 20}],
                "hazards": [{"x": 100, "y": 670, "width": 20, "height": 30}],
                "collectibles": [{"x": 50, "y": 650, "type": "gem"}],
                "buttons": [{"x": 150, "y": 650}],
                "start": {"x": 10, "y": 650},
                "end": {"x": 180, "y": 650},
            }
        ),
        encoding="utf-8",
    )

    data = load_level(str(level_file))
    level = Level(data, 0)

    assert level.start_pos == (10, 650)
    assert len(level.platforms) == 1
    assert len(level.hazards) == 1
    assert len(level.collectibles) == 1
    assert len(level.keys) == 1
    assert level.exit_zone.locked is True

    level.draw(pygame.Surface((1280, 720)))


def test_missing_level_returns_none(tmp_path):
    assert load_level(str(tmp_path / "missing.json")) is None


def test_ranking_is_sorted_and_limited_to_seven_entries(tmp_path):
    ranking_file = tmp_path / "ranking.json"
    entries = [{"name": str(index), "score": index} for index in range(10)]

    save_ranking(str(ranking_file), entries)
    ranking = load_ranking(str(ranking_file))

    assert len(ranking) == 7
    assert [entry["score"] for entry in ranking] == [9, 8, 7, 6, 5, 4, 3]
