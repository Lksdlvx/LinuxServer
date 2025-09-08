#!/bin/bash
# start_dev.sh - Script de démarrage développement

echo "🚀 Démarrage du serveur Flask Revit Plugins"
echo "=========================================="

# Vérification de l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel non trouvé"
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activation
source venv/bin/activate

# Vérification des dépendances
if ! pip show flask > /dev/null 2>&1; then
    echo "📦 Installation des dépendances..."
    pip install flask python-dotenv gunicorn
fi

echo "✅ Environnement prêt"
echo "🌐 Démarrage sur http://localhost:5000"
echo "Press Ctrl+C to stop"

# Démarrage
python app.py
