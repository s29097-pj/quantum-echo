"""Główna pętla gry i zarządzanie jej stanami."""

import os
from pathlib import Path
from collections import deque

import pygame

from .config import *
from .effects import ParticleSystem, Starfield
from .editor_ui import LevelEditor, delete_level, discover_levels, load_thumbnail
from .entities import Player
from .level import Level
from .arcade import ArcadeManager
from .runtime import clock, font_large, font_medium, font_small, screen
from .storage import load_level, load_ranking, save_ranking, load_settings, save_settings
from .ui import *

def main():
    # Kolejność poziomów i plik rankingu
    package_dir = os.path.dirname(__file__)
    LEVEL_ORDER = [
        os.path.join("levels", "level1.json"),
        os.path.join("levels", "level2.json"),
        os.path.join("levels", "level3.json"),
        os.path.join("levels", "level4.json"),
    ]
    campaign_levels = list(LEVEL_ORDER)
    custom_levels_dir = os.path.join(package_dir, "levels", "custom_levels")

    def refresh_level_order():
        """Dodaje zapisane poziomy użytkownika do listy treningowej."""
        custom_levels = []
        if os.path.isdir(custom_levels_dir):
            custom_levels = [
                os.path.join("levels", "custom_levels", filename)
                for filename in sorted(os.listdir(custom_levels_dir))
                if filename.lower().endswith(".json")
            ]
        LEVEL_ORDER[:] = campaign_levels + custom_levels

    def level_title(filename, index):
        if index < len(campaign_levels):
            return ["Pierwsze kroki", "Wyzwanie", "Wspinaczka", "Kwantowa Studnia"][index]
        return os.path.splitext(os.path.basename(filename))[0].replace("_", " ")

    refresh_level_order()
    RANKING_FILE = os.path.join(os.path.dirname(package_dir), "ranking.json")

    menu_options = [
        {"text": "SPACE/A - Kampania", "action": "start"},
        {"text": "ARCADE - Nieskończony tryb", "action": "arcade"},
        {"text": "S - Ustawienia", "action": "settings"},
        {"text": "I/Y - Instrukcje", "action": "instructions"},
        {"text": "R/B - Ranking", "action": "ranking"},
        {"text": "E - Edytor poziomów", "action": "editor"},
        {"text": "L/X - Wybór poziomów", "action": "browser"},
        {"text": "ESC/Back - Wyjście", "action": "exit"},
    ]

    # Zmienne gry
    state = GameState.MENU
    current_level_index = -1
    current_level = None
    current_level_filename = None
    player = None
    echo = None
    particle_system = ParticleSystem()
    starfield = Starfield(200, SCREEN_WIDTH, SCREEN_HEIGHT)
    is_training_mode = False
    is_arcade_mode = False
    arcade_manager = ArcadeManager()
    arcade_level = 0
    arcade_lives = 3
    settings_file = os.path.join(os.path.dirname(package_dir), "settings.json")
    settings = load_settings(settings_file)
    settings_menu = SettingsMenu(settings, lambda value: (save_settings(settings_file, value), apply_audio_settings(value)))

    # Audio jest częścią pakietu gry, tak jak fonty i poziomy. Dzięki temu
    # ścieżka nie zależy od katalogu roboczego, z którego uruchomiono grę.
    audio_dir = os.path.join(package_dir, "assets", "audio")
    audio_sounds = {}
    current_music = None

    def apply_audio_settings(value=None):
        value = value or settings
        try:
            pygame.mixer.music.set_volume(float(value["music_volume"]))
            for channel_index in range(pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(channel_index).set_volume(float(value["sfx_volume"]))
        except pygame.error:
            pass

    def load_audio_assets():
        for name in ("jump.wav", "collect_gem.wav", "collect_double_jump.wav",
                     "collect_shield.wav", "collect_key.wav", "gate_open.wav",
                     "death.wav", "swap.wav"):
            try:
                audio_sounds[name[:-4]] = pygame.mixer.Sound(os.path.join(audio_dir, name))
            except (pygame.error, FileNotFoundError, OSError) as error:
                # Audio jest opcjonalny: gra działa także przed uruchomieniem
                # audio_generator.py albo na systemie bez miksera.
                print(f"Błąd ładowania dźwięku '{name}': {error}")

    def play_sfx(name):
        sound = audio_sounds.get(name)
        if sound and pygame.mixer.get_init() is not None:
            try:
                sound.set_volume(float(settings["sfx_volume"]))
                # Nie używamy kanału muzycznego. find_channel(False) wybiera
                # wolny kanał i nie ucina aktywnego efektu.
                channel = pygame.mixer.find_channel(False)
                if channel:
                    channel.play(sound)
            except pygame.error as error:
                print(f"Błąd odtwarzania efektu '{name}': {error}")

    def play_music(name):
        nonlocal current_music
        if pygame.mixer.get_init() is None:
            return
        if name == current_music and pygame.mixer.music.get_busy():
            return
        filename = os.path.join(audio_dir, f"{name}_theme.wav")
        try:
            if current_music is not None:
                pygame.mixer.music.fadeout(250)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.set_volume(float(settings["music_volume"]))
            pygame.mixer.music.play(-1)
            current_music = name
        except (pygame.error, FileNotFoundError, OSError) as error:
            print(f"Błąd ładowania muzyki '{filename}': {error}")
            current_music = None

    def stop_music():
        nonlocal current_music
        if pygame.mixer.get_init() is not None and current_music is not None:
            pygame.mixer.music.fadeout(250)
        current_music = None

    load_audio_assets()
    apply_audio_settings()
    Player.set_audio_callback(play_sfx)
    play_music("menu")

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
    # Zmienne dla wirtualnej klawiatury
    virtual_keyboard_active = False
    letters = [
        ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
        ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
        ['K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T'],
        ['U', 'V', 'W', 'X', 'Y', 'Z', '.', '-', '_', '!'],
        ['CAPS', 'DEL', 'END']
    ]
    vk_selected_index = (0, 0) # Indeks zaznaczonej litery wirtualnej klawiatury
    vk_cooldown = 0
    VK_COOLDOWN_FRAMES = 8 # Czas odświeżania wirtualnej klawiatury
    is_caps_lock = True # Domyślnie włączony Caps Lock

    # Zmienne dla migającego kursora
    cursor_timer = 0
    cursor_visible = True

    # Zmienne dla systemu drugiego życia
    is_on_second_life = False
    ECHO_DELAY_FRAMES = 600
    # Stałe okno czasowe: append/popleft są O(1), a pozycję Echa pobieramy
    # z lewej strony kolejki zamiast indeksować środek deque (O(n)).
    player_history = deque(maxlen=ECHO_DELAY_FRAMES + 1)

    # Zmienne dla Zamiany Kwantowej
    swap_cooldown = 0
    SWAP_COOLDOWN_FRAMES = 180
    jump_buffer_frames = 0

    # --- OBSŁUGA KONTROLERA XBOX ---
    pygame.joystick.init()
    joysticks = []
    for i in range(pygame.joystick.get_count()):
        try:
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            joysticks.append(joystick)
        except pygame.error as e:
            print(f"Błąd inicjalizacji kontrolera {i}: {e}")
    controller = joysticks[0] if joysticks else None
    if controller:
        print(f"Wykryto kontroler: {controller.get_name()}")
    DEAD_ZONE = 0.1

    def joystick_axis(device, index):
        if device is None:
            return 0.0
        try:
            return device.get_axis(index) if index < device.get_numaxes() else 0.0
        except (pygame.error, IndexError):
            return 0.0

    def joystick_button(device, index):
        if device is None:
            return False

    def joystick_hat(device, index=0):
        try:
            return device.get_hat(index) if index < device.get_numhats() else (0, 0)
        except (pygame.error, IndexError):
            return (0, 0)
        try:
            return bool(index < device.get_numbuttons() and device.get_button(index))
        except (pygame.error, IndexError):
            return False

    # Zmienne dla kontrolera
    controller_jump_pressed = False
    controller_swap_pressed = False
    controller_pause_pressed = False
    controller_menu_pressed = False
    controller_instructions_pressed = False  # Przycisk Y
    controller_ranking_pressed = False  # Przycisk B
    controller_dpad_y_pressed = False  # Do nawigacji góra/dół w menu

    # Zmienne dla menu nawigacji
    menu_selected_index = 0
    menu_key_cooldown = 0
    level_select_selected_index = 0
    level_select_cooldown = 0
    editor_screen = LevelEditor(Path(custom_levels_dir))
    browser_selected_index = 0
    browser_scroll = 0
    browser_cooldown = 0
    browser_delete_pending = False
    browser_status = "Wybierz poziom: strzałki/D-pad, A/Enter gra, N/Y nowy, Delete/B usuń"
    thumbnail_cache = {}

    def open_editor():
        nonlocal state
        editor_screen.load()
        state = GameState.EDITOR

    def open_browser():
        nonlocal state, browser_selected_index, browser_scroll, thumbnail_cache, browser_delete_pending
        browser_selected_index = 0
        browser_scroll = 0
        browser_delete_pending = False
        thumbnail_cache = {}
        state = GameState.LEVEL_BROWSER

    def keep_browser_selection_visible(item_count):
        """Przewija widok do zaznaczonej karty, także po nawigacji padem."""
        nonlocal browser_scroll, browser_selected_index
        if not item_count:
            browser_scroll = 0
            return
        browser_selected_index = min(browser_selected_index, item_count - 1)
        row = browser_selected_index // 2
        card_top = 150 + row * 240 - browser_scroll
        if card_top < 150:
            browser_scroll += card_top - 150
        elif card_top + 220 > 700:
            browser_scroll += card_top + 220 - 700
        max_scroll = max(0, ((item_count + 1) // 2 - 2) * 240)
        browser_scroll = max(0, min(browser_scroll, max_scroll))

    # --- FUNKCJA DO OBSŁUGI WIBRACJI ---
    def set_vibration(controller, left_motor=0.0, right_motor=0.0, duration=250):
        """
        Ustawia wibracje kontrolera Xbox.
        left_motor, right_motor: wartości od 0.0 do 1.0
        duration: czas trwania w milisekundach
        """
        if controller:
            try:
                controller.rumble(left_motor, right_motor, duration)
            except AttributeError:
                # Obsługa starszych wersji Pygame lub innych kontrolerów
                pass

    # Funkcja do rozpoczęcia poziomu
    def start_level(level_filename, level_idx, training=False, level_data=None, arcade=False):
        nonlocal current_level, player, echo, is_on_second_life, player_history, level_time, state, swap_cooldown, current_level_filename, is_training_mode, swap_count, jump_buffer_frames, is_arcade_mode
        if level_data is None:
            level_path = os.path.join(package_dir, level_filename)
            level_data = load_level(level_path)
        is_training_mode = training
        is_arcade_mode = arcade
        stop_music()

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
            jump_buffer_frames = 0
            state = GameState.ARCADE if arcade else GameState.PLAYING
        else:
            state = GameState.MENU
            current_level_index = -1

    running = True
    while running:
        refresh_level_order()
        # --- OBSŁUGA KONTROLERA XBOX ---
        controller_left = False
        controller_right = False
        controller_jump_current = False
        controller_swap_current = False
        controller_pause_current = False
        controller_menu_current = False
        controller_instructions_current = False
        controller_ranking_current = False
        controller_up = False
        controller_down = False

        if controller:
            # Gałka analogowa
            left_x = joystick_axis(controller, 0)
            if left_x < -DEAD_ZONE:
                controller_left = True
            elif left_x > DEAD_ZONE:
                controller_right = True

            # D-Pad (często jako "hat")
            if controller:
                hat_x, hat_y = joystick_hat(controller)
                if hat_x == -1:
                    controller_left = True
                elif hat_x == 1:
                    controller_right = True
                if hat_y == 1:
                    controller_up = True
                elif hat_y == -1:
                    controller_down = True

            # Przyciski
            controller_jump_current = joystick_button(controller, 0)  # A
            controller_swap_current = joystick_button(controller, 2)  # X
            controller_pause_current = joystick_button(controller, 7)  # Start
            controller_menu_current = joystick_button(controller, 6)  # Back
            controller_instructions_current = joystick_button(controller, 3)  # Y
            controller_ranking_current = joystick_button(controller, 1)  # B

        # --- Obsługa zdarzeń ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif state == GameState.EDITOR:
                if editor_screen.handle_event(event) == "menu":
                    state = GameState.MENU

            elif state == GameState.LEVEL_BROWSER:
                if event.type == pygame.KEYDOWN:
                    if browser_delete_pending:
                        if event.key in (pygame.K_RETURN, pygame.K_y):
                            browser_files = discover_levels(Path(package_dir) / "levels")
                            if browser_files and browser_selected_index < len(browser_files):
                                if delete_level(browser_files[browser_selected_index], Path(custom_levels_dir)):
                                    browser_status = "Poziom usunięty wraz z miniaturą."
                                    browser_selected_index = max(0, browser_selected_index - 1)
                                else:
                                    browser_status = "Nie można usunąć poziomu kampanii."
                            browser_delete_pending = False
                        elif event.key in (pygame.K_ESCAPE, pygame.K_n):
                            browser_delete_pending = False
                            browser_status = "Usuwanie anulowane."
                    elif event.key == pygame.K_ESCAPE:
                        state = GameState.MENU
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        browser_selected_index = max(0, browser_selected_index - 1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        browser_selected_index += 1
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        browser_selected_index = max(0, browser_selected_index - 2)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        browser_selected_index += 2
                    elif event.key in (pygame.K_n, pygame.K_INSERT):
                        open_editor()
                    elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                        browser_delete_pending = True
                        browser_status = "Usunąć wybrany poziom? Enter/Y = tak, ESC/N = nie"
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        browser_files = discover_levels(Path(package_dir) / "levels")
                        if browser_files and browser_selected_index < len(browser_files):
                            current_level_index = browser_selected_index
                            start_level(os.path.relpath(browser_files[browser_selected_index], package_dir), current_level_index, training=True)
                elif event.type == pygame.MOUSEWHEEL:
                    browser_scroll = max(0, browser_scroll - event.y * 240)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    browser_files = discover_levels(Path(package_dir) / "levels")
                    card_width, card_height, gap = 560, 220, 20
                    origin_x, origin_y = 70, 150
                    if pygame.Rect(1000, 82, 240, 42).collidepoint(event.pos):
                        open_editor()
                        continue
                    column = (event.pos[0] - origin_x) // (card_width + gap)
                    row = (event.pos[1] - origin_y + browser_scroll) // (card_height + gap)
                    if 0 <= column < 2 and 0 <= row:
                        index = row * 2 + column
                        if index < len(browser_files):
                            card_x = origin_x + column * (card_width + gap)
                            card_y = origin_y + row * (card_height + gap) - browser_scroll
                            if pygame.Rect(card_x + 350, card_y + 145, 190, 35).collidepoint(event.pos):
                                browser_selected_index = index
                                if browser_delete_pending:
                                    if delete_level(browser_files[index], Path(custom_levels_dir)):
                                        browser_status = "Poziom usunięty wraz z miniaturą."
                                        browser_selected_index = max(0, browser_selected_index - 1)
                                    else:
                                        browser_status = "Nie można usunąć poziomu kampanii."
                                    browser_delete_pending = False
                                else:
                                    browser_delete_pending = True
                                    browser_status = "Kliknij ponownie lub naciśnij Enter, aby potwierdzić usunięcie."
                            else:
                                browser_selected_index = index
                                current_level_index = index
                                start_level(os.path.relpath(browser_files[index], package_dir), index, training=True)

            # --- OBSŁUGA KONTROLERA XBOX ---
            elif event.type == pygame.JOYDEVICEADDED:
                joysticks = []
                for i in range(pygame.joystick.get_count()):
                    try:
                        joystick = pygame.joystick.Joystick(i)
                        joystick.init()
                        joysticks.append(joystick)
                    except pygame.error as e:
                        print(f"Błąd inicjalizacji kontrolera {i}: {e}")
                controller = joysticks[0] if joysticks else None
                if controller:
                    print(f"Kontroler podłączony: {controller.get_name()}")

            elif event.type == pygame.JOYDEVICEREMOVED:
                joysticks = []
                for i in range(pygame.joystick.get_count()):
                    try:
                        joystick = pygame.joystick.Joystick(i)
                        joystick.init()
                        joysticks.append(joystick)
                    except pygame.error as e:
                        print(f"Błąd inicjalizacji kontrolera {i}: {e}")
                controller = joysticks[0] if joysticks else None
                if not controller:
                    print("Kontroler odłączony")

            # Obsługa zdarzeń klawiatury
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state in (GameState.PLAYING, GameState.ARCADE):
                        state = GameState.PAUSED
                    elif state in [GameState.PAUSED, GameState.INSTRUCTIONS, GameState.LEVEL_SELECT,
                                   GameState.GAME_OVER, GameState.RANKING, GameState.LEVEL_COMPLETE,
                                   GameState.TRAINING_COMPLETE, GameState.EDITOR, GameState.LEVEL_BROWSER,
                                   GameState.SETTINGS, GameState.ARCADE]:
                        state = GameState.MENU
                    elif state == GameState.MENU:
                        running = False

                # --- Obsługa przycisków w menu ---
                elif event.key == pygame.K_r and state == GameState.GAME_OVER:
                    if current_level_filename:
                        if not is_training_mode:
                            restart_penalty += 50
                            deaths += 1
                        start_level(current_level_filename, current_level_index, training=is_training_mode)

                # --- Obsługa przycisków w różnych stanach gry ---
                elif event.key == pygame.K_SPACE:
                    if state == GameState.MENU:
                        selected_action = menu_options[menu_selected_index]["action"]
                        if selected_action == "start":
                            current_level_index = 0
                            score, deaths, restart_penalty, total_swap_count = 0, 0, 0, 0
                            start_level(LEVEL_ORDER[current_level_index], current_level_index, training=False)
                        elif selected_action == "arcade":
                            arcade_lives = float("inf") if settings["lives"] == "infinite" else settings["lives"]
                            score, deaths, restart_penalty, total_swap_count = 0, 0, 0, 0
                            arcade_manager.level_number = 0
                            start_level(None, 0, level_data=arcade_manager.generate_level(), arcade=True)
                        elif selected_action == "settings":
                            settings_menu.selected = 0
                            state = GameState.SETTINGS
                        elif selected_action == "instructions":
                            state = GameState.INSTRUCTIONS
                        elif selected_action == "ranking":
                            state = GameState.RANKING
                        elif selected_action == "editor":
                            open_editor()
                        elif selected_action == "browser":
                            open_browser()
                        elif selected_action == "exit":
                            running = False
                        menu_key_cooldown = 10
                    elif state == GameState.PAUSED:
                        state = GameState.ARCADE if is_arcade_mode else GameState.PLAYING
                    elif state == GameState.LEVEL_COMPLETE:
                        current_level_index += 1
                        if current_level_index < len(LEVEL_ORDER):
                            start_level(LEVEL_ORDER[current_level_index], current_level_index, training=False)
                        else:
                            state = GameState.GAME_COMPLETE
                            input_active = True
                    elif state in (GameState.PLAYING, GameState.ARCADE) and player:
                        if not player.jump():
                            jump_buffer_frames = 3
                    elif state == GameState.TRAINING_COMPLETE:
                        state = GameState.MENU
                    elif state == GameState.SETTINGS:
                        settings_menu.activate()

                # --- Obsługa Zamiany Kwantowej ---
                elif event.key == pygame.K_q and state in (GameState.PLAYING, GameState.ARCADE):
                    if player and echo and swap_cooldown == 0 and not is_on_second_life:
                        player.rect, echo.rect = echo.rect, player.rect
                        swap_cooldown = SWAP_COOLDOWN_FRAMES
                        swap_count += 1
                        play_sfx("swap")
                        particle_system.add_burst(player.rect.centerx, player.rect.centery, PURPLE, 40)
                        particle_system.add_burst(echo.rect.centerx, echo.rect.centery, PURPLE, 40)
                        set_vibration(controller, left_motor=0.5, right_motor=0.5, duration=300)

                # --- Obsługa innych klawiszy ---
                elif event.key == pygame.K_i and state == GameState.MENU:
                    state = GameState.INSTRUCTIONS

                elif event.key == pygame.K_l and state == GameState.MENU:
                    open_browser()

                elif event.key == pygame.K_r and state == GameState.MENU:
                    state = GameState.RANKING

                elif event.key == pygame.K_e and state == GameState.MENU:
                    open_editor()

                elif event.key == pygame.K_s and state == GameState.MENU:
                    settings_menu.selected = 0
                    state = GameState.SETTINGS

                elif state == GameState.SETTINGS:
                    if settings_menu.handle_key(event.key) == "back":
                        save_settings(settings_file, settings)
                        state = GameState.MENU

                elif event.key == pygame.K_b and state == GameState.MENU:
                    open_browser()

                # --- Obsługa poziomów w trybie treningowym ---
                elif state == GameState.LEVEL_SELECT:
                    number_keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                   pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]
                    new_index = number_keys.index(event.key) if event.key in number_keys else -1
                    if 0 <= new_index < len(LEVEL_ORDER):
                        current_level_index = new_index
                        start_level(LEVEL_ORDER[current_level_index], current_level_index, training=True)

                elif state == GameState.TRAINING_COMPLETE:
                    if event.key == pygame.K_l:
                        open_browser()
                    elif event.key == pygame.K_ESCAPE:
                        state = GameState.MENU

                # --- Obsługa wprowadzania nazwy gracza ---
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

        # --- OBSŁUGA PRZYCISKÓW KONTROLERA (naciśnięcie) ---
        if controller:
            # Menu/ESC (Back button)
            if controller_menu_current and not controller_menu_pressed:
                if state in (GameState.PLAYING, GameState.ARCADE):
                    state = GameState.PAUSED
                elif state in [GameState.PAUSED, GameState.INSTRUCTIONS, GameState.LEVEL_SELECT, GameState.GAME_OVER,
                               GameState.RANKING, GameState.LEVEL_COMPLETE, GameState.TRAINING_COMPLETE,
                               GameState.EDITOR, GameState.LEVEL_BROWSER, GameState.SETTINGS]:
                    if state == GameState.LEVEL_BROWSER and browser_delete_pending:
                        browser_delete_pending = False
                        browser_status = "Usuwanie anulowane."
                    else:
                        state = GameState.MENU
                elif state == GameState.MENU:
                    running = False

            # Skok/Akcja (A button)
            if controller_jump_current and not controller_jump_pressed:
                if state == GameState.MENU:
                    selected_action = menu_options[menu_selected_index]["action"]
                    if selected_action == "start":
                        current_level_index = 0
                        score, deaths, restart_penalty, total_swap_count = 0, 0, 0, 0
                        start_level(LEVEL_ORDER[current_level_index], current_level_index, training=False)
                    elif selected_action == "arcade":
                        arcade_lives = float("inf") if settings["lives"] == "infinite" else settings["lives"]
                        score, deaths, restart_penalty, total_swap_count = 0, 0, 0, 0
                        arcade_manager.level_number = 0
                        start_level(None, 0, level_data=arcade_manager.generate_level(), arcade=True)
                    elif selected_action == "settings":
                        settings_menu.selected = 0
                        state = GameState.SETTINGS
                    elif selected_action == "instructions":
                        state = GameState.INSTRUCTIONS
                    elif selected_action == "ranking":
                        state = GameState.RANKING
                    elif selected_action == "editor":
                        open_editor()
                    elif selected_action == "browser":
                        open_browser()
                    elif selected_action == "exit":
                        running = False
                elif state == GameState.PAUSED:
                    state = GameState.ARCADE if is_arcade_mode else GameState.PLAYING
                elif state == GameState.LEVEL_COMPLETE:
                    current_level_index += 1
                    if current_level_index < len(LEVEL_ORDER):
                        start_level(LEVEL_ORDER[current_level_index], current_level_index, training=False)
                    else:
                        state = GameState.GAME_COMPLETE
                        input_active = True
                elif state in (GameState.PLAYING, GameState.ARCADE) and player:
                    if not player.jump():
                        jump_buffer_frames = 3
                elif state == GameState.TRAINING_COMPLETE:
                    state = GameState.MENU
                elif state == GameState.LEVEL_BROWSER:
                    if browser_delete_pending:
                        browser_files = discover_levels(Path(package_dir) / "levels")
                        if browser_files and browser_selected_index < len(browser_files):
                            if delete_level(browser_files[browser_selected_index], Path(custom_levels_dir)):
                                browser_status = "Poziom usunięty wraz z miniaturą."
                                browser_selected_index = max(0, browser_selected_index - 1)
                            else:
                                browser_status = "Nie można usunąć poziomu kampanii."
                        browser_delete_pending = False
                    else:
                        browser_files = discover_levels(Path(package_dir) / "levels")
                        if browser_files and browser_selected_index < len(browser_files):
                            current_level_index = browser_selected_index
                            start_level(os.path.relpath(browser_files[browser_selected_index], package_dir), current_level_index, training=True)

            # Obsługa pozostałych opcji w menu
            if state == GameState.MENU:
                if controller_instructions_current and not controller_instructions_pressed:
                    state = GameState.INSTRUCTIONS
                if controller_swap_current and not controller_swap_pressed:  # X button
                    open_browser()
                if controller_ranking_current and not controller_ranking_pressed:  # B button
                    state = GameState.RANKING

            if state == GameState.SETTINGS:
                if menu_key_cooldown > 0:
                    menu_key_cooldown -= 1
                elif controller_up or controller_down:
                    settings_menu.move(-1 if controller_up else 1)
                    menu_key_cooldown = 10
                elif controller_left or controller_right:
                    settings_menu.adjust(-1 if controller_left else 1)
                    menu_key_cooldown = 10
                if controller_jump_current and not controller_jump_pressed:
                    settings_menu.activate()

            # Nawigacja i akcje przeglądarki poziomów.
            if state == GameState.LEVEL_BROWSER:
                if browser_cooldown > 0:
                    browser_cooldown -= 1
                if browser_cooldown == 0 and (controller_left or controller_right or controller_up or controller_down):
                    if controller_left or controller_up:
                        browser_selected_index = max(0, browser_selected_index - (2 if controller_up else 1))
                    else:
                        browser_selected_index += 2 if controller_down else 1
                    browser_cooldown = 10
                if controller_instructions_current and not controller_instructions_pressed:
                    open_editor()
                if controller_ranking_current and not controller_ranking_pressed:
                    browser_delete_pending = True
                    browser_status = "A = potwierdź usunięcie, Back = anuluj"

            # Zamiana kwantowa (X button)
            if controller_swap_current and not controller_swap_pressed and state in (GameState.PLAYING, GameState.ARCADE):
                if player and echo and swap_cooldown == 0 and not is_on_second_life:
                    player.rect, echo.rect = echo.rect, player.rect
                    swap_cooldown = SWAP_COOLDOWN_FRAMES
                    swap_count += 1
                    play_sfx("swap")
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, PURPLE, 40)
                    particle_system.add_burst(echo.rect.centerx, echo.rect.centery, PURPLE, 40)
                    # Dodaj wibracje przy zamianie kwantowej
                    set_vibration(controller, left_motor=0.5, right_motor=0.5, duration=300)

            # Pauza (Start button)
            if controller_pause_current and not controller_pause_pressed:
                if state in (GameState.PLAYING, GameState.ARCADE):
                    state = GameState.PAUSED
                elif state == GameState.PAUSED:
                    state = GameState.ARCADE if is_arcade_mode else GameState.PLAYING
                elif state == GameState.GAME_OVER and current_level_filename:
                    if not is_training_mode:
                        restart_penalty += 50
                        deaths += 1
                    start_level(current_level_filename, current_level_index, training=is_training_mode)

        # Aktualizuj stan przycisków
        controller_jump_pressed = controller_jump_current
        controller_swap_pressed = controller_swap_current
        controller_pause_pressed = controller_pause_current
        controller_menu_pressed = controller_menu_current
        controller_instructions_pressed = controller_instructions_current
        controller_ranking_pressed = controller_ranking_current

        # Powrót do menu po śmierci/pauzie przywraca motyw menu, a wejście do
        # Arcade zawsze zapewnia motyw arcade nawet przy przejściu z innego
        # ekranu bez ponownego uruchamiania aplikacji.
        if state in (GameState.PLAYING, GameState.ARCADE):
            stop_music()
        elif state in (GameState.MENU, GameState.SETTINGS, GameState.INSTRUCTIONS,
                       GameState.RANKING, GameState.GAME_OVER):
            play_music("menu")

        # --- Aktualizacja logiki gry ---
        player_vel_x_for_parallax = 0
        if state in (GameState.PLAYING, GameState.ARCADE) and player and current_level:
            level_time += 1
            if swap_cooldown > 0:
                swap_cooldown -= 1

            keys = pygame.key.get_pressed()

            if jump_buffer_frames > 0:
                jump_buffer_frames -= 1

            # --- INTEGRACJA KONTROLERA Z RUCHEM ---
            # Bezpieczniejsza integracja kontrolera
            left_pressed = keys[pygame.K_LEFT] or keys[pygame.K_a] or controller_left
            right_pressed = keys[pygame.K_RIGHT] or keys[pygame.K_d] or controller_right

            # Tworzymy własny obiekt klawiszy
            class KeyState:
                def __getitem__(self, key):
                    if key == pygame.K_LEFT or key == pygame.K_a:
                        return left_pressed
                    elif key == pygame.K_RIGHT or key == pygame.K_d:
                        return right_pressed
                    # Dla innych klawiszy zwracamy False (lub oryginalną wartość jeśli istnieje)
                    return False

            # --- Aktualizacja gracza ---
            player.handle_input(KeyState())
            player_vel_x_for_parallax = player.vel_x

            # Świat aktualizujemy przed wyznaczeniem kolizji. Dzięki temu
            # cache platform jest ważny przez całą klatkę.
            current_level.update(player_vel_x_for_parallax, player.vel_y)

            # Sprawdzenie, czy gracz ma drugie życie
            # Ograniczenie historii gracza do ostatnich ECHO_DELAY_FRAMES
            solid_platforms = current_level.get_solid_platforms()
            result = player.update(solid_platforms, current_level.hazards,
                                   current_level.collectibles, current_level.keys,
                                   time_dilation_zones=current_level.time_dilation_zones)

            if not is_on_second_life:
                # Zapisujemy stan po fizyce, dzięki czemu Echo odtwarza pełną
                # klatkę i nie wymaga kosztownego wyszukiwania w deque.
                player_history.append(player.rect.topleft)

            # Jeśli skok został wciśnięty tuż przed lądowaniem, wykonaj go
            # natychmiast po wykryciu podłoża.
            if jump_buffer_frames > 0 and player.jump():
                jump_buffer_frames = 0

            # Sprawdzenie, czy gracz zginął lub zebrał przedmiot
            if result == "hit" or result == "fell":
                if is_arcade_mode:
                    deaths += 1
                    play_sfx("death")
                    if arcade_lives != float("inf"):
                        arcade_lives -= 1
                    set_vibration(controller, left_motor=1.0, right_motor=1.0, duration=800)
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, RED, 30)
                    if arcade_lives == float("inf") or arcade_lives > 0:
                        start_level(None, arcade_manager.level_number - 1,
                                    level_data=arcade_manager.restart_level(), arcade=True)
                    else:
                        state = GameState.GAME_OVER
                elif not is_on_second_life and echo:
                    # Gracz umiera, ale ma Echo
                    play_sfx("death")
                    is_on_second_life = True
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, CYAN, 50)
                    # Dodaj wibracje przy śmierci
                    set_vibration(controller, left_motor=0.5, right_motor=0.5, duration=500)

                    # Przeniesienie stanu gracza do Echa
                    echo.has_double_jump = player.has_double_jump
                    echo.invincible = player.invincible
                    echo.invincible_timer = player.invincible_timer

                    # Przeniesienie historii gracza do Echa
                    player, echo = echo, player
                    player.is_echo = False
                    player.color = BLUE
                    player.image.fill(player.color)

                    echo = None  # Usuń Echo, aby nie było już aktywne
                else:
                    if not is_training_mode:
                        deaths += 1
                    play_sfx("death")
                    # Dodaj wibracje przy śmierci
                    set_vibration(controller, left_motor=1.0, right_motor=1.0, duration=800)
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, RED, 30)
                    state = GameState.GAME_OVER

            # Sprawdzenie, czy gracz zebrał przedmiot
            elif result == "gem":
                if not is_training_mode: score += 100
                particle_system.add_burst(player.rect.centerx, player.rect.centery, YELLOW, 15)
                # Dodaj wibracje przy zbieraniu klejnotu
                set_vibration(controller, left_motor=0.3, right_motor=0.3, duration=200)

            elif result == "double_jump":
                if not is_training_mode: score += 50
                particle_system.add_burst(player.rect.centerx, player.rect.centery, PURPLE, 20)
                # Dodaj wibracje przy podwójnym skoku
                set_vibration(controller, left_motor=0.4, right_motor=0.4, duration=200)

            elif result == "shield":
                particle_system.add_burst(player.rect.centerx, player.rect.centery, ORANGE, 25)
                # Dodaj wibracje przy tarczy
                set_vibration(controller, left_motor=0.5, right_motor=0.5, duration=300)

            # Sprawdzenie, czy gracz zebrał klucz
            if echo:
                history_pos = player_history[0] if len(player_history) == player_history.maxlen else None
                echo.update(solid_platforms, [], [], [], history_pos=history_pos,
                            paradox_switches=current_level.paradox_switches)

            particle_system.update()

            # Sprawdzenie, czy gracz dotarł do strefy wyjścia
            if player.rect.colliderect(current_level.exit_zone.rect) and not current_level.exit_zone.locked:
                if is_training_mode:
                    state = GameState.TRAINING_COMPLETE
                elif is_arcade_mode:
                    score += 1000
                    total_swap_count += swap_count
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, GREEN, 100)
                    start_level(None, arcade_manager.level_number,
                                level_data=arcade_manager.generate_level(), arcade=True)
                else:
                    state = GameState.LEVEL_COMPLETE
                    score += 1000
                    total_swap_count += swap_count
                    particle_system.add_burst(player.rect.centerx, player.rect.centery, GREEN, 100)
        else:
            starfield.update(1)

        # --- Rysowanie ---
        screen.fill(BLACK)

        # Rysowanie tła
        if state in (GameState.PLAYING, GameState.ARCADE):
            if current_level:
                # Tło musi być pierwszą warstwą sceny po wyczyszczeniu ekranu.
                current_level.background.draw(screen)
                current_level.draw(screen, draw_background=False)
            if player: player.draw(screen)
            if echo: echo.draw(screen)
            particle_system.draw(screen)
            gems_left = len([c for c in current_level.collectibles if c.type == "gem"])
            draw_hud(screen, player, gems_left, not is_on_second_life, level_time, swap_cooldown,
                     arcade_lives if is_arcade_mode else None,
                     arcade_manager.level_number if is_arcade_mode else None)

        # --- Rysowanie innych stanów gry ---
        elif state == GameState.SETTINGS:
            settings_menu.draw(screen)

        elif state == GameState.MENU:
            starfield.draw(screen)

            # --- Menu z nawigacją ---
            # Obsługa nawigacji w menu (klawiatura i kontroler)
            if menu_key_cooldown > 0:
                menu_key_cooldown -= 1

            # Obsługa D-Pad / strzałek góra/dół
            keys = pygame.key.get_pressed()
            if (keys[pygame.K_DOWN] or keys[pygame.K_s] or controller_down) and menu_key_cooldown == 0:
                menu_selected_index = (menu_selected_index + 1) % len(menu_options)
                menu_key_cooldown = 10
            if (keys[pygame.K_UP] or keys[pygame.K_w] or controller_up) and menu_key_cooldown == 0:
                menu_selected_index = (menu_selected_index - 1) % len(menu_options)
                menu_key_cooldown = 10

            # Obsługa potwierdzenia opcji (ENTER / A)
            if keys[pygame.K_RETURN] or keys[pygame.K_SPACE] or keys[pygame.K_a] or joystick_button(controller, 0):
                if menu_key_cooldown == 0:  # Zapobiegaj podwójnemu wyborowi
                    selected = menu_options[menu_selected_index]["action"]
                    if selected == "start":
                        current_level_index = 0
                        score, deaths, restart_penalty, total_swap_count = 0, 0, 0, 0
                        start_level(LEVEL_ORDER[current_level_index], current_level_index, training=False)
                    elif selected == "arcade":
                        arcade_lives = float("inf") if settings["lives"] == "infinite" else settings["lives"]
                        score, deaths, restart_penalty, total_swap_count = 0, 0, 0, 0
                        arcade_manager.level_number = 0
                        start_level(None, 0, level_data=arcade_manager.generate_level(), arcade=True)
                    elif selected == "settings":
                        settings_menu.selected = 0
                        state = GameState.SETTINGS
                    elif selected == "instructions":
                        state = GameState.INSTRUCTIONS
                        menu_selected_index = 0  # Resetuj wybór przy wyjściu z menu
                    elif selected == "ranking":
                        state = GameState.RANKING
                    elif selected == "editor":
                        open_editor()
                    elif selected == "browser":
                        open_browser()
                    elif selected == "exit":
                        running = False
                    menu_key_cooldown = 10  # Zapobiegaj natychmiastowemu ponownemu wyborowi

            # --- Rysowanie menu ---
            text_color = (230, 230, 240)
            shadow_color = (40, 40, 50)
            highlight_color = CYAN

            draw_pixel_text(screen, "Quantum Echo", font_large, (SCREEN_WIDTH // 2, 150), PURPLE, shadow_color)
            draw_pixel_text(screen, "Manipuluj czasem!", font_medium, (SCREEN_WIDTH // 2, 230), highlight_color,
                            shadow_color)

            # Rysowanie opcji menu
            menu_y_start = 320
            menu_y_spacing = 50
            for i, option in enumerate(menu_options):
                color = highlight_color if i == menu_selected_index else text_color
                draw_pixel_text(screen, option["text"], font_medium,
                                (SCREEN_WIDTH // 2, menu_y_start + i * menu_y_spacing), color, shadow_color)

            draw_pixel_text(screen, "Produkcja: Cybermich 2025", font_small, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40),
                            GRAY, shadow_color)

        # Rysowanie instrukcji
        elif state == GameState.INSTRUCTIONS:
            starfield.draw(screen)
            text_color = (230, 230, 240)
            shadow_color = (40, 40, 50)
            highlight_color = CYAN

            draw_pixel_text(screen, "Instrukcje", font_large, (SCREEN_WIDTH // 2, 100), YELLOW, shadow_color)

            instructions = [
                "Sterowanie:", "A/D lub Strzałki/Gałka - Ruch", "SPACJA/A - Skok", "",
                "Mechaniki Kwantowe:",
                "Q/X - Zamiana z Echem. Użyj jej, by uciec z opresji!",
                "Twoje Echo podąża za Tobą z 10-sekundowym opóźnieniem.",
                "Gdy zginiesz, przejmujesz nad nim kontrolę!", "",
                "ESC/Back - Powrót do menu"
            ]
            y = 220
            for line in instructions:
                if line in ["Sterowanie:", "Mechaniki Kwantowe:"]:
                    current_color = highlight_color
                elif line == "ESC/Back - Powrót do menu":
                    current_color = ORANGE
                else:
                    current_color = text_color

                if line:
                    draw_pixel_text(screen, line, font_small, (SCREEN_WIDTH // 2, y), current_color, shadow_color)

                y += 35

        # Poziomy gry
        elif state == GameState.LEVEL_SELECT:
            starfield.draw(screen)

            # Obsługa nawigacji w wyborze poziomów
            level_options = [
                {
                    "text": f"{index + 1} {'Poziom' if index < len(campaign_levels) else 'Custom'}: {level_title(filename, index)}",
                    "level": index,
                }
                for index, filename in enumerate(LEVEL_ORDER)
            ]

            if level_select_cooldown > 0:
                level_select_cooldown -= 1

            # Obsługa D-Pad / strzałek góra/dół w wyborze poziomów
            keys = pygame.key.get_pressed()
            if (keys[pygame.K_DOWN] or controller_down) and level_select_cooldown == 0:
                level_select_selected_index = (level_select_selected_index + 1) % len(level_options)
                level_select_cooldown = 10
            if (keys[pygame.K_UP] or controller_up) and level_select_cooldown == 0:
                level_select_selected_index = (level_select_selected_index - 1) % len(level_options)
                level_select_cooldown = 10

            # Obsługa potwierdzenia wyboru poziomu
            if keys[pygame.K_RETURN] or keys[pygame.K_SPACE] or joystick_button(controller, 0):
                if level_select_cooldown == 0:
                    selected_level = level_options[level_select_selected_index]["level"]
                    current_level_index = selected_level
                    start_level(LEVEL_ORDER[current_level_index], current_level_index, training=True)
                    level_select_cooldown = 10

            draw_text("Wybierz poziom:", font_large, GREEN, screen, SCREEN_WIDTH // 2, 100, center=True)
            draw_text("Tryb Treningowy pozwala na naukę mechanik gry", font_medium, GRAY, screen, SCREEN_WIDTH // 2,
                      150, center=True)

            # Rysowanie opcji poziomów z podświetleniem
            y_start = 250
            y_spacing = 60
            for i, option in enumerate(level_options):
                color = CYAN if i == level_select_selected_index else WHITE
                draw_text(option["text"], font_medium, color, screen, SCREEN_WIDTH // 2, y_start + i * y_spacing,
                          center=True)

            draw_text("ESC/Back - Powrót do menu", font_small, ORANGE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
                      center=True)

        elif state == GameState.EDITOR:
            editor_screen.draw(screen, font_small)

        elif state == GameState.LEVEL_BROWSER:
            browser_files = discover_levels(Path(package_dir) / "levels")
            if browser_files:
                browser_selected_index = min(browser_selected_index, len(browser_files) - 1)
            else:
                browser_selected_index = 0
            keep_browser_selection_visible(len(browser_files))
            max_scroll = max(0, ((len(browser_files) + 1) // 2 - 2) * 240)
            browser_scroll = min(browser_scroll, max_scroll)
            screen.fill((16, 20, 34))
            draw_text("PRZEGLĄDARKA POZIOMÓW", font_large, CYAN, screen, SCREEN_WIDTH // 2, 70, center=True)
            draw_text("Kliknij miniaturę, aby rozpocząć | ESC: menu", font_small, GRAY,
                      screen, SCREEN_WIDTH // 2, 112, center=True)
            pygame.draw.rect(screen, (45, 105, 85), (1000, 82, 240, 42), border_radius=5)
            draw_text("+ NOWY POZIOM (N / Y)", font_small, WHITE, screen, 1120, 103, center=True)
            card_width, card_height, gap = 560, 220, 20
            origin_x, origin_y = 70, 150
            for index, level_path in enumerate(browser_files):
                column, row = index % 2, index // 2
                rect = pygame.Rect(origin_x + column * (card_width + gap),
                                   origin_y + row * (card_height + gap) - browser_scroll, card_width, card_height)
                selected = index == browser_selected_index
                pygame.draw.rect(screen, (45, 55, 82) if selected else (30, 36, 58), rect, border_radius=8)
                cache_key = str(level_path)
                if cache_key not in thumbnail_cache:
                    thumbnail_cache[cache_key] = load_thumbnail(level_path)
                thumbnail = thumbnail_cache[cache_key]
                if thumbnail:
                    preview = pygame.transform.scale(thumbnail, (320, 180))
                    screen.blit(preview, (rect.x + 12, rect.y + 12))
                title = level_path.stem.replace("_", " ")
                draw_text(title, font_medium, WHITE, screen, rect.x + 350, rect.y + 45)
                draw_text("KLIKNIJ, ABY GRAĆ", font_small, GREEN, screen, rect.x + 350, rect.y + 95)
                try:
                    deletable = level_path.resolve().relative_to(Path(custom_levels_dir).resolve()) is not None
                except ValueError:
                    deletable = False
                if deletable:
                    pygame.draw.rect(screen, (115, 45, 55), (rect.x + 350, rect.y + 145, 190, 35), border_radius=4)
                    draw_text("USUŃ (DELETE / B)", font_small, WHITE, screen, rect.x + 445, rect.y + 163, center=True)
            draw_text(browser_status, font_small, YELLOW if browser_delete_pending else GRAY,
                      screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 22, center=True)
            if not browser_files:
                draw_text("Brak plików JSON w folderze levels.", font_medium, WHITE,
                          screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)

        # Pauza
        elif state == GameState.PAUSED:
            if current_level:
                current_level.background.draw(screen)
                current_level.draw(screen, draw_background=False)
            if player: player.draw(screen)
            if echo: echo.draw(screen)
            particle_system.draw(screen)
            gems_left = len([c for c in current_level.collectibles if c.type == "gem"]) if current_level else 0
            if player:
                draw_hud(screen, player, gems_left, not is_on_second_life, level_time, swap_cooldown,
                         arcade_lives if is_arcade_mode else None,
                         arcade_manager.level_number if is_arcade_mode else None)

            pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT));
            pause_overlay.set_alpha(180);
            pause_overlay.fill(BLACK)
            screen.blit(pause_overlay, (0, 0))
            draw_text("PAUZA", font_large, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, center=True)
            draw_text("SPACE/A - Kontynuuj", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                      center=True)
            draw_text("ESC/Back - Wyjdź do Menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2,
                      SCREEN_HEIGHT // 2 + 50, center=True)

        elif state == GameState.GAME_OVER:
            starfield.draw(screen)
            draw_text("KONIEC GRY", font_large, RED, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, center=True)
            if is_arcade_mode:
                draw_text(f"Pokonane poziomy: {max(0, arcade_manager.level_number - 1)}", font_medium, WHITE,
                          screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
                draw_text(f"Śmierci: {deaths}", font_medium, WHITE, screen, SCREEN_WIDTH // 2,
                          SCREEN_HEIGHT // 2 + 55, center=True)
                draw_text("ESC/Back - Menu Główne", font_medium, WHITE, screen, SCREEN_WIDTH // 2,
                          SCREEN_HEIGHT // 2 + 150, center=True)
            elif is_training_mode:
                draw_text("Tryb Treningowy", font_medium, CYAN, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                          center=True)
                draw_text("R/Start - Restart Poziomu", font_medium, WHITE, screen, SCREEN_WIDTH // 2,
                          SCREEN_HEIGHT // 2 + 150, center=True)
            else:
                draw_text(f"Wynik: {score - restart_penalty}", font_medium, WHITE, screen, SCREEN_WIDTH // 2,
                          SCREEN_HEIGHT // 2, center=True)
                draw_text(f"Śmierci: {deaths}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50,
                          center=True)
                draw_text("R/Start - Restart Poziomu (-50 pkt)", font_medium, WHITE, screen, SCREEN_WIDTH // 2,
                          SCREEN_HEIGHT // 2 + 150, center=True)
            draw_text("ESC/Back - Menu Główne", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 200,
                      center=True)

        # --- Wyświetlanie wyników poziomu ---
        elif state == GameState.LEVEL_COMPLETE:
            starfield.draw(screen)
            y_pos = SCREEN_HEIGHT // 2 - 150
            draw_text("POZIOM UKOŃCZONY!", font_large, GREEN, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 80
            draw_text(f"Wynik: {score - restart_penalty}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos,
                      center=True)
            y_pos += 50
            draw_text(f"Czas: {level_time // 60}s", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text(f"Użyte zamiany: {swap_count}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            if restart_penalty > 0:
                y_pos += 50
                draw_text(f"Kara za restarty: -{restart_penalty} pkt", font_medium, RED, screen, SCREEN_WIDTH // 2,
                          y_pos, center=True)
            y_pos += 40
            draw_text("SPACE/A - Następny poziom", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text("ESC/Back - Wyjdź do Menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)

        # --- Tryb treningowy ---
        elif state == GameState.TRAINING_COMPLETE:
            starfield.draw(screen)
            draw_text("TRENING UKOŃCZONY", font_large, GREEN, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
                      center=True)
            draw_text("L - Wybierz inny poziom", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50,
                      center=True)
            draw_text("ESC/Back - Powrót do menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2,
                      SCREEN_HEIGHT // 2 + 100, center=True)

        # --- Podsumowanie gry ---
        elif state == GameState.GAME_COMPLETE:
            starfield.draw(screen)
            if not virtual_keyboard_active:
                virtual_keyboard_active = True # Aktywuj klawiaturę przy pierwszym wejściu

            # --- Logika migającego kursora ---
            cursor_timer += 1
            if cursor_timer > FPS / 2: # Miganie co pół sekundy
                cursor_visible = not cursor_visible
                cursor_timer = 0
                cursor_color = YELLOW if cursor_visible else BLACK

            # --- Logika wirtualnej klawiatury ---
            if vk_cooldown > 0:
                vk_cooldown -= 1

            if virtual_keyboard_active and controller and vk_cooldown == 0:
                hat_x, hat_y = joystick_hat(controller)
                row, col = vk_selected_index

                # Nawigacja D-padem
                if hat_y == 1:  # Góra
                    vk_selected_index = (max(0, row - 1), col)
                    vk_cooldown = VK_COOLDOWN_FRAMES
                elif hat_y == -1: # Dół
                    vk_selected_index = (min(len(letters) - 1, row + 1), col)
                    vk_cooldown = VK_COOLDOWN_FRAMES
                elif hat_x == -1: # Lewo
                    vk_selected_index = (row, max(0, col - 1))
                    vk_cooldown = VK_COOLDOWN_FRAMES
                elif hat_x == 1:  # Prawo
                    vk_selected_index = (row, min(len(letters[row]) - 1, col + 1))
                    vk_cooldown = VK_COOLDOWN_FRAMES

                # Zatwierdzenie litery (przycisk A)
                if joystick_button(controller, 0) and not controller_jump_pressed:
                    # Upewnij się, że indeks jest w granicach
                    if row < len(letters) and col < len(letters[row]):
                        selected_item = letters[row][col]

                        if selected_item == 'CAPS':
                            is_caps_lock = not is_caps_lock
                        elif selected_item == 'DEL':
                            player_name = player_name[:-1]
                        elif selected_item == 'END':
                            if player_name:
                                final_score = score - restart_penalty
                                ranking.append({"name": player_name, "score": final_score})
                                save_ranking(RANKING_FILE, ranking)
                                state = GameState.RANKING
                                virtual_keyboard_active = False
                        elif len(player_name) < 10:  # Ograniczenie długości imienia
                            letter_to_add = selected_item
                            if letter_to_add.isalpha(): # Sprawdź czy to litera
                                player_name += letter_to_add.upper() if is_caps_lock else letter_to_add.lower()
                            else: # Dla symboli jak '.', '-'
                                player_name += letter_to_add

                        vk_cooldown = VK_COOLDOWN_FRAMES * 2  # Dłuższy cooldown po akcji

            # --- Rysowanie ekranu podsumowania ---
            y_pos = 80
            draw_text("GRATULACJE!", font_large, GREEN, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 70
            final_score = score - restart_penalty
            draw_text(f"Ostateczny wynik: {final_score}", font_medium, YELLOW, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text(f"Suma śmierci: {deaths}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50
            draw_text(f"Suma zamian: {total_swap_count}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 80
            draw_text("Wpisz swoje imię:", font_medium, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)
            y_pos += 50

            # Pole do wpisywania imienia z kursorem
            input_box_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, y_pos, 400, 50)
            pygame.draw.rect(screen, WHITE, input_box_rect, 2)

            # Rysuj tekst gracza
            player_text_surf = font_medium.render(player_name, True, WHITE)
            player_text_rect = player_text_surf.get_rect(center=input_box_rect.center)
            screen.blit(player_text_surf, player_text_rect)

            # Rysuj migający kursor na końcu tekstu
            if cursor_visible:
                cursor_x = player_text_rect.right + 2 if player_name else input_box_rect.centerx
                cursor_y = input_box_rect.centery
                cursor_rect = pygame.Rect(cursor_x, cursor_y - 20, 4, 40)
                pygame.draw.rect(screen, WHITE, cursor_rect)

            y_pos += 70

            # Rysowanie wirtualnej klawiatury
            if virtual_keyboard_active:
                # Tworzenie tablicy liter do wyświetlenia na podstawie stanu Caps Lock
                display_letters = []
                for row_items in letters:
                    new_row = []
                    for item in row_items:
                        if len(item) == 1 and item.isalpha(): # Zmieniaj tylko pojedyncze litery
                            new_row.append(item.upper() if is_caps_lock else item.lower())
                        else:
                            new_row.append(item) # Zostaw 'DEL', 'END', 'CAPS' bez zmian
                    display_letters.append(new_row)

                draw_virtual_keyboard(screen, display_letters, vk_selected_index, font_medium, SCREEN_WIDTH // 2, y_pos, 60, YELLOW, WHITE)

            y_pos += 300
            draw_text("Wybierz END, aby zapisać", font_small, WHITE, screen, SCREEN_WIDTH // 2, y_pos, center=True)

        # Ranking
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
            draw_text("ESC/Back - Powrót do menu", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
                      center=True)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
