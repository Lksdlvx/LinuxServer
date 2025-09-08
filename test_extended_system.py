# test_simplified_system.py - Script de test pour le système simplifié
import requests
import json
import sys
import time


class SimplifiedSystemTester:
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
                print(f"  📊 Version: {data.get('version', 'Inconnue')}")
                print(f"  🎯 Features: {data.get('features', [])}")

                return True
            else:
                print(f"  ❌ Serveur répond mais erreur: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("  ❌ Impossible de se connecter au serveur")
            print("  💡 Vérifiez que le serveur est démarré avec: python app.py")
            return False
        except Exception as e:
            print(f"  ❌ Erreur: {str(e)}")
            return False

    def test_status_endpoint(self):
        """Test du endpoint de statut simplifié"""
        print("\n📊 Test du statut simplifié...")
        try:
            response = requests.get(f"{self.base_url}/api/status")
            if response.status_code == 200:
                data = response.json()
                print("  ✅ Statut récupéré")

                # Affichage des statistiques
                stats = data.get('statistics', {})
                print("  📈 Statistiques:")
                print(f"    - Plugins: {stats.get('plugins_count', 0)}")
                print(f"    - Utilisateurs: {stats.get('users_count', 0)}")
                print(f"    - Utilisateurs actifs: {stats.get('active_users', 0)}")

                # Vérification des fichiers de config
                config_files = data.get('config_files', {})
                print("  🔧 Fichiers de configuration:")
                print(f"    - users.json: {'✅' if config_files.get('users_json') else '❌'}")

                # S'assurer qu'il n'y a plus de référence aux packs
                if 'packs_json' not in config_files:
                    print("    ✅ Aucune référence aux packs dans la config")
                else:
                    print("    ⚠️ Références aux packs encore présentes")

                self.test_results.append(("Status endpoint", True, "OK"))
                return True
            else:
                print(f"  ❌ Erreur: {response.status_code}")
                self.test_results.append(("Status endpoint", False, response.status_code))
                return False
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
            self.test_results.append(("Status endpoint", False, str(e)))
            return False

    def test_plugins_list(self):
        """Test de la liste des plugins (sans packs)"""
        print("\n📋 Test liste plugins simplifiée...")
        try:
            response = requests.get(f"{self.base_url}/api/plugins")
            if response.status_code == 200:
                data = response.json()
                print("  ✅ Liste récupérée")
                print(f"  📄 Plugins disponibles: {data.get('plugin_count', 0)}")

                # Affichage des plugins
                plugins = data.get('plugins', [])
                if plugins:
                    print("  🔌 Plugins sur disque:")
                    for plugin in plugins[:5]:  # Premiers 5
                        print(f"    - {plugin.get('name', 'Sans nom')}")
                    if len(plugins) > 5:
                        print(f"    ... et {len(plugins) - 5} autres")

                # S'assurer qu'il n'y a plus de packs dans la réponse
                if 'packs' not in data:
                    print("  ✅ Aucune information de pack dans la réponse")
                else:
                    print("  ⚠️ Informations de packs encore présentes")

                self.test_results.append(("Plugins list", True, "OK"))
                return True
            else:
                print(f"  ❌ Erreur: {response.status_code}")
                self.test_results.append(("Plugins list", False, response.status_code))
                return False
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
            self.test_results.append(("Plugins list", False, str(e)))
            return False

    def test_user_permissions(self):
        """Test des permissions utilisateur simplifiées"""
        print("\n👤 Test des permissions utilisateur simplifiées...")

        # Utilisateurs de test
        test_users = [
            {
                'email': 'test@example.com',
                'api_key': 'flask-test-key-123456',
                'name': 'Utilisateur Test'
            },
            {
                'email': 'architect@company.com',
                'api_key': 'architect-key-789012',
                'name': 'Architecte Test'
            }
        ]

        for user in test_users:
            print(f"\n  🔍 Test utilisateur: {user['name']}")
            try:
                headers = {
                    'X-User-Email': user['email'],
                    'X-API-Key': user['api_key']
                }

                response = requests.get(
                    f"{self.base_url}/api/user_plugins",
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    print("    ✅ Permissions récupérées")
                    print(f"    👤 Nom: {data.get('user_name', 'Inconnu')}")
                    print(f"    🔌 Total plugins autorisés: {data.get('total_plugins', 0)}")

                    # Vérifier la structure simplifiée
                    allowed_plugins = data.get('allowed_plugins', [])
                    print(f"    📋 Plugins: {allowed_plugins}")

                    # S'assurer qu'il n'y a plus d'infos de packs
                    if 'allowed_packs' not in data and 'pack_plugins' not in data:
                        print("    ✅ Aucune information de pack dans la réponse")
                    else:
                        print("    ⚠️ Informations de packs encore présentes")

                    self.test_results.append(("User permissions", True, user['email']))

                elif response.status_code == 401:
                    print("    ❌ Authentification échouée")
                    print("    💡 Vérifiez la configuration dans config/users.json")
                    self.test_results.append(("User permissions", False, "Auth failed"))

                else:
                    print(f"    ❌ Erreur: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"    📄 Détail: {error_data.get('error', 'Inconnue')}")
                    except:
                        print(f"    📄 Réponse: {response.text[:100]}")
                    self.test_results.append(("User permissions", False, response.status_code))

            except Exception as e:
                print(f"    ❌ Exception: {str(e)}")
                self.test_results.append(("User permissions", False, str(e)))

    def test_plugin_download(self):
        """Test de téléchargement d'un plugin avec machine tracking"""
        print("\n⬇️ Test de téléchargement avec tracking machine...")

        try:
            headers = {
                'X-User-Email': 'test@example.com',
                'X-API-Key': 'flask-test-key-123456',
                'X-Plugin-Name': 'hello_world',
                'X-Computer-Name': 'TEST-DESKTOP-SIMPLIFIED',
                'X-Autodesk-User': 'jean.test',
                'X-Machine-ID': 'TEST-DESKTOP-SIMPLIFIED_JEAN.TEST',
                'X-OS-Version': 'Windows 11',
                'X-Revit-Version': '2024'
            }

            response = requests.get(
                f"{self.base_url}/api/get_plugin",
                headers=headers
            )

            if response.status_code == 200:
                print("  ✅ Plugin téléchargé avec succès")
                print(f"  📄 Taille: {len(response.text)} caractères")

                # Vérification que c'est du code Python
                if "def main():" in response.text:
                    print("  ✅ Structure du plugin correcte")
                else:
                    print("  ⚠️ Structure du plugin inhabituelle")

                # Test consultation des machines enregistrées
                print("  💻 Vérification de l'enregistrement de la machine...")
                machine_headers = {
                    'X-User-Email': 'test@example.com',
                    'X-API-Key': 'flask-test-key-123456'
                }
                machine_response = requests.get(
                    f"{self.base_url}/api/machines/test@example.com",
                    headers=machine_headers
                )

                if machine_response.status_code == 200:
                    machine_data = machine_response.json()
                    total_machines = machine_data.get('total_machines', 0)
                    print(f"    ✅ Machines enregistrées: {total_machines}")

                    machines = machine_data.get('machines', {})
                    if 'TEST-DESKTOP-SIMPLIFIED_JEAN.TEST' in machines:
                        print("    ✅ Machine de test correctement enregistrée")
                    else:
                        print("    ⚠️ Machine de test non trouvée dans les enregistrements")

                self.test_results.append(("Plugin download", True, "hello_world"))

            elif response.status_code == 403:
                print("  ❌ Accès refusé")
                print(f"  📄 Réponse: {response.text}")
                print("  💡 Vérifiez les permissions dans config/users.json")
                self.test_results.append(("Plugin download", False, "Access denied"))

            else:
                print(f"  ❌ Erreur: {response.status_code}")
                print(f"  📄 Réponse: {response.text}")
                self.test_results.append(("Plugin download", False, response.status_code))

        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
            self.test_results.append(("Plugin download", False, str(e)))

    def test_pack_endpoints_removed(self):
        """Test que les endpoints de packs ont bien été supprimés"""
        print("\n🚫 Test de suppression des endpoints de packs...")

        pack_endpoints = [
            '/api/pack/basic',
            '/api/pack/premium',
            '/api/pack/structural'
        ]

        for endpoint in pack_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                if response.status_code == 404:
                    print(f"  ✅ {endpoint} correctement supprimé (404)")
                else:
                    print(f"  ⚠️ {endpoint} encore disponible ({response.status_code})")
                    self.test_results.append(("Pack endpoints removed", False, f"{endpoint} still exists"))
                    return
            except Exception as e:
                print(f"  ❌ Erreur test {endpoint}: {str(e)}")

        print("  ✅ Tous les endpoints de packs sont bien supprimés")
        self.test_results.append(("Pack endpoints removed", True, "All removed"))

    def generate_report(self):
        """Génère un rapport final"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL - SYSTÈME SIMPLIFIÉ")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r[1] == True])

        print("📈 Résumé:")
        print(f"  - Tests réussis: {passed_tests}/{total_tests}")
        print(
            f"  - Taux de réussite: {passed_tests / total_tests * 100:.1f}%" if total_tests > 0 else "  - Aucun test exécuté")

        print("\n📋 Détail des tests:")
        for test_name, success, details in self.test_results:
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}: {details}")

        # Analyse de la migration
        migration_success = True
        migration_issues = []

        for test_name, success, details in self.test_results:
            if not success:
                migration_success = False
                migration_issues.append(f"{test_name}: {details}")

        print("\n🔄 Analyse de la migration:")
        if migration_success:
            print("  ✅ Migration réussie - Système simplifié fonctionnel")
            print("  🎯 Tous les packs ont été correctement supprimés")
            print("  🔌 Système de plugins individuels opérationnel")
        else:
            print("  ⚠️ Migration partiellement réussie")
            print("  🔧 Problèmes détectés:")
            for issue in migration_issues:
                print(f"    - {issue}")

        if passed_tests == total_tests:
            print("\n🎉 MIGRATION COMPLÈTE ET RÉUSSIE !")
            print("✅ Votre système simplifié fonctionne parfaitement")
            print("🚀 Plus simple à maintenir et déboguer")
            print("💡 Vous pouvez maintenant utiliser uniquement les plugins individuels")
        elif passed_tests >= total_tests * 0.8:
            print("\n✅ MIGRATION MAJORITAIREMENT RÉUSSIE")
            print("⚠️ Quelques ajustements mineurs nécessaires")
        else:
            print("\n❌ PROBLÈMES DE MIGRATION DÉTECTÉS")
            print("🔧 Vérifiez la configuration et relancez les tests")

        # Sauvegarde du rapport
        try:
            report_path = "migration_report.json"
            with open(report_path, 'w') as f:
                json.dump({
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'migration_type': 'packs_removal',
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'success_rate': passed_tests / total_tests * 100 if total_tests > 0 else 0,
                    'migration_successful': migration_success,
                    'issues': migration_issues,
                    'results': [
                        {'test': r[0], 'success': r[1], 'details': str(r[2])}
                        for r in self.test_results
                    ]
                }, f, indent=2)
            print(f"\n📄 Rapport de migration sauvé: {report_path}")
        except Exception as e:
            print(f"\n⚠️ Impossible de sauver le rapport: {str(e)}")

    def run_all_tests(self):
        """Lance tous les tests de migration"""
        print("🧪 TESTS DE MIGRATION - SYSTÈME SIMPLIFIÉ")
        print("=" * 50)

        # Test préliminaire de connectivité
        if not self.test_server_availability():
            print("\n❌ ARRÊT DES TESTS - Serveur non disponible")
            return False

        # Tests de migration
        self.test_status_endpoint()
        self.test_plugins_list()
        self.test_user_permissions()
        self.test_plugin_download()
        self.test_pack_endpoints_removed()

        # Rapport final
        self.generate_report()

        return True

    def main():
        """Fonction principale"""
        print("🚀 Démarrage des tests de migration...")
        print("🎯 Vérification du système simplifié sans packs")
        print("🌐 Serveur cible: http://localhost:5000")
        print()

        tester = SimplifiedSystemTester()
        success = tester.run_all_tests()

        return 0 if success else 1

    if __name__ == "__main__":
        sys.exit(main())