"""Bezpieczne, proceduralne poziomy trybu Arcade.

Generator rozdziela "Golden Path" od elementów dodatkowych. Golden Path jest
tworzony wyłącznie w granicach wynikających z fizyki Playera, więc losowość nie
może wylosować obowiązkowego skoku, którego gracz nie jest w stanie wykonać.
"""

import math
import random

from .config import (GRAVITY, JUMP_FORCE, PLAYER_HEIGHT, PLAYER_SPEED,
                     PLAYER_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH)


class ArcadeManager:
    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.level_number = 0
        self.difficulty_level = 0
        self.current_data = None
        self.golden_path = []
        # Player.rect ma obecnie 40 px wysokości. Headroom dotyczy tylko
        # platform, które przecinają ten sam pionowy korytarz ruchu gracza.
        self.player_width = PLAYER_WIDTH
        self.player_height = PLAYER_HEIGHT
        self.minimum_headroom = self.player_height * 3

        # Player skacze z prędkością poziomą PLAYER_SPEED, a jego pionowa
        # prędkość jest aktualizowana co klatkę: v += GRAVITY.
        self.jump_time = (2.0 * abs(JUMP_FORCE)) / GRAVITY
        self.max_jump_height = (abs(JUMP_FORCE) ** 2) / (2.0 * GRAVITY)
        self.max_horizontal_reach = PLAYER_SPEED * self.jump_time
        # Margines pozwala uwzględnić szerokość gracza i niedokładne wejście.
        self.safe_horizontal_reach = max(1, int(self.max_horizontal_reach * 0.72))
        self.safe_vertical_reach = max(1, int(self.max_jump_height * 0.72))

    def has_sufficient_airspace(self, candidate, platforms):
        """Sprawdza wolną przestrzeń nad i pod platformą.

        Platformy rozdzielone poziomo nie tworzą sufitu nad graczem, dlatego
        analizujemy tylko te, które mają wspólny korytarz X. To pozwala budować
        wykonalne rozpadliny, ale odrzuca układy z niskim sufitem.
        """
        candidate_left = candidate["x"]
        candidate_right = candidate["x"] + candidate["width"]
        candidate_top = candidate["y"]
        candidate_bottom = candidate["y"] + candidate["height"]
        for platform in platforms:
            left = platform["x"]
            right = platform["x"] + platform["width"]
            if candidate_right <= left or candidate_left >= right:
                continue
            top = platform["y"]
            bottom = platform["y"] + platform["height"]
            if candidate_bottom <= top:
                clearance = top - candidate_bottom
            elif candidate_top >= bottom:
                clearance = candidate_top - bottom
            else:
                return False
            if clearance < self.minimum_headroom:
                return False
        return True

    def _make_golden_path(self, rng, difficulty):
        """Tworzy wykonalny zygzak: wspinaczka do góry, potem zejście.

        X zmienia kierunek co kilka platform, a Y pracuje w dwóch fazach.
        Dzięki temu poziom nie jest autostradą w prawo, ale nadal zachowuje
        stały rytm skoku i szerokie, bezpieczne platformy docelowe.
        """
        start = {"x": 0, "y": 680, "width": 280, "height": 40}
        path = [start]
        y = start["y"]
        vertical_phase = "up"
        step = 0
        max_gap = min(self.safe_horizontal_reach, 70 + min(55, difficulty * 8))

        # Stała liczba segmentów daje czas na dojście do obu ekstremów
        # ekranu, zamiast kończyć poziom zaraz po pierwszym ruchu w prawo.
        while step < 18:
            previous = path[-1]
            gap = rng.randint(self.player_width + 10, max_gap)
            width = rng.randint(155, 205)

            direction = 1 if (step // 3) % 2 == 0 else -1
            if direction > 0:
                next_x = previous["x"] + previous["width"] + gap
            else:
                next_x = previous["x"] - gap - width
            if not (0 <= next_x <= SCREEN_WIDTH - width):
                direction *= -1
                if direction > 0:
                    next_x = previous["x"] + previous["width"] + gap
                else:
                    next_x = previous["x"] - gap - width
            # Przy granicy ekranu wybierz najbliższy bezpieczny wariant.
            if not (0 <= next_x <= SCREEN_WIDTH - width):
                next_x = max(0, min(SCREEN_WIDTH - width,
                                    previous["x"] + rng.randint(-90, 90)))

            if vertical_phase == "up":
                delta_y = -rng.randint(45, self.safe_vertical_reach)
            else:
                delta_y = rng.randint(45, self.safe_vertical_reach)
            next_y = max(100, min(650, y + delta_y))
            if vertical_phase == "up" and next_y <= 130:
                vertical_phase = "down"
            elif vertical_phase == "down" and next_y >= 610:
                vertical_phase = "up"

            platform = {"x": int(next_x), "y": int(next_y), "width": width, "height": 24}
            if not self.has_sufficient_airspace(platform, path):
                # Wymuś rozdzielenie korytarzy X, zachowując kierunek skoku.
                if next_x >= previous["x"]:
                    platform["x"] = min(SCREEN_WIDTH - width,
                                         previous["x"] + previous["width"] + self.player_width + 10)
                else:
                    platform["x"] = max(0, previous["x"] - width - self.player_width - 10)
            path.append(platform)
            y = platform["y"]
            step += 1
        return path

    def generate_level(self):
        self.level_number += 1
        rng = random.Random(self.seed + self.level_number * 7919)
        self.difficulty_level = self.level_number
        difficulty = self.difficulty_level
        max_gap = min(self.safe_horizontal_reach, 70 + min(55, difficulty * 8))
        self.golden_path = self._make_golden_path(rng, difficulty)

        # Klucz znajduje się w środku ścieżki: najpierw gracz musi dotrzeć do
        # niego, dopiero potem może kontynuować do zablokowanego wyjścia.
        key_index = max(1, min(len(self.golden_path) - 2,
                               len(self.golden_path) // 2))

        temporal_ratio = min(0.40, 0.28 + difficulty * 0.02)
        temporal_count = max(1, math.ceil(len(self.golden_path) * temporal_ratio))
        temporal_candidates = [index for index in range(1, len(self.golden_path) - 1)
                               if index != key_index]
        rng.shuffle(temporal_candidates)
        temporal_indices = set(temporal_candidates[:min(temporal_count, len(temporal_candidates))])

        platforms = []
        temporal = []
        for index, platform in enumerate(self.golden_path):
            if index in temporal_indices:
                temporal.append({**platform, "initial_state": "solid",
                                 "solid_time": max(90, 180 - difficulty * 3),
                                 "phased_time": min(180, 120 + difficulty * 4)})
            else:
                platforms.append(dict(platform))

        # Odnogi zaczynają się przy Golden Path, ale odchodzą pionowo w bok.
        # Ostatnia platforma każdej odnogi dostaje nagrodę.
        branch_count = min(3, 1 + difficulty // 6)
        optional_platforms = []
        branches = []
        for branch_index in range(branch_count):
            anchor = self.golden_path[2 + (branch_index * 4) % max(1, len(self.golden_path) - 3)]
            branch = []
            previous = anchor
            direction = -1 if anchor["x"] > SCREEN_WIDTH // 2 else 1
            for depth in range(2 + (difficulty // 8)):
                width = rng.randint(120, 170)
                gap = rng.randint(self.player_width + 10, max_gap)
                x = previous["x"] - width - gap if direction < 0 else previous["x"] + previous["width"] + gap
                if not (0 <= x <= SCREEN_WIDTH - width):
                    direction *= -1
                    x = previous["x"] - width - gap if direction < 0 else previous["x"] + previous["width"] + gap
                if not (0 <= x <= SCREEN_WIDTH - width):
                    break
                y = max(130, min(640, previous["y"] + rng.randint(-self.safe_vertical_reach,
                                                                   self.safe_vertical_reach)))
                candidate = {"x": int(x), "y": int(y), "width": width, "height": 18}
                # Odnogi są opcjonalnymi skrótami/ryzykiem; mogą przechodzić
                # bliżej innych dekoracyjnych platform, ale pozostają oddalone
                # od swojego poprzednika o bezpieczny dystans skoku.
                platforms.append(candidate)
                optional_platforms.append(candidate)
                branch.append(candidate)
                previous = candidate
            if branch:
                branches.append(branch)

        # Pułapki są na brzegach lub pod spodem platform. Z czasem rośnie ich
        # liczba, ale środek platformy pozostaje możliwym miejscem lądowania.
        hazards = []
        hazard_count = min(12, max(2, difficulty + 1))
        # Golden Path nie ma kolców na górnej powierzchni lądowania. Część
        # kolców trafia pod platformy (ryzyko przy skoku), reszta na odnogi,
        # ale nie na ich końcowe platformy z nagrodą.
        for index, platform in enumerate(self.golden_path[1:]):
            if len(hazards) >= hazard_count:
                break
            if index % 2 == 0:
                hazards.append({"x": platform["x"] + platform["width"] // 2 - 12,
                                "y": platform["y"] + platform["height"],
                                "width": 24, "height": 24})
        branch_hazard_candidates = [platform for branch in branches for platform in branch[:-1]]
        for platform in branch_hazard_candidates:
            if len(hazards) >= hazard_count:
                break
            hazards.append({"x": platform["x"] + platform["width"] - 29,
                            "y": platform["y"] - 24, "width": 24, "height": 24})

        # Znajdźki są wyłącznie na bocznych platformach, dzięki czemu są
        # nagrodą za ryzyko, a nie obowiązkowym elementem ścieżki.
        collectibles = []
        for branch in branches:
            reward_platform = branch[-1]
            for offset, collectible_type in enumerate(("gem", "gem", "shield")):
                collectibles.append({"x": reward_platform["x"] + 20 + offset * 38,
                                     "y": reward_platform["y"] - 32, "type": collectible_type})

        key_platform = self.golden_path[key_index]
        buttons = [{"x": key_platform["x"] + key_platform["width"] // 2 - 20,
                    "y": key_platform["y"] - 40}]

        last = self.golden_path[-1]
        self.current_data = {
            "platforms": platforms,
            "temporal_platforms": temporal,
            "hazards": hazards,
            "collectibles": collectibles,
            "buttons": buttons,
            "start": {"x": 45, "y": 620},
            "end": {"x": min(SCREEN_WIDTH - 100, last["x"] + last["width"] // 2),
                    "y": max(100, last["y"] - 45), "locked": True},
            "difficulty_level": difficulty,
            "branches": branches,
        }
        return self.current_data

    def restart_level(self):
        return self.current_data
