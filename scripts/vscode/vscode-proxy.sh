#!/usr/bin/env bash
# ProxyCommand for the cajal-cpu SSH host: bridge stdin/stdout to port 22 on the compute
# node of your current allocation, so VS Code Remote-SSH lands directly on the node running
# your job. Installed to ~/bin by scripts/setup_vscode_remote.sh; runs on the login node.
node=$(~/bin/vscode-node.sh)
if [ -z "$node" ]; then
  echo "cajal-cpu: no running allocation. Start one first, e.g.:" >&2
  echo "  sbatch -J vscode -p fast -A tp_2630_ubordeaux_neuromics_184418 -c 4 --mem=16G -t 08:00:00 --wrap='sleep infinity'" >&2
  exit 1
fi
exec nc "$node" 22
