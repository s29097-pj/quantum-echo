"""Trwały zapis danych gry."""

import json


DEFAULT_SETTINGS = {
    "lives": 3,
    "music_volume": 0.7,
    "sfx_volume": 0.8,
}


def load_settings(filename):
    """Wczytuje ustawienia, uzupełniając brakujące pola wartościami domyślnymi."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
        settings = DEFAULT_SETTINGS.copy()
        settings.update(data if isinstance(data, dict) else {})
        if settings["lives"] not in (1, 3, 5, "infinite"):
            settings["lives"] = DEFAULT_SETTINGS["lives"]
        for key in ("music_volume", "sfx_volume"):
            settings[key] = max(0.0, min(1.0, float(settings[key])))
        return settings
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        return DEFAULT_SETTINGS.copy()


def save_settings(filename, settings):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4, ensure_ascii=False)


def load_level(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Błąd: Nie można znaleźć pliku poziomu: {filename}")
    except json.JSONDecodeError as error:
        print(f"Błąd: Niepoprawny format pliku JSON '{filename}': {error}")
    except OSError as error:
        print(f"Niespodziewany błąd podczas ładowania poziomu '{filename}': {error}")
    return None


def load_ranking(filename):
    try:
        with open(filename, "r") as file:
            data = json.load(file)
            return sorted(data, key=lambda entry: entry["score"], reverse=True)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_ranking(filename, ranking_data):
    sorted_ranking = sorted(ranking_data, key=lambda entry: entry["score"], reverse=True)
    with open(filename, "w") as file:
        json.dump(sorted_ranking[:7], file, indent=4)
