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

Le dashboard web est accessible sur `http://<hostname>.local:5000`.

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

Editer `config.json` via le dashboard web ou manuellement, puis redemarrer le service :

```json
{
  "threshold": 0.15,
  "pre_boom_seconds": 1.0,
  "post_boom_seconds": 1.5,
  "cooldown_seconds": 5,
  "sample_rate": null,
  "channels": 1,
  "device": null,
  "alsa_device": "plughw:1,0",
  "output_sample_rate": 48000
}
```

| Parametre | Description |
|---|---|
| `threshold` | Seuil de detection RMS (0.0-1.0). Baisser = plus sensible. |
| `pre_boom_seconds` | Secondes d'audio conservees avant le boom. |
| `post_boom_seconds` | Secondes d'audio enregistrees apres la detection. |
| `cooldown_seconds` | Pause apres chaque replay pour eviter les boucles. |
| `sample_rate` | Frequence d'echantillonnage. `null` = auto-detection depuis le device. |
| `channels` | Canaux d'entree (1 = mono). |
| `device` | Index du device sounddevice pour la capture. `null` = auto-detection du premier device USB. |
| `alsa_device` | Device ALSA pour la lecture (ex: `plughw:1,0`). |
| `output_sample_rate` | Frequence de sortie pour la lecture (48000 recommande). |
| `web_port` | Port du dashboard web (5000 par defaut). |

### Trouver les devices audio

```bash
python3 stopboom.py --list-devices
```

Cela affiche tous les peripheriques disponibles avec leur index, nombre de canaux et sample rate.

### Calibrer le seuil

Lancer StopBoom et faire du bruit. Les logs affichent la valeur RMS a chaque detection.
Ajuster `threshold` dans `config.json` selon les valeurs observees.

## Depannage

### Pas de son en sortie

1. Verifier que le peripherique n'est pas en mute
2. Monter le volume ALSA : `amixer -c <card> contents` pour voir les controles, puis `amixer -c <card> cset numid=<id> <max>`
3. Tester avec : `speaker-test -D plughw:<card>,0 -c 2 -t sine -f 440`

### Trouver le bon device ALSA

```bash
arecord -l   # Peripheriques de capture
aplay -l     # Peripheriques de lecture
```

Le numero de carte correspond au `<card>` dans `plughw:<card>,0`.
