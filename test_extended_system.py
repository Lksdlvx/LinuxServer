# test_extended_system.py - Script de test complet
import requests
import json
import sys
import time


class ExtendedSystemTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []

    def test_server_availability(self):
        """Test si le serveur répond"""
        print("🔍 Test de disponibilité du serveur...")
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print("  ✅ Serveur disponible")
                print("  📊 Version: {}".format(data.get('version', 'Inconnue')))
                print("  🎯 Features: {}".format(data.get('features', [])))
                return True
            else:
                print("  ❌ Serveur répond mais erreur: {}".format(response.status_code))
                return False
        except requests.exceptions.ConnectionError:
            print("  ❌ Impossible de se connecter au serveur")
            print("  💡 Vérifiez que le serveur est démarré avec: ./start_dev.sh")
            return False
        except Exception as e:
            print("  ❌ Erreur: {}".format(str(e)))
            return False

    def test_status_endpoint(self):
        """Test du endpoint de statut étendu"""
        print("\n📊 Test du statut étendu...")
        try:
            response = requests.get("{}/api/status".format(self.base_url))
            if response.status_code == 200:
                data = response.json()
                print("  ✅ Statut récupéré")

                # Affichage des statistiques
                stats = data.get('statistics', {})
                print("  📈 Statistiques:")
                print("    - Plugins: {}".format(stats.get('plugins_count', 0)))
                print("    - Packs: {}".format(stats.get('packs_count', 0)))
                print("    - Utilisateurs: {}".format(stats.get('users_count', 0)))
                print("    - Utilisateurs actifs: {}".format(stats.get('active_users', 0)))

                # Vérification des fichiers de config
                config_files = data.get('config_files', {})
                print("  🔧 Fichiers de configuration:")
                print("    - users.json: {}".format('✅' if config_files.get('users_json') else '❌'))
                print("    - packs.json: {}".format('✅' if config_files.get('packs_json') else '❌'))

                self.test_results.append(("Status endpoint", True, "OK"))
                return True
            else:
                print("  ❌ Erreur: {}".format(response.status_code))
                self.test_results.append(("Status endpoint", False, response.status_code))
                return False
        except Exception as e:
            print("  ❌ Exception: {}".format(str(e)))
            self.test_results.append(("Status endpoint", False, str(e)))
            return False

    def test_plugins_list(self):
        """Test de la liste des plugins et packs"""
        print("\n📋 Test liste plugins et packs...")
        try:
            response = requests.get("{}/api/plugins".format(self.base_url))
            if response.status_code == 200:
                data = response.json()
                print("  ✅ Liste récupérée")
                print("  📄 Plugins disponibles: {}".format(data.get('plugin_count', 0)))
                print("  📦 Packs disponibles: {}".format(data.get('pack_count', 0)))

                # Affichage des plugins
                plugins = data.get('plugins', [])
                if plugins:
                    print("  🔌 Plugins sur disque:")
                    for plugin in plugins[:5]:  # Premiers 5
                        print("    - {}".format(plugin.get('name', 'Sans nom')))
                    if len(plugins) > 5:
                        print("    ... et {} autres".format(len(plugins) - 5))

                # Affichage des packs
                packs = data.get('packs', {})
                if packs:
                    print("  📦 Packs configurés:")
                    for pack_name, pack_info in packs.items():
                        print("    - {}: {} ({} plugins, {}€)".format(
                            pack_name,
                            pack_info.get('name', 'Sans nom'),
                            pack_info.get('plugin_count', 0),
                            pack_info.get('price', 0)
                        ))
                else:
                    print("  ⚠️ Aucun pack configuré")

                self.test_results.append(("Plugins list", True, "OK"))
                return True
            else:
                print("  ❌ Erreur: {}".format(response.status_code))
                self.test_results.append(("Plugins list", False, response.status_code))
                return False
        except Exception as e:
            print("  ❌ Exception: {}".format(str(e)))
            self.test_results.append(("Plugins list", False, str(e)))
            return False

    def test_user_permissions(self):
        """Test des permissions utilisateur avec packs"""
        print("\n👤 Test des permissions utilisateur...")

        # Utilisateurs de test (basés sur votre config)
        test_users = [
            {
                'email': 'test@example.com',
                'api_key': 'flask-test-key-123456',
                'name': 'Utilisateur Test'
            }
        ]

        for user in test_users:
            print("\n  🔍 Test utilisateur: {}".format(user['name']))
            try:
                headers = {
                    'X-User-Email': user['email'],
                    'X-API-Key': user['api_key']
                }

                response = requests.get(
                    "{}/api/user_plugins".format(self.base_url),
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    print("    ✅ Permissions récupérées")
                    print("    👤 Nom: {}".format(data.get('user_name', 'Inconnu')))
                    print("    🔌 Total plugins autorisés: {}".format(data.get('total_plugins', 0)))
                    print("    📦 Packs: {}".format(data.get('allowed_packs', [])))
                    print("    🎯 Plugins individuels: {}".format(data.get('individual_plugins', [])))

                    # Affichage de quelques plugins autorisés
                    all_plugins = data.get('all_allowed_plugins', [])
                    if all_plugins:
                        print("    📋 Quelques plugins autorisés:")
                        for plugin in all_plugins[:3]:
                            print("      - {}".format(plugin))
                        if len(all_plugins) > 3:
                            print("      ... et {} autres".format(len(all_plugins) - 3))

                    self.test_results.append(("User permissions", True, user['email']))

                elif response.status_code == 401:
                    print("    ❌ Authentification échouée")
                    print("    💡 Vérifiez la configuration dans config/users.json")
                    self.test_results.append(("User permissions", False, "Auth failed"))

                else:
                    print("    ❌ Erreur: {}".format(response.status_code))
                    try:
                        error_data = response.json()
                        print("    📄 Détail: {}".format(error_data.get('error', 'Inconnue')))
                    except:
                        print("    📄 Réponse: {}".format(response.text[:100]))
                    self.test_results.append(("User permissions", False, response.status_code))

            except Exception as e:
                print("    ❌ Exception: {}".format(str(e)))
                self.test_results.append(("User permissions", False, str(e)))

    def test_plugin_download(self):
        """Test de téléchargement d'un plugin avec machine tracking"""
        print("\n⬇️ Test de téléchargement avec tracking machine...")

        try:
            headers = {
                'X-User-Email': 'test@example.com',
                'X-API-Key': 'flask-test-key-123456',
                'X-Plugin-Name': 'hello_world',
                'X-Computer-Name': 'TEST-DESKTOP',
                'X-Autodesk-User': 'jean.test',
                'X-Machine-ID': 'TEST-DESKTOP_JEAN.TEST',
                'X-OS-Version': 'Windows 11',
                'X-Revit-Version': '2024'
            }

            response = requests.get(
                "{}/api/get_plugin".format(self.base_url),
                headers=headers
            )

            if response.status_code == 200:
                print("  ✅ Plugin téléchargé avec succès")
                print("  📄 Taille: {} caractères".format(len(response.text)))

                # Vérification que c'est du code Python
                if "def main():" in response.text:
                    print("  ✅ Structure du plugin correcte")
                else:
                    print("  ⚠️ Structure du plugin inhabituelle")

                # Test consultation des machines enregistrées
                print("  💻 Vérification de l'enregistrement de la machine...")
                machine_response = requests.get("{}/api/machines/test@example.com".format(self.base_url))
                if machine_response.status_code == 200:
                    machine_data = machine_response.json()
                    total_machines = machine_data.get('total_machines', 0)
                    print("    ✅ Machines enregistrées: {}".format(total_machines))

                    machines = machine_data.get('machines', {})
                    if 'TEST-DESKTOP_JEAN.TEST' in machines:
                        print("    ✅ Machine de test correctement enregistrée")
                    else:
                        print("    ⚠️ Machine de test non trouvée dans les enregistrements")

                self.test_results.append(("Plugin download", True, "hello_world"))

            elif response.status_code == 403:
                print("  ❌ Accès refusé")
                print("  📄 Réponse: {}".format(response.text))
                print("  💡 Vérifiez les permissions dans config/users.json")
                self.test_results.append(("Plugin download", False, "Access denied"))

            else:
                print("  ❌ Erreur: {}".format(response.status_code))
                print("  📄 Réponse: {}".format(response.text))
                self.test_results.append(("Plugin download", False, response.status_code))

        except Exception as e:
            print("  ❌ Exception: {}".format(str(e)))
            self.test_results.append(("Plugin download", False, str(e)))

    def test_pack_info(self):
        """Test des informations de pack"""
        print("\n📦 Test des informations de pack...")

        # Test avec le pack 'basic' qui devrait exister par défaut
        try:
            response = requests.get("{}/api/pack/basic".format(self.base_url))
            if response.status_code == 200:
                data = response.json()
                pack_info = data.get('pack_info', {})
                print("  ✅ Pack 'basic' trouvé")
                print("  📝 Nom: {}".format(pack_info.get('name', 'Sans nom')))
                print("  📄 Description: {}".format(pack_info.get('description', 'Sans description')[:50]))
                print("  🔌 Plugins: {}".format(len(pack_info.get('plugins', []))))
                print("  💰 Prix: {}€".format(pack_info.get('price', 0)))

                self.test_results.append(("Pack info", True, "basic"))

            elif response.status_code == 404:
                print("  ⚠️ Pack 'basic' non trouvé")
                print("  💡 Vérifiez le fichier config/plugin_packs.json")
                self.test_results.append(("Pack info", False, "Pack not found"))

            else:
                print("  ❌ Erreur: {}".format(response.status_code))
                self.test_results.append(("Pack info", False, response.status_code))

        except Exception as e:
            print("  ❌ Exception: {}".format(str(e)))
            self.test_results.append(("Pack info", False, str(e)))

    def generate_report(self):
        """Génère un rapport final"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL DES TESTS")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r[1] == True])

        print("📈 Résumé:")
        print("  - Tests réussis: {}/{}".format(passed_tests, total_tests))
        print("  - Taux de réussite: {:.1f}%".format(passed_tests / total_tests * 100 if total_tests > 0 else 0))

        print("\n📋 Détail des tests:")
        for test_name, success, details in self.test_results:
            status = "✅" if success else "❌"
            print("  {} {}: {}".format(status, test_name, details))

        if passed_tests == total_tests:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
            print("✅ Votre système étendu fonctionne parfaitement")
            print("🚀 Vous pouvez commencer à utiliser les packs de plugins")
        elif passed_tests >= total_tests * 0.8:
            print("\n✅ SYSTÈME MAJORITAIREMENT FONCTIONNEL")
            print("⚠️ Quelques problèmes mineurs à corriger")
        else:
            print("\n❌ PROBLÈMES DÉTECTÉS")
            print("🔧 Vérifiez la configuration et les fichiers manquants")

        # Sauvegarde du rapport
        try:
            report_path = "test_report.json"
            with open(report_path, 'w') as f:
                json.dump({
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'success_rate': passed_tests / total_tests * 100 if total_tests > 0 else 0,
                    'results': [
                        {'test': r[0], 'success': r[1], 'details': str(r[2])}
                        for r in self.test_results
                    ]
                }, f, indent=2)
            print("\n📄 Rapport détaillé sauvé: {}".format(report_path))
        except Exception as e:
            print("\n⚠️ Impossible de sauver le rapport: {}".format(str(e)))

    def run_all_tests(self):
        """Lance tous les tests"""
        print("🧪 TESTS DU SYSTÈME ÉTENDU")
        print("=" * 50)

        # Test préliminaire de connectivité
        if not self.test_server_availability():
            print("\n❌ ARRÊT DES TESTS - Serveur non disponible")
            return False

        # Tests principaux
        self.test_status_endpoint()
        self.test_plugins_list()
        self.test_user_permissions()
        self.test_plugin_download()
        self.test_pack_info()

        # Rapport final
        self.generate_report()

        return True


def main():
    """Fonction principale"""
    print("🚀 Démarrage des tests du système étendu...")
    print("🌐 Serveur cible: http://localhost:5000")
    print()

    tester = ExtendedSystemTester()
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())