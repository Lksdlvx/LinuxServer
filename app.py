# app.py - Serveur Flask avec gestion des entreprises
from flask import Flask, request, jsonify, send_file, abort
import os
import json
import logging
from datetime import datetime

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(BASE_DIR, 'plugins')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
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


class PluginServer:
    def __init__(self):
        self.users_file = os.path.join(CONFIG_DIR, 'users.json')
        self._load_config()

    def _load_config(self):
        """Charge la configuration des entreprises et utilisateurs"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                self.companies = self.config.get('companies', {})
                logger.info(f"Configuration chargée: {len(self.companies)} entreprises")
        except FileNotFoundError:
            logger.error(f"Fichier users.json non trouvé: {self.users_file}")
            self.companies = {}
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans users.json: {e}")
            self.companies = {}

    def authenticate_user(self, autodesk_user, computer_name, api_key):
        """Authentifie un utilisateur par autodesk_user + computer_name + api_key"""
        user_key = f"{autodesk_user}_{computer_name}"

        # Chercher dans toutes les entreprises
        for company_id, company_data in self.companies.items():
            if not company_data.get('active', False):
                continue

            users = company_data.get('users', {})
            if user_key in users:
                user = users[user_key]

                # Vérifier l'API key
                if user.get('api_key') != api_key:
                    raise Exception('API key invalide')

                if not user.get('active', False):
                    raise Exception('Compte utilisateur désactivé')

                # Vérifier l'expiration de l'utilisateur
                expires = user.get('expires')
                if expires:
                    try:
                        expire_date = datetime.strptime(expires, "%Y-%m-%d")
                        if datetime.now() > expire_date:
                            raise Exception('Compte utilisateur expiré')
                    except ValueError:
                        logger.warning(f"Format de date expires invalide pour {user_key}: {expires}")

                # Retourner l'utilisateur avec les infos de l'entreprise
                return {
                    'user': user,
                    'company': company_data,
                    'company_id': company_id,
                    'user_key': user_key
                }

        raise Exception('Utilisateur non trouvé ou non autorisé')

    def check_plugin_access(self, auth_data, plugin_name):
        """Vérifie l'accès au plugin basé sur les permissions utilisateur"""
        user = auth_data['user']
        allowed = user.get('allowed_plugins', [])

        if '*' in allowed or plugin_name in allowed:
            return True
        raise Exception(f'Accès refusé au plugin: {plugin_name}')

    def get_user_allowed_plugins(self, auth_data):
        """Récupère les plugins autorisés pour l'utilisateur"""
        user = auth_data['user']
        allowed = user.get('allowed_plugins', [])

        if '*' in allowed:
            return [p['name'] for p in self.list_disk_plugins()]
        return sorted(allowed)

    def list_disk_plugins(self):
        """Liste tous les plugins disponibles sur le disque"""
        plugins = []
        if os.path.exists(PLUGINS_DIR):
            for file in os.listdir(PLUGINS_DIR):
                if file.endswith('.py'):
                    stat = os.stat(os.path.join(PLUGINS_DIR, file))
                    plugins.append({
                        'name': file[:-3],  # Enlever .py
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        return plugins

    def get_company_stats(self, company_id):
        """Statistiques d'une entreprise"""
        if company_id not in self.companies:
            return None

        company = self.companies[company_id]
        users = company.get('users', {})

        # Compter les utilisateurs actifs et non expirés
        active_users = 0
        expired_users = 0

        for user in users.values():
            if not user.get('active', False):
                continue

            expires = user.get('expires')
            if expires:
                try:
                    expire_date = datetime.strptime(expires, "%Y-%m-%d")
                    if datetime.now() > expire_date:
                        expired_users += 1
                    else:
                        active_users += 1
                except ValueError:
                    active_users += 1  # Si format invalide, considérer comme actif
            else:
                active_users += 1  # Pas d'expiration = actif

        return {
            'company_name': company['name'],
            'total_users': len(users),
            'active_users': active_users,
            'expired_users': expired_users,
            'created_at': company.get('created_at')
        }

    def get_global_stats(self):
        """Statistiques globales du système"""
        total_companies = len(self.companies)
        active_companies = len([c for c in self.companies.values() if c.get('active', False)])

        total_users = 0
        active_users = 0

        for company in self.companies.values():
            if not company.get('active', False):
                continue
            users = company.get('users', {})
            total_users += len(users)
            active_users += len([u for u in users.values() if u.get('active', False)])

        return {
            'total_companies': total_companies,
            'active_companies': active_companies,
            'total_users': total_users,
            'active_users': active_users,
            'total_plugins': len(self.list_disk_plugins())
        }


# IMPORTANT: Instance du serveur AVANT les routes
plugin_server = PluginServer()


def authenticate_request():
    """Authentification par autodesk_user + computer_name + api_key"""
    autodesk_user = request.headers.get('X-Autodesk-User')
    computer_name = request.headers.get('X-Computer-Name')
    api_key = request.headers.get('X-API-Key')

    if not autodesk_user or not computer_name or not api_key:
        return None, jsonify({
            'error': 'Headers X-Autodesk-User, X-Computer-Name et X-API-Key requis'
        }), 401

    try:
        auth_data = plugin_server.authenticate_user(autodesk_user, computer_name, api_key)
        return auth_data, None, None
    except Exception as e:
        return None, jsonify({'error': str(e)}), 403


@app.route('/')
def home():
    """Page d'accueil"""
    try:
        stats = plugin_server.get_global_stats()
        return {
            'service': 'Revit Plugins Server',
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'version': '4.0.0-companies',
            'features': ['company_management', 'individual_plugins', 'user_expiration'],
            'statistics': stats,
            'endpoints': {
                'get_plugin': '/api/get_plugin',
                'user_info': '/api/user_info',
                'company_stats': '/api/company_stats',
                'status': '/api/status'
            }
        }
    except Exception as e:
        logger.error(f"Erreur dans home(): {e}")
        return jsonify({
            'service': 'Revit Plugins Server',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/get_plugin', methods=['GET'])
def get_plugin():
    """API pour récupérer un plugin"""
    # Authentification
    auth_data, error_response, status_code = authenticate_request()
    if not auth_data:
        return error_response, status_code

    try:
        plugin_name = request.headers.get('X-Plugin-Name')
        if not plugin_name:
            return jsonify({'error': 'X-Plugin-Name requis'}), 400

        # Vérification des droits
        plugin_server.check_plugin_access(auth_data, plugin_name)

        # Lecture et envoi du fichier
        file_path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")
        if not os.path.exists(file_path):
            return jsonify({'error': f'Plugin {plugin_name} introuvable'}), 404

        user_info = auth_data['user']
        company_info = auth_data['company']

        logger.info(f"Plugin {plugin_name} téléchargé par {user_info['name']} "
                    f"({company_info['name']})")

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Erreur get_plugin: {e}")
        return jsonify({'error': str(e)}), 403


@app.route('/api/user_info', methods=['GET'])
def get_user_info():
    """Informations complètes de l'utilisateur"""
    auth_data, error_response, status_code = authenticate_request()
    if not auth_data:
        return error_response, status_code

    try:
        user = auth_data['user']
        company = auth_data['company']

        # Plugins autorisés
        allowed_plugin_names = plugin_server.get_user_allowed_plugins(auth_data)

        # Détails des plugins
        all_disk_plugins = plugin_server.list_disk_plugins()
        user_plugins = [p for p in all_disk_plugins if p['name'] in allowed_plugin_names]

        return jsonify({
            'success': True,
            'user': {
                'name': user['name'],
                'email': user['email'],
                'autodesk_user': user['autodesk_user'],
                'computer_name': user['computer_name'],
                'allowed_plugins': user.get('allowed_plugins', []),
                'expires': user.get('expires')
            },
            'company': {
                'name': company['name'],
                'created_at': company.get('created_at')
            },
            'plugins_details': user_plugins,
            'total_plugins': len(user_plugins),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erreur user_info: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@app.route('/api/company_stats', methods=['GET'])
def get_company_stats():
    """Statistiques de l'entreprise de l'utilisateur connecté"""
    auth_data, error_response, status_code = authenticate_request()
    if not auth_data:
        return error_response, status_code

    try:
        company_id = auth_data['company_id']
        stats = plugin_server.get_company_stats(company_id)

        return jsonify({
            'success': True,
            'company_id': company_id,
            'company_stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erreur company_stats: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@app.route('/api/plugins', methods=['GET'])
def list_plugins():
    """Liste tous les plugins disponibles sur le serveur"""
    try:
        plugins = plugin_server.list_disk_plugins()
        return jsonify({
            'success': True,
            'plugins': plugins,
            'plugin_count': len(plugins),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erreur list_plugins: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@app.route('/api/status', methods=['GET'])
def status():
    """Health check avec statistiques"""
    try:
        stats = plugin_server.get_global_stats()
        return jsonify({
            'status': 'OK',
            'version': '4.0.0-companies',
            'statistics': stats,
            'config_files': {
                'users_json': os.path.exists(plugin_server.users_file)
            },
            'timestamp': datetime.now().isoformat()
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
    print("🚀 Serveur Flask démarré (Version Entreprises)")
    print(f"📁 Dossiers: {BASE_DIR}")
    print(f"🔌 Plugins: {PLUGINS_DIR}")
    print(f"⚙️ Config: {CONFIG_DIR}")
    print(f"📝 Logs: {LOGS_DIR}")
    print("🏢 Gestion des entreprises activée")
    print("🔐 Authentification: autodesk_user + computer_name + api_key")
    print("👥 Permissions individuelles par utilisateur")

    # Développement seulement
    app.run(debug=True, host='0.0.0.0', port=5000)