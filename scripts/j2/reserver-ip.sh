#!/usr/bin/env bash
set -euo pipefail

# Inventaire de la séance. Adapter les MAC et IP aux baux sur une nouvelle cible.
sudo virsh -c qemu:///system net-update default add ip-dhcp-host \
  "<host mac='52:54:00:00:ef:17' name='k3s-server-1' ip='192.168.122.53'/>" --live --config
sudo virsh -c qemu:///system net-update default add ip-dhcp-host \
  "<host mac='52:54:00:b1:6f:7f' name='k3s-server-2' ip='192.168.122.70'/>" --live --config
sudo virsh -c qemu:///system net-update default add ip-dhcp-host \
  "<host mac='52:54:00:9a:d2:8e' name='k3s-server-3' ip='192.168.122.152'/>" --live --config

sudo virsh -c qemu:///system net-dumpxml default --inactive | grep '<host '
