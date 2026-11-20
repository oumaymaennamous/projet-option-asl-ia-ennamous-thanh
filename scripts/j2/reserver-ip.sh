#!/usr/bin/env bash
set -euo pipefail

vms=(
  "k3s-server-1 52:54:00:00:ef:17 192.168.122.53"
  "k3s-server-2 52:54:00:b1:6f:7f 192.168.122.70"
  "k3s-server-3 52:54:00:9a:d2:8e 192.168.122.152"
)

virsh_cmd=(sudo virsh -c qemu:///system)
"${virsh_cmd[@]}" net-info default >/dev/null

for entry in "${vms[@]}"; do
  read -r vm mac expected_ip <<<"$entry"
  if "${virsh_cmd[@]}" dominfo "$vm" >/dev/null 2>&1; then
    actual_mac=$("${virsh_cmd[@]}" domiflist "$vm" |
      awk 'NR > 2 && $5 != "" { print tolower($5); exit }')
    if [ "$actual_mac" != "$mac" ]; then
      echo "La VM existante $vm utilise la MAC $actual_mac (attendue : $mac)." >&2
      echo "Aucune réservation DHCP n’a été modifiée." >&2
      exit 1
    fi
    actual_ip=$("${virsh_cmd[@]}" domifaddr "$vm" --source lease |
      awk '$4 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\// { sub(/\/.*/, "", $4); print $4; exit }')
    if [ -n "$actual_ip" ] && [ "$actual_ip" != "$expected_ip" ]; then
      echo "La VM existante $vm utilise l’IP $actual_ip (attendue : $expected_ip)." >&2
      echo "Aucune réservation DHCP n’a été modifiée." >&2
      exit 1
    fi
  fi
done

if ! "${virsh_cmd[@]}" net-info default | grep -Eq '^Active:[[:space:]]+yes$'; then
  "${virsh_cmd[@]}" net-start default
fi
"${virsh_cmd[@]}" net-autostart default

check_lease() {
  local xml=$1
  local vm=$2
  local mac=$3
  local ip=$4
  local by_mac by_name by_ip

  by_mac=$(printf '%s\n' "$xml" | grep -F "mac='$mac'" || true)
  by_name=$(printf '%s\n' "$xml" | grep -F "name='$vm'" || true)
  by_ip=$(printf '%s\n' "$xml" | grep -F "ip='$ip'" || true)
  if [ -z "$by_mac" ] && [ -z "$by_name" ] && [ -z "$by_ip" ]; then
    return 1
  fi
  if [[ "$by_mac" == *"name='$vm'"* && "$by_mac" == *"ip='$ip'"* &&
        "$by_name" == *"mac='$mac'"* && "$by_name" == *"ip='$ip'"* &&
        "$by_ip" == *"mac='$mac'"* && "$by_ip" == *"name='$vm'"* ]]; then
    return 0
  fi

  echo "Conflit de réservation DHCP pour $vm ($mac, $ip)." >&2
  printf '%s\n' "$by_mac" "$by_name" "$by_ip" | grep -v '^$' >&2
  return 2
}

for entry in "${vms[@]}"; do
  read -r vm mac ip <<<"$entry"
  config_xml=$("${virsh_cmd[@]}" net-dumpxml default --inactive)
  live_xml=$("${virsh_cmd[@]}" net-dumpxml default)
  config_present=false
  live_present=false

  if check_lease "$config_xml" "$vm" "$mac" "$ip"; then
    config_present=true
  else
    status=$?
    if [ "$status" -eq 2 ]; then
      exit 1
    fi
  fi
  if check_lease "$live_xml" "$vm" "$mac" "$ip"; then
    live_present=true
  else
    status=$?
    if [ "$status" -eq 2 ]; then
      exit 1
    fi
  fi

  if [ "$config_present" = true ] && [ "$live_present" = true ]; then
    echo "Réservation déjà correcte : $vm ($ip)"
    continue
  fi
  if [ "$config_present" != true ]; then
    "${virsh_cmd[@]}" net-update default add ip-dhcp-host \
      "<host mac='$mac' name='$vm' ip='$ip'/>" --config
  fi
  if [ "$live_present" != true ]; then
    "${virsh_cmd[@]}" net-update default add ip-dhcp-host \
      "<host mac='$mac' name='$vm' ip='$ip'/>" --live
  fi
  echo "Réservation ajoutée : $vm ($ip)"
done

"${virsh_cmd[@]}" net-dumpxml default --inactive | grep '<host '
