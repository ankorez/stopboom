#!/usr/bin/env python3
"""Génère les sons prédéfinis pour StopBoom."""

import os
import wave
import numpy as np

SR = 48000
DURATION = 3.0
SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "sounds")


def save_wav(name, audio):
    """Sauvegarde un array float32 en wav stéréo 48kHz."""
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)
    stereo = np.column_stack([audio_int16, audio_int16])
    path = os.path.join(SOUNDS_DIR, f"{name}.wav")
    with wave.open(path, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    print(f"  {path} ({len(audio) / SR:.1f}s)")


def gen_alarm():
    """Alarme : deux fréquences qui alternent rapidement."""
    t = np.linspace(0, DURATION, int(SR * DURATION), dtype=np.float32)
    switch = (np.floor(t * 8) % 2).astype(np.float32)
    f1, f2 = 800, 1200
    audio = switch * np.sin(2 * np.pi * f1 * t) + (1 - switch) * np.sin(2 * np.pi * f2 * t)
    return audio.astype(np.float32) * 0.9


def gen_doorbell():
    """Sonnette : ding-dong répété."""
    t = np.linspace(0, DURATION, int(SR * DURATION), dtype=np.float32)
    audio = np.zeros_like(t)
    ding_f, dong_f = 1047, 784  # C6, G5
    cycle = 0.5  # ding-dong every 0.5s
    for start in np.arange(0, DURATION, cycle):
        mid = start + cycle * 0.4
        mask_ding = (t >= start) & (t < mid)
        mask_dong = (t >= mid) & (t < start + cycle)
        env_ding = np.exp(-8 * (t[mask_ding] - start))
        env_dong = np.exp(-8 * (t[mask_dong] - mid))
        audio[mask_ding] += np.sin(2 * np.pi * ding_f * t[mask_ding]) * env_ding
        audio[mask_dong] += np.sin(2 * np.pi * dong_f * t[mask_dong]) * env_dong
    return audio.astype(np.float32) * 0.9


def gen_hammer():
    """Marteau : impacts courts de bruit blanc."""
    t = np.linspace(0, DURATION, int(SR * DURATION), dtype=np.float32)
    audio = np.zeros_like(t)
    for start in np.arange(0, DURATION, 0.3):
        mask = (t >= start) & (t < start + 0.08)
        env = np.exp(-30 * (t[mask] - start))
        audio[mask] += np.random.randn(np.sum(mask)).astype(np.float32) * env
    return audio.astype(np.float32) * 0.9


def gen_honk():
    """Klaxon : fréquence basse pulsée."""
    t = np.linspace(0, DURATION, int(SR * DURATION), dtype=np.float32)
    pulse = ((np.sin(2 * np.pi * 4 * t) > 0).astype(np.float32) * 0.5 + 0.5)
    audio = np.sin(2 * np.pi * 350 * t) * pulse
    audio += np.sin(2 * np.pi * 440 * t) * pulse * 0.5
    return audio.astype(np.float32) * 0.9


def gen_siren():
    """Sirène : fréquence qui monte et descend."""
    t = np.linspace(0, DURATION, int(SR * DURATION), dtype=np.float32)
    freq = 600 + 400 * np.sin(2 * np.pi * 2 * t)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    audio = np.sin(phase)
    return audio.astype(np.float32) * 0.9


if __name__ == "__main__":
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    print("Génération des sons...")
    save_wav("alarm", gen_alarm())
    save_wav("doorbell", gen_doorbell())
    save_wav("hammer", gen_hammer())
    save_wav("honk", gen_honk())
    save_wav("siren", gen_siren())
    print("Terminé!")
