#!/usr/bin/env python3
"""StopBoom - Détecte les booms des voisins et les rejoue."""

import json
import os
import sys
import time
import wave
import queue
import logging
import tempfile
import subprocess
import numpy as np
import sounddevice as sd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("stopboom")


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def rms(block):
    """Calcule le volume RMS d'un bloc audio."""
    return np.sqrt(np.mean(block ** 2))


def list_devices():
    """Affiche les devices audio disponibles."""
    print("\n=== Devices audio disponibles ===\n")
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        inp = d["max_input_channels"]
        out = d["max_output_channels"]
        sr = int(d["default_samplerate"])
        flags = []
        if inp > 0:
            flags.append(f"{inp} in")
        if out > 0:
            flags.append(f"{out} out")
        print(f"  [{i}] {d['name']}  ({', '.join(flags)})  {sr} Hz")
    print()
    print("Pour config.json :")
    print('  "device" : index du device avec des canaux input (micro)')
    print('  "alsa_device" : "plughw:<card>,0" pour la sortie')
    print()
    print("Astuce : lancer 'arecord -l' et 'aplay -l' pour voir les cartes ALSA")
    print()


def detect_device():
    """Auto-détecte le premier device USB avec entrée et sortie."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        name = d["name"].lower()
        if "usb" in name and d["max_input_channels"] > 0:
            return i, d
    return None, None


def play_audio(audio, sr, alsa_device, out_sr):
    """Joue l'audio via aplay en stéréo."""
    # Resample si nécessaire
    if sr != out_sr:
        n_samples = int(len(audio) * out_sr / sr)
        indices = np.linspace(0, len(audio) - 1, n_samples)
        audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    # Convertir float32 -> int16
    audio_int16 = (audio * 32767).astype(np.int16)

    # Stéréo (dupliquer le canal mono)
    stereo = np.column_stack([audio_int16, audio_int16])

    # Écrire un fichier wav temporaire
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
        with wave.open(f, "w") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(out_sr)
            w.writeframes(stereo.tobytes())

    # Jouer via aplay
    subprocess.run(["aplay", "-D", alsa_device, tmp_path],
                   capture_output=True)

    os.unlink(tmp_path)


def main():
    if "--list-devices" in sys.argv:
        list_devices()
        return

    cfg = load_config()
    channels = cfg["channels"]
    threshold = cfg["threshold"]
    pre_seconds = cfg["pre_boom_seconds"]
    post_seconds = cfg["post_boom_seconds"]
    cooldown = cfg["cooldown_seconds"]
    device = cfg["device"]
    alsa_device = cfg.get("alsa_device", "plughw:1,0")
    out_sr = cfg.get("output_sample_rate", 48000)

    # Auto-détection du device si null
    if device is None:
        idx, dev_info = detect_device()
        if idx is not None:
            device = idx
            log.info("Device auto-détecté: [%d] %s", idx, dev_info["name"])
        else:
            log.error("Aucun device USB détecté. Lancer avec --list-devices pour voir les devices disponibles.")
            sys.exit(1)

    # Récupérer le sample rate du device
    dev_info = sd.query_devices(device)
    sr = cfg.get("sample_rate")
    if sr is None or sr == 0:
        sr = int(dev_info["default_samplerate"])
        log.info("Sample rate auto-détecté: %d Hz", sr)

    block_size = 1024
    pre_samples = int(sr * pre_seconds)
    post_samples = int(sr * post_seconds)

    # Buffer circulaire pour garder l'audio avant le boom
    buffer_len = int(sr * (pre_seconds + 1))
    ring = np.zeros((buffer_len, channels), dtype=np.float32)
    write_pos = 0

    log.info("StopBoom démarré")
    log.info("  threshold=%.2f  pre=%.1fs  post=%.1fs  cooldown=%ds",
             threshold, pre_seconds, post_seconds, cooldown)
    log.info("  device=[%s] %s", device, dev_info["name"])
    log.info("  alsa_device=%s  sr=%d  out_sr=%d  channels=%d",
             alsa_device, sr, out_sr, channels)

    boom_detected = False
    post_recording = None
    post_recorded = 0
    paused = False

    # Queue pour envoyer l'audio capturé au thread principal
    boom_queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        nonlocal write_pos, boom_detected, post_recording, post_recorded, paused

        if status:
            log.warning("Audio status: %s", status)

        if paused:
            return

        # Si on est en train d'enregistrer le post-boom
        if boom_detected:
            remaining = post_samples - post_recorded
            to_copy = min(frames, remaining)
            post_recording[post_recorded:post_recorded + to_copy] = indata[:to_copy]
            post_recorded += to_copy

            if post_recorded >= post_samples:
                boom_detected = False
                # Assembler pre-boom + post-boom
                pre_start = (write_pos - pre_samples) % buffer_len
                if pre_start < write_pos:
                    pre_audio = ring[pre_start:write_pos].copy()
                else:
                    pre_audio = np.concatenate([
                        ring[pre_start:],
                        ring[:write_pos]
                    ])
                boom_audio = np.concatenate([pre_audio, post_recording])
                # Envoyer au thread principal pour playback
                paused = True
                boom_queue.put(boom_audio)
            return

        # Écrire dans le buffer circulaire
        for i in range(frames):
            ring[write_pos] = indata[i]
            write_pos = (write_pos + 1) % buffer_len

        # Vérifier le volume
        level = rms(indata)
        if level > threshold:
            log.info("BOOM détecté! RMS=%.4f (seuil=%.4f)", level, threshold)
            boom_detected = True
            post_recording = np.zeros((post_samples, channels), dtype=np.float32)
            post_recorded = 0

    try:
        with sd.InputStream(
            samplerate=sr,
            channels=channels,
            dtype="float32",
            blocksize=block_size,
            device=device,
            callback=callback,
        ):
            log.info("En écoute... (Ctrl+C pour arrêter)")
            while True:
                try:
                    boom_audio = boom_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Flatten si mono
                if boom_audio.ndim == 2 and boom_audio.shape[1] == 1:
                    boom_audio = boom_audio.flatten()

                log.info("Lecture du boom (%.2fs)...", len(boom_audio) / sr)
                play_audio(boom_audio, sr, alsa_device, out_sr)
                log.info("Lecture terminée")

                if cooldown > 0:
                    log.info("Cooldown %ds...", cooldown)
                    time.sleep(cooldown)

                paused = False
                log.info("Écoute reprise")

    except KeyboardInterrupt:
        log.info("Arrêt demandé")
    except Exception as e:
        log.error("Erreur: %s", e)
        raise


if __name__ == "__main__":
    main()
