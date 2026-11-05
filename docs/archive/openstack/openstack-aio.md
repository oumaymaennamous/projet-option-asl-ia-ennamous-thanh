# Installation automatisée d’OpenStack all-in-one

## Périmètre et statut

Le script `scripts/openstack-aio.py` déploie OpenStack sur **l’hôte physique**, avec Kolla-Ansible. Les VM K3s seront créées ensuite : elles ne sont pas installées par ce script.

Profil : Ubuntu Server 24.04 LTS x86_64, OpenStack 2026.1, KVM et réseau Neutron Open vSwitch. Horizon, Nova, Neutron, Glance et Keystone font partie du socle ; Cinder et Octavia sont désactivés. Ce profil minimal ne réclame ni partition ni volume LVM supplémentaire.

Le code Kolla-Ansible est fixé au commit `6de82f8b4b1794ea4e3b2c8f5ff3649dce0719c7` de stable/2026.1, vérifié lors de la rédaction. Ce n’est pas un installateur universel ni une installation déjà validée sur notre machine. Vérifier son cycle de support avant de conserver cette version à long terme.

## 1. Préparer la machine et le réseau

- Hôte dédié neuf sous Ubuntu 24.04, accès sudo et virtualisation Intel VT-x/AMD-V activée.
- Deux interfaces distinctes, branchées et actives : management avec IPv4 statique et route Internet ; interface externe Neutron dédiée, sans IPv4 ni adresse IPv6 globale ni route.
- Une VIP IPv4 **réservée par l’administrateur du réseau**, libre, hors DHCP et dans le sous-réseau de management. La VIP d’API OpenStack n’est pas une Floating IP de VM.
- L’interface externe doit être reliée au réseau fournisseur prévu par le laboratoire. Le script ne configure pas le switch, le DHCP, les VLAN ou Netplan et ne retire aucune adresse IP.
- Accès aux dépôts Ubuntu, OpenDev, PyPI, Ansible Galaxy, releases.openstack.org et aux registres d’images utilisés par Kolla. Les restrictions réseau peuvent bloquer l’installation.
- Le script exige par défaut 16 Gio de RAM installée environ et 80 Gio libres sur les systèmes de fichiers concernés : **seuils du script**, pas garantie de capacité pour notre plateforme. Viser plutôt 32 à 64 Gio de RAM et un SSD avec assez d’espace pour les VM, artefacts et journaux, à dimensionner ensemble. Le minimum officiel de Kolla seul est de 8 Go de RAM et 40 Go disque, hors besoins du projet.

Repérer la configuration sans la modifier :

```bash
cat /etc/os-release
ip -br addr
ip route
free -h
df -h / /var/lib
lscpu
```

Si la machine n’a qu’une interface, ce profil s’arrête. Il faut un plan réseau spécifique validé avant de l’adapter ; ne pas réutiliser aveuglément l’interface SSH pour Neutron.

## 2. Récupérer les fichiers

Sur la machine physique :

```bash
sudo apt update
sudo apt install -y git python3 iproute2
git clone --branch oumayma https://github.com/oumaymaennamous/projet-option-asl-ia-ennamous-thanh.git
cd projet-option-asl-ia-ennamous-thanh
```

Si le dépôt est déjà cloné, se placer dans ce dépôt sur la branche oumayma et récupérer les changements au lieu de le cloner de nouveau.

## 3. Générer et renseigner la configuration

```bash
sudo python3 scripts/openstack-aio.py init-config
sudo nano /etc/mlops-openstack.json
```

Exemple **à remplacer par les valeurs du laboratoire** :

```json
{
  "management_interface": "eno1",
  "external_interface": "eno2",
  "internal_vip": "192.168.10.250",
  "vip_reserved_outside_dhcp": true,
  "minimum_ram_gib": 16,
  "minimum_free_disk_gib": 80
}
```

Ne mettre le booléen à true qu’après réservation de la VIP. L’exemple initial utilise volontairement CHANGE_ME et false. Le script refuse deux interfaces identiques, un OS incompatible et une configuration incomplète. La configuration JSON n’est jamais exécutée comme du code shell.

## 4. Diagnostic sans installation

```bash
sudo python3 scripts/openstack-aio.py check
```

Cette action ne modifie pas l’hôte. Elle vérifie notamment OS, architecture, virtualisation, ressources locales, interfaces, routes et cohérence de la VIP. Elle ne prouve pas que la VIP est réservée, que le réseau externe est utilisable ou que toutes les futures VM tiendront en mémoire.

## 5. Préparer Kolla-Ansible

```bash
sudo python3 scripts/openstack-aio.py prepare --apply
```

Cette action installe les dépendances Ubuntu, crée un environnement Python dans `/opt/mlops-openstack/venv`, installe Kolla-Ansible et le client OpenStack, récupère les collections Ansible, copie l’inventaire all-in-one et génère `/etc/kolla/globals.yml` et les mots de passe.

