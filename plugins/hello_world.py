# -*- coding: utf-8 -*-
"""
Plugin Hello World - Version Flask
Téléchargé et exécuté dynamiquement depuis le serveur Flask
"""

import sys
from datetime import datetime


def test_revit_context():
    """Test si on est dans un contexte Revit"""
    try:
        # Test de présence de l'API Revit
        import clr
        clr.AddReference('RevitAPI')
        from Autodesk.Revit.DB import Transaction

        print("🏗️  Contexte Revit détecté")
        return True
    except (ImportError, FileNotFoundError, Exception) as e:
        print("💻 Contexte Python standard")
        print(f"   Détail: {type(e).__name__}")
        return False


def get_system_info():
    """Récupère les informations système"""
    return {
        'message': 'Hello World depuis Flask !',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'python_version': sys.version.split()[0],
        'platform': sys.platform,
        'encoding': sys.getdefaultencoding()
    }


def display_info(info_dict):
    """Affiche les informations de manière formatée"""
    print("=" * 60)
    print("PLUGIN HELLO WORLD - SERVEUR FLASK")
    print("=" * 60)

    for key, value in info_dict.items():
        formatted_key = key.replace('_', ' ').title()
        print("{}: {}".format(formatted_key, value))

    print("=" * 60)
    print("✅ Plugin exécuté avec succès depuis Flask !")
    print("=" * 60)


def main():
    """Fonction principale du plugin"""
    try:
        # Test du contexte
        is_revit = test_revit_context()

        # Récupération des informations système
        info = get_system_info()

        # Affichage
        display_info(info)

        # Préparation du résultat
        result = info.copy()
        result['revit_context'] = is_revit
        result['status'] = 'success'

        print("[PLUGIN] Résultat: {}".format(result))
        return result

    except Exception as e:
        error_message = str(e)
        print("[PLUGIN] Erreur: {}".format(error_message))

        result = {
            'status': 'error',
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        return result


# Point d'entrée
if __name__ == "__main__":
    main()