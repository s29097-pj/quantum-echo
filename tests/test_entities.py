import pygame

from quantumecho_game.entities import Collectible, Hazard, Platform, Player, TemporalPlatform


def empty_collision_inputs():
    return [], [], []


def test_player_moves_right_when_right_key_is_pressed():
    player = Player(100, 100)
    class PressedKeys:
        def __getitem__(self, key):
            return key == pygame.K_RIGHT

    keys = PressedKeys()

    player.handle_input(keys)
    player.update([], [], [], [])

    assert player.rect.x == 105
    assert player.vel_x == 5


def test_player_lands_on_platform():
    player = Player(100, 40)
    platform = Platform(80, 100, 120, 20)

    for _ in range(30):
        player.update([platform], [], [], [])
        if player.on_ground:
            break

    assert player.on_ground is True
    assert player.rect.bottom == platform.rect.top
    assert player.vel_y == 0


def test_player_is_hit_by_hazard():
    player = Player(100, 100)
    hazard = Hazard(100, 100, 30, 30)

    result = player.update([], [hazard], [], [])

    assert result == "hit"


def test_player_collects_double_jump_power_up():
    player = Player(100, 100)
    collectible = Collectible(100, 100, "double_jump")
    collectibles = [collectible]

    result = player.update([], [], collectibles, [])

    assert result == "double_jump"
    assert player.has_double_jump is True
    assert collectibles == []


def test_temporal_platform_changes_state_after_duration():
    platform = TemporalPlatform(0, 0, 100, 20, initial_state="solid", solid_time=1, phased_time=1)

    platform.update()
    platform.update()

    assert platform.state == "phased"
