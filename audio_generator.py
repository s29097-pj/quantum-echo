"""Minimalny generator retro audio dla Quantum Echo.

Uruchom:
    python audio_generator.py

Generuje 8-bitowe, jednowątkowe PCM WAV bez bibliotek zewnętrznych.
"""

import math
import os
import struct
import wave


SAMPLE_RATE = 44100
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "quantumecho_game/assets", "audio")


def _note_frequency(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _sample(frequency, time, waveform="square"):
    phase = (frequency * time) % 1.0
    if waveform == "sine":
        return math.sin(2.0 * math.pi * phase)
    return 1.0 if phase < 0.5 else -1.0


def _render(notes, waveform="square", note_length=0.16, volume=0.28):
    frames = bytearray()
    for note, duration in notes:
        frequency = _note_frequency(note) if note else 0.0
        sample_count = int(SAMPLE_RATE * duration)
        for index in range(sample_count):
            time = index / SAMPLE_RATE
            value = 0.0 if not frequency else _sample(frequency, time, waveform)
            # Krótki attack/release ogranicza trzaski na granicach nut.
            envelope = min(1.0, index / max(1, SAMPLE_RATE * 0.008))
            envelope *= min(1.0, (sample_count - index) / max(1, SAMPLE_RATE * 0.015))
            pcm = int(32767 * volume * value * envelope)
            # 16-bit signed little-endian PCM, stereo interleaved. To jest
            # standardowy, bezkompresyjny format zgodny z mikserem Pygame.
            pcm = max(-32768, min(32767, pcm))
            frames.extend(struct.pack("<hh", pcm, pcm))
    return bytes(frames)


def _write_wav(filename, frames):
    with wave.open(filename, "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)


def generate_audio(output_dir=OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)

    # Spokojne, sine-wave'owe arpeggio: dłuższe nuty i duży oddech między
    # frazami sprawiają, że menu nie męczy przy wielokrotnym słuchaniu.
    menu_melody = [
        (60, 0.32), (64, 0.32), (67, 0.42), (None, 0.18),
        (59, 0.32), (62, 0.32), (67, 0.42), (None, 0.24),
    ] * 2
    arcade_melody = [(72, 0.09), (76, 0.09), (79, 0.09), (84, 0.09)] * 4
    jump = [(72, 0.045), (79, 0.055), (84, 0.08)]
    collect_gem = [(84, 0.05), (91, 0.05), (96, 0.12)]
    collect_double_jump = [(72, 0.06), (79, 0.06), (88, 0.14)]
    collect_shield = [(55, 0.08), (62, 0.08), (67, 0.18)]
    collect_key = [(67, 0.08), (74, 0.08), (79, 0.08), (86, 0.18)]
    gate_open = [(48, 0.10), (55, 0.10), (60, 0.10), (67, 0.28)]
    # Śmierć: opadający, dysonansowy akord. Zamiana: szybki rezonans
    # stereo-symulowany zmianą wysokości, bez potrzeby korzystania z MIDI.
    death = [(67, 0.10), (63, 0.10), (58, 0.14), (None, 0.12), (46, 0.32)]
    swap = [(96, 0.045), (88, 0.045), (100, 0.045), (91, 0.045), (105, 0.16)]

    files = {
        "menu_theme.wav": _render(menu_melody, "sine", volume=0.12),
        "arcade_theme.wav": _render(arcade_melody, "square", volume=0.16),
        "jump.wav": _render(jump, "sine", volume=0.32),
        "collect_gem.wav": _render(collect_gem, "sine", volume=0.28),
        "collect_double_jump.wav": _render(collect_double_jump, "square", volume=0.24),
        "collect_shield.wav": _render(collect_shield, "sine", volume=0.24),
        "collect_key.wav": _render(collect_key, "square", volume=0.24),
        "gate_open.wav": _render(gate_open, "sine", volume=0.26),
        "death.wav": _render(death, "sine", volume=0.30),
        "swap.wav": _render(swap, "square", volume=0.24),
    }
    for name, frames in files.items():
        _write_wav(os.path.join(output_dir, name), frames)
    return tuple(os.path.join(output_dir, name) for name in files)


if __name__ == "__main__":
    for path in generate_audio():
        print(f"Wygenerowano: {path}")
