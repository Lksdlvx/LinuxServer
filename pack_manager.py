# pack_manager.py
import json
import os
import logging


class PackManager:
    """Gestionnaire des packs de plugins intégré au système existant"""

    def __init__(self, config_dir, plugins_dir):
        self.config_dir = config_dir
        self.plugins_dir = plugins_dir
        self.packs_config_path = os.path.join(config_dir, 'plugin_packs.json')
        self.packs_data = self.load_packs_config()

    def load_packs_config(self):
        """Charge la configuration des packs"""
        try:
            if os.path.exists(self.packs_config_path):
                with open(self.packs_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Configuration par défaut si le fichier n'existe pas
                default_config = self._create_default_config()
                self.save_packs_config(default_config)
                return default_config

        except json.JSONDecodeError as e:
            logging.error("Erreur JSON dans packs config: {}".format(str(e)))
            return {"packs": {}, "individual_plugins": {}}
        except Exception as e:
            logging.error("Erreur chargement packs config: {}".format(str(e)))
            return {"packs": {}, "individual_plugins": {}}

    def _create_default_config(self):
        """Crée une configuration par défaut"""
        return {
            "packs": {
                "basic": {
                    "name": "Pack Basique",
                    "description": "Outils essentiels pour débuter avec Revit",
                    "plugins": ["hello_world"],
                    "price": 29.99,
                    "category": "starter"
                },
                "premium": {
                    "name": "Pack Premium",
                    "description": "Accès à tous les plugins disponibles",
                    "plugins": ["*"],
                    "price": 199.99,
                    "category": "professional"
                }
            },
            "individual_plugins": {
                "hello_world": {
                    "name": "Hello World",
                    "description": "Plugin de démonstration et test",
                    "price": 0.00,
                    "category": "demo"
                }
            }
        }

    def save_packs_config(self, config_data):
        """Sauvegarde la configuration des packs"""
        try:
            with open(self.packs_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error("Erreur sauvegarde packs config: {}".format(str(e)))
            return False

    def get_plugins_from_pack(self, pack_name):
        """Récupère la liste des plugins d'un pack"""
        packs = self.packs_data.get("packs", {})

        if pack_name not in packs:
            return []

        pack = packs[pack_name]
        plugins = pack.get("plugins", [])

        # Si le pack contient "*", retourner tous les plugins disponibles
        if "*" in plugins:
            return self.get_all_available_plugins()

        return plugins

    def get_all_available_plugins(self):
        """Récupère tous les plugins disponibles sur le disque"""
        if not os.path.exists(self.plugins_dir):
            return []

        available_plugins = []
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith('.py'):
                plugin_name = filename[:-3]  # Enlève .py
                available_plugins.append(plugin_name)

        return available_plugins

    def get_pack_info(self, pack_name):
        """Récupère les informations détaillées d'un pack - NOUVELLE MÉTHODE"""
        packs = self.packs_data.get("packs", {})

        if pack_name not in packs:
            return {}

        pack = dict(packs[pack_name])  # Copie pour éviter les modifications
        plugins = list(pack.get("plugins", []))

        # Résoudre includes_packs si présent
        for included_pack in pack.get("includes_packs", []):
            if included_pack in packs:
                included_plugins = packs[included_pack].get("plugins", [])
                plugins.extend(included_plugins)

        # Si le pack contient "*", retourner tous les plugins disponibles
        if "*" in plugins:
            plugins = self.get_all_available_plugins()
        else:
            # Dédoublonner et trier
            plugins = sorted(set(plugins))

        return {
            "name": pack.get("name", pack_name),
            "description": pack.get("description", ""),
            "plugins": plugins,
            "plugin_count": len(plugins),
            "price": pack.get("price", 0.0),
            "category": pack.get("category", "general")
        }

    def resolve_user_permissions(self, user_data):
        """Résout toutes les permissions d'un utilisateur (plugins + packs)"""
        allowed_plugins = set()

        # 1. Plugins individuels
        individual_plugins = user_data.get("allowed_plugins", [])
        if "*" in individual_plugins:
            return self.get_all_available_plugins()

        allowed_plugins.update(individual_plugins)

        # 2. Plugins depuis les packs
        allowed_packs = user_data.get("allowed_packs", [])
        if "*" in allowed_packs:
            return self.get_all_available_plugins()

        for pack_name in allowed_packs:
            pack_plugins = self.get_plugins_from_pack(pack_name)
            allowed_plugins.update(pack_plugins)

        return list(allowed_plugins)

    def is_plugin_allowed(self, user_data, plugin_name):
        """Vérifie si un plugin est autorisé pour un utilisateur"""
        allowed_plugins = self.resolve_user_permissions(user_data)
        return plugin_name in allowed_plugins

    def get_user_detailed_permissions(self, user_data):
        """Récupère les permissions détaillées d'un utilisateur"""
        individual_plugins = user_data.get("allowed_plugins", [])
        allowed_packs = user_data.get("allowed_packs", [])

        # Résolution des plugins depuis les packs
        pack_plugins = {}
        for pack_name in allowed_packs:
            if pack_name == "*":
                pack_plugins = {"*": self.get_all_available_plugins()}
                break
            pack_plugins[pack_name] = self.get_plugins_from_pack(pack_name)

        return {
            "individual_plugins": individual_plugins,
            "pack_plugins": pack_plugins,
            "all_allowed_plugins": self.resolve_user_permissions(user_data)
        }

    def list_all_packs(self):
        """Liste tous les packs disponibles avec leurs informations - VERSION CORRIGÉE"""
        packs = self.packs_data.get("packs", {})
        result = {}

        for pack_name in packs.keys():
            result[pack_name] = self.get_pack_info(pack_name)

        return result