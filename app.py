# app.py - Serveur Flask principal avec support des packs -
from flask import Flask, request, jsonify, send_file
import os
import json
import logging
from datetime import datetime
from functools import wraps
from pack_manager import PackManager

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(BASE_DIR, 'plugins')  # RESTAURÉ
CONFIG_DIR = os.path.join(BASE_DIR, 'config')    # RESTAURÉ
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# S'assurer que le dossier de logs existe
os.makedirs(LOGS_DIR, exist_ok=True)

# Configuration du logger
logger = logging.getLogger('plugin_server')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(os.path.join(LOGS_DIR, 'access.log'))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(logging.StreamHandler())


# Classe principale du serveur
class PluginServer:
    def __init__(self):
        self.config_file = os.path.join(CONFIG_DIR, 'plugin_packs.json')
        self.users_file = os.path.join(CONFIG_DIR, 'users.json')
        self.pack_manager = PackManager(CONFIG_DIR, PLUGINS_DIR)
        # Charger la config au démarrage
        self._load_configs()

    def _load_configs(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.packs = json.load(f)
        with open(self.users_file, 'r', encoding='utf-8') as f:
            self.users = json.load(f)

    def authenticate_user(self, email, api_key):
        """Vérifie la validité de l'utilisateur et de sa clé API."""
        user = self.users.get(email)
        if not user or user.get('api_key') != api_key:
            raise Exception('Authentification échouée')
        return user

    def check_plugin_access(self, user, plugin_name):
        """Vérifie si l'utilisateur a bien le droit d'accéder au plugin."""
        allowed = user.get('allowed_plugins', [])
        if '*' not in allowed and plugin_name not in allowed:
            raise Exception('Accès refusé au plugin')
        return True

    def check_pack_access(self, user, pack_name):
        """Vérifie si l'utilisateur peut accéder au pack."""
        allowed = user.get('allowed_packs', [])
        if '*' not in allowed and pack_name not in allowed:
            raise Exception('Accès refusé au pack')
        return True

    def update_machine_info(self, email, machine_data):
        """Ajoute ou met à jour une machine pour l'utilisateur - VERSION CORRIGÉE."""
        try:
            u = self.users[email]
            machines = u.setdefault('machines', {})
            # Utiliser machine_id comme clé pour cohérence
            machine_id = machine_data.get('machine_id', machine_data.get('computer_name', 'unknown'))
            machines[machine_id] = machine_data
            u['machines'] = machines

            # Sauvegarder
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour machine: {e}")
            return False

    def list_disk_plugins(self):
        plugins = []
        if os.path.exists(PLUGINS_DIR):
            for file in os.listdir(PLUGINS_DIR):
                if file.endswith('.py'):
                    stat = os.stat(os.path.join(PLUGINS_DIR, file))
                    plugins.append({
                        'name': file[:-3],
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        return plugins

    def list_all_packs(self):
        """Retourne les packs détaillés via PackManager."""
        return self.pack_manager.list_all_packs()


def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500


# Instance du serveur
plugin_server = PluginServer()


# Décorateur pour authentifier l'utilisateur - VERSION CORRIGÉE
def authenticate_user(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        user_email = request.headers.get('X-User-Email')
        if not api_key or not user_email:
            return jsonify({'error': 'Headers X-API-Key et X-User-Email requis'}), 401
        try:
            user = plugin_server.authenticate_user(user_email, api_key)
            # CORRECTION : Ajouter l'email dans l'objet user
            user = dict(user)
            user['email'] = user_email
            request.user = user
        except Exception as e:
            return jsonify({'error': str(e)}), 403
        return func(*args, **kwargs)

    return wrapper


@app.route('/')
def home():
    """Page d'accueil"""
    return {
        'service': 'Revit Plugins Server',
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'features': ['individual_plugins', 'plugin_packs', 'machine_tracking'],
        'endpoints': {
            'get_plugin': '/api/get_plugin',
            'list_plugins': '/api/plugins',
            'user_plugins': '/api/user_plugins',
            'pack_info': '/api/pack/<pack_name>',
            'user_machines': '/api/machines/<user_email>',
            'status': '/api/status'
        }
    }


# CORRECTION : Ordre des décorateurs inversé
@app.route('/api/get_plugin', methods=['GET'])
@authenticate_user
def get_plugin():
    """API pour récupérer un plugin (avec support des packs et machines)"""
    try:
        plugin_name = request.headers.get('X-Plugin-Name')
        if not plugin_name:
            return jsonify({'error': 'X-Plugin-Name requis'}), 400

        # Vérification des droits
        plugin_server.check_plugin_access(request.user, plugin_name)

        # Mise à jour des informations machine si fournies
        machine_id = request.headers.get('X-Machine-ID')
        if machine_id:
            # CORRECTION : Utiliser l'email depuis request.user maintenant disponible
            machine_data = {
                'machine_id': machine_id,
                'computer_name': request.headers.get('X-Computer-Name', 'Unknown'),
                'autodesk_user': request.headers.get('X-Autodesk-User', 'Unknown'),
                'os_version': request.headers.get('X-OS-Version', 'Unknown'),
                'revit_version': request.headers.get('X-Revit-Version', 'Unknown'),
                'last_seen': datetime.utcnow().isoformat() + 'Z'
            }
            plugin_server.update_machine_info(request.user['email'], machine_data)

        # Lecture et envoi du fichier
        file_path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")
        if not os.path.exists(file_path):
            return jsonify({'error': 'Plugin introuvable'}), 404
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 403


# CORRECTION : Ordre des décorateurs + structure de réponse alignée
@app.route('/api/plugins', methods=['GET'])
@authenticate_user
def list_plugins():
    """Lister les plugins et packs disponibles - VERSION CORRIGÉE"""
    try:
        plugins = plugin_server.list_disk_plugins()
        packs = plugin_server.list_all_packs()
        return jsonify({
            'plugins': plugins,
            'plugin_count': len(plugins),
            'packs': packs,
            'pack_count': len(packs)
        })
    except Exception as e:
        return internal_error(e)


# CORRECTION : Ordre des décorateurs
@app.route('/api/user_plugins', methods=['GET'])
@authenticate_user
def get_user_plugins():
    """Récupère les plugins autorisés pour un utilisateur spécifique"""
    try:
        # L'authentification est déjà faite par le décorateur
        user_email = request.user['email']
        user = request.user

        # Résolution des permissions détaillées
        permissions = plugin_server.pack_manager.get_user_detailed_permissions(user)

        return jsonify({
            'success': True,
            'user_email': user_email,
            'user_name': user.get('name', 'Inconnu'),
            'individual_plugins': permissions['individual_plugins'],
            'allowed_packs': user.get('allowed_packs', []),
            'pack_plugins': permissions['pack_plugins'],
            'all_allowed_plugins': permissions['all_allowed_plugins'],
            'total_plugins': len(permissions['all_allowed_plugins']),
            'expires': user.get('expires'),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        app.logger.error("Erreur user_plugins pour {}: {}".format(
            request.user.get('email', 'unknown'), str(e)
        ))
        return jsonify({'error': 'Erreur interne du serveur'}), 500


# CORRECTION : Ordre des décorateurs + wrapper pack_info
@app.route('/api/pack/<pack_name>', methods=['GET'])
@authenticate_user
def get_pack_info(pack_name):
    """Récupère les informations détaillées d'un pack - VERSION CORRIGÉE"""
    try:
        plugin_server.check_pack_access(request.user, pack_name)
        info = plugin_server.pack_manager.get_pack_info(pack_name)
        if not info:
            return jsonify({'error': 'Pack introuvable'}), 404
        return jsonify({'pack_info': info})
    except Exception as e:
        return jsonify({'error': str(e)}), 403


# CORRECTION : Ordre des décorateurs + structure machines cohérente
@app.route('/api/machines/<user_email>', methods=['GET'])
@authenticate_user
def get_user_machines(user_email):
    """Endpoint pour consulter les machines d'un utilisateur - VERSION CORRIGÉE"""
    # On autorise seulement l'utilisateur concerné ou un admin
    if request.user['email'] != user_email and not request.user.get('is_admin'):
        return jsonify({'error': 'Accès non autorisé'}), 403
    try:
        with open(plugin_server.users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        machines = users.get(user_email, {}).get('machines', {})
        return jsonify({
            'email': user_email,
            'total_machines': len(machines) if isinstance(machines, dict) else len(machines or []),
            'machines': machines
        })
    except Exception as e:
        return internal_error(e)


# CORRECTION : Structure de réponse alignée avec le test
@app.route('/api/status', methods=['GET'])
def status():
    """Statut de santé du service - VERSION CORRIGÉE"""
    try:
        # Vérification des fichiers de config
        cfg_users = os.path.exists(plugin_server.users_file)
        cfg_packs = os.path.exists(plugin_server.config_file)

        # Statistiques
        plugins = plugin_server.list_disk_plugins()
        packs = plugin_server.pack_manager.list_all_packs()

        # Comptage des utilisateurs
        try:
            with open(plugin_server.users_file, 'r', encoding='utf-8') as f:
                all_users = json.load(f)
        except Exception:
            all_users = {}

        active_users = sum(1 for u in all_users.values()
                           if isinstance(u, dict) and u.get('active', False))

        return jsonify({
            'status': 'OK',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'statistics': {
                'plugins_count': len(plugins),
                'packs_count': len(packs),
                'users_count': len(all_users),
                'active_users': active_users
            },
            'config_files': {
                'users_json': cfg_users,
                'packs_json': cfg_packs
            }
        })
    except Exception as e:
        logger.error(f"Erreur status: {e}")
        return jsonify({'status': 'ERROR', 'error': str(e)}), 500


# Gestion des erreurs globales
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Route introuvable'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Erreur interne'}), 500


if __name__ == '__main__':
    print("🚀 Serveur Flask démarré")
    print("📁 Dossiers: {}".format(BASE_DIR))
    print("🔌 Plugins: {}".format(PLUGINS_DIR))
    print("⚙️ Config: {}".format(CONFIG_DIR))
    print("📝 Logs: {}".format(LOGS_DIR))
    print("📦 Support des packs: ✅")
    print("💻 Tracking machines: ✅")

    # Développement seulement
    app.run(debug=True, host='0.0.0.0', port=5000)