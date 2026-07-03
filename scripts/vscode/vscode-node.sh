#!/usr/bin/env bash
# Print the compute node hosting your VS Code allocation, for the cajal-cpu SSH host.
# Prefer a running job whose name starts with "vscode"; otherwise fall back to your most
# recent running job that is NOT an Open OnDemand dashboard job. Installed to ~/bin by
# scripts/setup_vscode_remote.sh and called on the login node by vscode-proxy.sh.
pref=$(squeue -u "$USER" -h -t R -o "%j|%N" | awk -F'|' '$1 ~ /^vscode/ {print $2; exit}')
if [ -n "$pref" ]; then echo "$pref"; exit 0; fi
squeue -u "$USER" -h -t R -o "%i|%j|%N" \
  | grep -v 'sys/dashboard' \
  | sort -t'|' -k1,1n | tail -1 | cut -d'|' -f3
