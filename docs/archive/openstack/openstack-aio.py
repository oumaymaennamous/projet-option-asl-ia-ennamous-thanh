#!/usr/bin/env python3
"""OpenStack 2026.1 / Kolla-Ansible all-in-one, Ubuntu 24.04 x86_64.
No shell sourcing, disk formatting, Netplan editing or automatic destruction.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

RELEASE = "2026.1"
KOLLA_COMMIT = "6de82f8b4b1794ea4e3b2c8f5ff3649dce0719c7"
STATE = Path("/opt/mlops-openstack")
VENV = STATE / "venv"
ETC = Path("/etc/kolla")
EXAMPLE = {
    "management_interface": "CHANGE_ME",
    "external_interface": "CHANGE_ME",
    "internal_vip": "CHANGE_ME",
    "vip_reserved_outside_dhcp": False,
    "minimum_ram_gib": 16,
    "minimum_free_disk_gib": 80,
}


def fail(message):
    raise RuntimeError(message)


def run(args, capture=False, env=None):
    return subprocess.run([str(a) for a in args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None, env=env)


def load_config(path):
    c = json.loads(path.read_text())
    if set(c) != set(EXAMPLE):
        fail("Le fichier doit contenir exactement les clés de init-config.")
    for key in ("management_interface", "external_interface"):
        if not isinstance(c[key], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,15}", c[key]):
            fail("Nom d’interface invalide : " + key)
        if c[key] in ("lo", "CHANGE_ME"):
            fail("Remplacer les interfaces d’exemple.")
    if c["management_interface"] == c["external_interface"]:
        fail("Deux interfaces distinctes sont nécessaires pour ce profil.")
    vip = ipaddress.IPv4Address(c["internal_vip"])
    if vip.is_loopback or vip.is_multicast or vip.is_unspecified or vip.is_link_local:
        fail("VIP IPv4 non utilisable.")
    if c["vip_reserved_outside_dhcp"] is not True:
        fail("Faire réserver la VIP hors DHCP puis passer vip_reserved_outside_dhcp à true.")
    for key, floor in (("minimum_ram_gib", 8), ("minimum_free_disk_gib", 40)):
        if type(c[key]) is not int or c[key] < floor:
            fail(f"{key} doit être un entier >= {floor}.")
    return c


def ip_json(*args):
    return json.loads(run(["ip", "-j", *args], capture=True).stdout)


def preflight(c):
    info = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v.strip('"')
    if (info.get("ID"), info.get("VERSION_ID")) != ("ubuntu", "24.04"):
        fail("Ce script est limité à Ubuntu Server 24.04.")
    if platform.machine() != "x86_64":
        fail("Ce profil est limité à x86_64.")
    if not shutil.which("ip"):
        fail("Installer iproute2 avant le diagnostic.")
    if not re.search(r"\b(vmx|svm)\b", Path("/proc/cpuinfo").read_text()):
        fail("Activer Intel VT-x / AMD-V dans le BIOS/UEFI.")
    ram = int(re.search(r"MemTotal:\s+(\d+)", Path("/proc/meminfo").read_text())[1]) / 1048576
    free = min(shutil.disk_usage("/").free, shutil.disk_usage("/var/lib").free) / 2**30
    # Small tolerance because firmware reserves some of the installed RAM.
    if ram < c["minimum_ram_gib"] * .95 or free < c["minimum_free_disk_gib"]:
        fail(f"Ressources insuffisantes : RAM {ram:.1f} Gio, disque libre {free:.1f} Gio.")
    mgmt = ip_json("addr", "show", "dev", c["management_interface"])[0]
    ext = ip_json("addr", "show", "dev", c["external_interface"])[0]
    for iface in (mgmt, ext):
        if "UP" not in iface["flags"] or "LOWER_UP" not in iface["flags"]:
            fail("Interface non active ou câble débranché : " + iface["ifname"])
    addresses = [a for a in mgmt["addr_info"] if a["family"] == "inet"]
    if not addresses or any(a.get("dynamic") for a in addresses):
        fail("Une IPv4 d’administration statique est requise ; configurer Netplan séparément.")
    vip = ipaddress.IPv4Address(c["internal_vip"])
    networks = [ipaddress.IPv4Interface(f"{a['local']}/{a['prefixlen']}").network for a in addresses]
    if not any(vip in n and vip not in (n.network_address, n.broadcast_address) for n in networks):
        fail("La VIP doit être une adresse hôte dans le sous-réseau de management.")
    assigned = [a["local"] for i in ip_json("addr") for a in i.get("addr_info", [])]
    if str(vip) in assigned and not (STATE / "managed.json").exists():
        fail("La VIP est déjà attribuée localement ; choisir une adresse libre.")
    if any(a.get("scope") != "link" for a in ext.get("addr_info", [])):
        fail("L’interface Neutron doit être dédiée et sans adresse IP globale.")
    if ip_json("-4", "route", "show", "table", "all", "dev", c["external_interface"]):
        fail("L’interface Neutron porte des routes ; ne pas utiliser l’interface d’administration.")
    routes = ip_json("-4", "route", "show", "default")
    if not routes or any(r.get("dev") != c["management_interface"] for r in routes):
        fail("La route par défaut doit passer uniquement par l’interface d’administration.")
    if Path("/etc/rancher/k3s").exists() or Path("/etc/kubernetes").exists():
        fail("Utiliser un hôte dédié à OpenStack ; Kubernetes sera dans les VM.")
    print(f"Diagnostic local OK : {os.cpu_count()} CPU logiques, RAM {ram:.1f} Gio, libre {free:.1f} Gio.")
    print("Cela ne valide pas la capacité des futures VM, le DHCP ni le réseau du laboratoire.")


def environment():
    env = os.environ.copy()
    env["PATH"] = str(VENV / "bin") + os.pathsep + env.get("PATH", "")
    env["ANSIBLE_CONFIG"] = str(STATE / "ansible.cfg")
    env["ANSIBLE_COLLECTIONS_PATH"] = str(STATE / "collections")
    return env


def kolla(action):
    run([VENV / "bin/kolla-ansible", action, "-i", STATE / "all-in-one"], env=environment())


def prepare(c):
    if (STATE / "managed.json").exists():
        if json.loads((STATE / "managed.json").read_text()) != c:
            fail("Configuration différente : aucune migration réseau automatique. Revoir manuellement.")
        print("Préparation déjà effectuée ; utiliser prechecks ou deploy.")
        return
    if ETC.exists() and any(ETC.iterdir()) and not (STATE / "preparing.json").exists():
        fail("/etc/kolla existe déjà : refus d’écraser une installation inconnue.")
    if shutil.which("docker") and not (STATE / "preparing.json").exists():
        fail("Docker est déjà présent : ce profil attend un hôte dédié neuf.")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (STATE / "preparing.json").exists():
        if json.loads((STATE / "preparing.json").read_text()) != c:
            fail("La configuration diffère de la préparation interrompue.")
    (STATE / "preparing.json").write_text(json.dumps(c, indent=2) + "\n")
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", "git", "python3-dev", "python3-venv",
         "libffi-dev", "gcc", "libssl-dev", "libdbus-glib-1-dev", "ca-certificates", "iputils-arping"])
    if not VENV.exists():
        run(["python3", "-m", "venv", VENV])
    run([VENV / "bin/pip", "install", "--upgrade", "pip"])
    run([VENV / "bin/pip", "install",
         "git+https://opendev.org/openstack/kolla-ansible@" + KOLLA_COMMIT])
    run([VENV / "bin/pip", "install", "python-openstackclient", "-c",
         "https://releases.openstack.org/constraints/upper/" + RELEASE])
    (STATE / "ansible.cfg").write_text("[defaults]\ninterpreter_python = /usr/bin/python3\n")
    run([VENV / "bin/kolla-ansible", "install-deps"], env=environment())
    share = VENV / "share/kolla-ansible"
    shutil.copyfile(share / "ansible/inventory/all-in-one", STATE / "all-in-one")
    ETC.mkdir(mode=0o700, exist_ok=True)
    os.chmod(ETC, 0o700)
    # JSON is valid YAML; values are serialized without shell or template interpolation.
    globals_config = {
        "workaround_ansible_issue_8743": True,
        "kolla_base_distro": "ubuntu", "openstack_release": RELEASE,
        "kolla_container_engine": "docker",
        "network_interface": c["management_interface"],
        "neutron_external_interface": c["external_interface"],
        "kolla_internal_vip_address": c["internal_vip"],
        "neutron_plugin_agent": "openvswitch", "nova_compute_virt_type": "kvm",
        "enable_horizon": True, "enable_cinder": False, "enable_octavia": False,
    }
    (ETC / "globals.yml").write_text(json.dumps(globals_config, indent=2) + "\n")
    if not (ETC / "passwords.yml").exists():
        shutil.copyfile(share / "etc_examples/kolla/passwords.yml", ETC / "passwords.yml")
    run([VENV / "bin/kolla-genpwd"], env=environment())
    os.chmod(ETC / "passwords.yml", 0o600)
    freeze = run([VENV / "bin/pip", "freeze"], capture=True).stdout
    (STATE / "python-requirements.lock").write_text(freeze)
    collections = run([VENV / "bin/ansible-galaxy", "collection", "list", "--format", "json"],
                      capture=True, env=environment()).stdout
    (STATE / "collections-installed.json").write_text(collections)
    (STATE / "kolla-commit.txt").write_text(KOLLA_COMMIT + "\n")
    (STATE / "managed.json").write_text(json.dumps(c, indent=2) + "\n")
    print("Préparation terminée. Les mots de passe restent dans /etc/kolla/passwords.yml.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init-config", "check", "prepare", "prechecks", "deploy", "verify"])
    parser.add_argument("--config", type=Path, default=Path("/etc/mlops-openstack.json"))
    parser.add_argument("--apply", action="store_true", help="Autoriser les modifications de l’hôte")
    args = parser.parse_args()
    if args.action == "init-config":
        # Exclusive creation: never overwrite a configured host file.
        with args.config.open("x") as f:
            f.write(json.dumps(EXAMPLE, indent=2) + "\n")
        print("Exemple créé :", args.config)
        return
    c = load_config(args.config)
    preflight(c)
    if args.action == "check":
        return
    if os.geteuid() != 0:
        fail("Utiliser sudo pour cette action.")
    if args.action != "verify" and not args.apply:
        fail("Ajouter --apply pour autoriser cette action sur l’hôte.")
    if args.action == "prepare":
        prepare(c)
        return
    if not (STATE / "managed.json").exists() or json.loads((STATE / "managed.json").read_text()) != c:
        fail("Exécuter prepare avec cette configuration avant de continuer.")
    if args.action in ("prechecks", "deploy"):
        # ARP duplicate-address detection: ping alone cannot establish availability.
        assigned = [a["local"] for i in ip_json("addr") for a in i.get("addr_info", [])]
        if c["internal_vip"] not in assigned:
            run(["arping", "-D", "-I", c["management_interface"], "-c", "3", c["internal_vip"]])
        kolla("bootstrap-servers")
        kolla("prechecks")
        if args.action == "prechecks":
            return
        kolla("deploy")
        kolla("post-deploy")
        for name in ("clouds.yaml", "admin-openrc.sh"):
            if (ETC / name).exists():
                os.chmod(ETC / name, 0o600)
        # Private manifest: inventory of exact downloaded container image digests.
        ids = run(["docker", "image", "ls", "-q"], capture=True).stdout.split()
        images = run(["docker", "image", "inspect", *sorted(set(ids))], capture=True).stdout if ids else "[]"
        (STATE / "container-images.json").write_text(images)
    env = environment()
    env["OS_CLIENT_CONFIG_FILE"] = str(ETC / "clouds.yaml")
    env["OS_CLOUD"] = "kolla-admin"
    for command in (("token", "issue", "-f", "value", "-c", "expires"),
                    ("compute", "service", "list"), ("network", "agent", "list")):
        run([VENV / "bin/openstack", *command], env=env)
    print("API interrogées. Vérifier les services up/enabled puis tester une VM.")
    print("Horizon (HTTP, laboratoire privé uniquement) : http://" + c["internal_vip"])


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError, KeyError, IndexError) as e:
        print("ARRÊT :", e, file=sys.stderr)
        sys.exit(1)
