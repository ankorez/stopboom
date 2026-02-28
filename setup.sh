#!/bin/bash
# Setup StopBoom sur Raspberry Pi

set -e

echo "=== Installation des dépendances système ==="
sudo apt update
sudo apt install -y python3-pip python3-venv portaudio19-dev

echo "=== Création de l'environnement virtuel ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Installation des dépendances Python ==="
pip install -r requirements.txt

echo "=== Installation du service systemd ==="
sudo cp stopboom.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stopboom

echo ""
echo "=== Installation terminée ==="
echo "Commandes utiles :"
echo "  sudo systemctl start stopboom    # Démarrer"
echo "  sudo systemctl stop stopboom     # Arrêter"
echo "  sudo systemctl status stopboom   # Statut"
echo "  journalctl -u stopboom -f        # Voir les logs"
echo ""
echo "Pour tester manuellement :"
echo "  source venv/bin/activate"
echo "  python3 stopboom.py"