Une préparation interrompue peut être relancée avec la même configuration. Les mots de passe existants ne sont pas remplacés par un nouveau fichier. Un répertoire Kolla inconnu ou un Docker préexistant sur un hôte non géré provoque un arrêt plutôt qu’une reprise hasardeuse.

## 6. Installer le socle hôte et vérifier Kolla

```bash
sudo python3 scripts/openstack-aio.py prechecks --apply
```

Cette action **n’est pas un diagnostic en lecture seule** : elle exécute `bootstrap-servers`, qui peut installer Docker et modifier le système, puis les prechecks officiels. Un test ARP détecte les réponses à la VIP avant son attribution ; il ne remplace pas sa réservation administrative.

## 7. Déployer OpenStack automatiquement

```bash
sudo python3 scripts/openstack-aio.py deploy --apply
```

Le script refait bootstrap et prechecks, lance deploy puis post-deploy, et interroge les API. Il s’arrête à la première erreur. Il ne tente pas de masquer l’échec ni de détruire les ressources pour recommencer. Kolla peut modifier l’hôte et raccorder l’interface externe à son bridge ; conserver un accès console à la machine.

On peut lancer directement cette action après prepare ; l’étape séparée prechecks permet simplement de contrôler le résultat avant de déployer tous les services.

## 8. Vérifier et accéder à Horizon

```bash
sudo python3 scripts/openstack-aio.py verify
```

Cette action interroge l’authentification, les services de calcul et les agents réseau, sans imprimer le token ni le mot de passe. Vérifier les états affichés : une réponse API ne suffit pas à prouver que le cloud est pleinement fonctionnel.

Ouvrir `http://VIP` depuis le réseau de management. Domaine Default, projet admin et utilisateur admin. Le mot de passe est dans `/etc/kolla/passwords.yml` sous `keystone_admin_password` ; le consulter localement, ne pas le coller dans un chat ou dans Git.

Le profil conserve les paramètres TLS par défaut de Kolla : **HTTP pour ce laboratoire privé**. Ne pas exposer Horizon ou les API sur Internet ; ajouter un TLS et une politique d’accès adaptés avant un usage hors laboratoire. Aucun réglage de pare-feu n’est désactivé par notre code ; les règles existantes doivent être compatibles avec Kolla.

La validation complète suivante reste à faire : téléverser une image, configurer le réseau fournisseur et les Floating IP autorisés, créer une petite VM, puis tester sa console, son accès SSH et sa sortie réseau. Ces paramètres dépendent du laboratoire ; le script n’exécute pas `init-runonce` et ne les invente pas.

## Secrets, reprise et reproductibilité

- `/etc/kolla/passwords.yml`, `/etc/kolla/clouds.yaml` et les éventuels openrc restent sur l’hôte avec accès restreint. Ne pas versionner ni publier ces fichiers ou les logs bruts.
- `/opt/mlops-openstack` conserve la configuration utilisée, le commit Kolla, un snapshot pip, les versions des collections et, après deploy, un manifeste privé des images Docker avec leurs digests.
- Un changement de configuration après préparation est refusé : les migrations réseau et mises à jour nécessitent une procédure distincte. Ce script n’offre aucune commande destroy, upgrade ou formatage.
- Les références d’images 2026.1, les paquets apt et certaines dépendances distantes peuvent évoluer. Les snapshots sont des preuves d’installation, **pas un verrouillage intégral permettant une reconstruction bit à bit**. Pour J5, conserver les dépendances/collections et images exactes dans un cache ou registre, puis tester une reconstruction avec ces références et les mêmes secrets sauvegardés de manière sûre.
- Sauvegarder les données et les secrets hors de la machine avant toute destruction/reconstruction. Ne pas supprimer le seul exemplaire d’une VM ou d’un volume utile.

## Validation réalisée avant livraison

Syntaxe Python et tests des refus de configuration : interfaces identiques, VIP invalide, réservation absente et ressources minimales incohérentes. La génération de configuration et le mode d’aide ont aussi été exécutés sans déploiement.

**Le déploiement réel n’a pas été exécuté ici : aucun accès à la machine physique n’est disponible.** Les prechecks et la validation VM sur le laboratoire restent nécessaires.

## Documentation officielle utilisée

- https://docs.openstack.org/kolla-ansible/2026.1/user/quickstart.html
- https://docs.openstack.org/kolla-ansible/2026.1/user/support-matrix.html
- https://docs.openstack.org/kolla-ansible/2026.1/reference/networking/neutron.html

Après cette étape : création automatisée des deux VM, puis installation de K3s et des applications selon [l’architecture V2](../architecture/proposition-oumayma-v2.md).
