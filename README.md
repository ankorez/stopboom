# StopBoom

Detecte les booms des voisins via un speakerphone Jabra USB et les rejoue automatiquement.

## Materiel requis

- Raspberry Pi (Zero W/2W, 3, 4, 5) ou tout autre appareil Linux
- Speakerphone USB ou micro + enceinte (teste avec Jabra SPEAK 410)

## Installation

### 1. Preparer l'appareil

Installer un OS Linux (ex: Raspberry Pi OS Lite avec [Raspberry Pi Imager](https://www.raspberrypi.com/software/)).

Pour un Raspberry Pi, activer SSH et configurer le Wi-Fi dans les reglages avances de l'Imager.

### 2. Copier les fichiers

Depuis la machine de developpement :

```bash
ssh <user>@<hostname> "mkdir -p ~/stopboom"
scp stopboom.py config.json requirements.txt setup.sh stopboom.service <user>@<hostname>:~/stopboom/
```

### 3. Lancer l'installation

```bash
ssh <user>@<hostname>
cd ~/stopboom
chmod +x setup.sh
./setup.sh
```

Cela installe les dependances systeme, cree un environnement virtuel Python, et configure le service systemd.

### 4. Monter le volume du Jabra

```bash
# Mettre le volume ALSA au max
amixer -c 1 cset numid=3 11

# Utiliser aussi les boutons physiques + sur le Jabra
```

## Utilisation

### Test manuel

```bash
cd ~/stopboom
source venv/bin/activate
python3 stopboom.py
```

### Service systemd (demarrage automatique)

```bash
sudo systemctl start stopboom      # Demarrer
sudo systemctl stop stopboom       # Arreter
sudo systemctl status stopboom     # Statut
sudo systemctl restart stopboom    # Redemarrer (apres modif config)
journalctl -u stopboom -f          # Voir les logs en direct
```

Le service demarre automatiquement au boot du Pi.

## Configuration

Editer `config.json` puis redemarrer le service :

```json
{
  "threshold": 0.15,
  "pre_boom_seconds": 1.0,
  "post_boom_seconds": 1.5,
  "cooldown_seconds": 5,
  "sample_rate": 16000,
  "channels": 1,
  "device": 1,
  "alsa_device": "plughw:1,0"
}
```

| Parametre | Description |
|---|---|
| `threshold` | Seuil de detection RMS (0.0-1.0). Baisser = plus sensible. |
| `pre_boom_seconds` | Secondes d'audio conservees avant le boom. |
| `post_boom_seconds` | Secondes d'audio enregistrees apres la detection. |
| `cooldown_seconds` | Pause apres chaque replay pour eviter les boucles. |
| `sample_rate` | Frequence d'echantillonnage (16000 pour le Jabra). |
| `channels` | Canaux d'entree (1 = mono). |
| `device` | Index du device sounddevice pour la capture. |
| `alsa_device` | Device ALSA pour la lecture (`plughw:1,0` pour le Jabra). |

### Calibrer le seuil

```bash
cd ~/stopboom
source venv/bin/activate
python3 -c "
import sounddevice as sd
import numpy as np

def callback(indata, frames, time, status):
    level = np.sqrt(np.mean(indata**2))
    bars = int(level * 200)
    print(f'RMS: {level:.4f} |{\"#\" * bars}')

with sd.InputStream(samplerate=16000, channels=1, device=1, callback=callback, blocksize=1024):
    import time
    while True:
        time.sleep(0.1)
"
```

Faire du bruit et noter les valeurs RMS pour ajuster `threshold`.

## Depannage

### Trouver le bon device

```bash
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

Reperer l'index du Jabra et mettre a jour `device` dans `config.json`.

### Pas de son en sortie

1. Verifier que le Jabra n'est pas en mute (voyant rouge)
2. Monter le volume : `amixer -c 1 cset numid=3 11`
3. Appuyer sur le bouton volume + du Jabra
4. Tester avec : `speaker-test -D plughw:1,0 -c 2 -t sine -f 440`
