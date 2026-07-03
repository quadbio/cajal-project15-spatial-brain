#!/usr/bin/env bash
# Set up "local VS Code -> compute node" (Remote-SSH) for this course. Run ON THE CLUSTER,
# from the repo root:
#
#     bash scripts/setup_vscode_remote.sh
#
# WHAT IT DOES
# VS Code Remote-SSH wants a stable host to connect to, but your work must run on a compute
# node (never the login node) — and Slurm gives you a different node every allocation. This
# installs two tiny helpers into ~/bin on the cluster that resolve the "cajal-cpu" SSH host
# to whatever node your current job is on:
#   ~/bin/vscode-node.sh   finds the node of your running job (prefers a job named "vscode*")
#   ~/bin/vscode-proxy.sh  bridges an SSH connection to port 22 on that node
# Then it prints a ready-to-paste block for your LAPTOP's ~/.ssh/config (the one step a
# cluster-side script can't do for you) and the exact commands to connect. Re-runnable.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # scripts/ -> repo root
SRC="$REPO/scripts/vscode"
ACCOUNT=tp_2630_ubordeaux_neuromics_184418
LOGIN_HOST=core.cluster.france-bioinformatique.fr

# --- must run on the cluster (needs Slurm's squeue, which the helpers call) ---
command -v squeue >/dev/null 2>&1 || {
  echo "ERROR: 'squeue' not found — run this on the IFB cluster (ssh cajal), not your laptop." >&2
  exit 1; }
[ -d "$SRC" ] || { echo "ERROR: $SRC missing — run this from your clone of the repo." >&2; exit 1; }

# --- install the ~/bin helpers ---
echo ">> installing VS Code node-resolver helpers into ~/bin"
mkdir -p "$HOME/bin"
install -m 0755 "$SRC/vscode-node.sh"  "$HOME/bin/vscode-node.sh"
install -m 0755 "$SRC/vscode-proxy.sh" "$HOME/bin/vscode-proxy.sh"
echo "   installed -> ~/bin/vscode-node.sh, ~/bin/vscode-proxy.sh"

# --- emit the personalized laptop SSH config ---
# We assume you already SSH to the cluster (basic key + a login host in ~/.ssh/config), so
# the only new laptop change is the "cajal-cpu" host below. The login block is shown last as
# a fallback in case you don't have one yet.
cat <<EOF

Server side done. Now one small laptop change (you already SSH to the cluster).

1. Add this ONE host to your laptop's ~/.ssh/config:

# ---8<--- cajal-cpu VS Code Remote-SSH — paste into ~/.ssh/config ---8<---
# Resolves to the compute node of your running job (prefers one named "vscode*").
# Start an allocation first (step 2), then point VS Code Remote-SSH at "cajal-cpu".
# NOTE: the ProxyCommand's "ssh cajal" must name YOUR login host. If your existing host
# for the cluster is called something else, change "cajal" there to match it.
Host cajal-cpu
  User $USER
  IdentityFile ~/.ssh/id_rsa_cajal
  IdentitiesOnly yes
  ProxyCommand ssh cajal '~/bin/vscode-proxy.sh'
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  ControlMaster auto
  ControlPath ~/.ssh/cm-%r@%h-%p
  ControlPersist 600
  ServerAliveInterval 30
  ServerAliveCountMax 3
# ---8<--- end ---8<---

2. Start a compute allocation for your session (from your laptop, or on the cluster):
     ssh cajal "sbatch -J vscode -p fast -A $ACCOUNT -c 4 --mem=16G -t 08:00:00 --wrap='sleep infinity'"
   Check it's running:
     ssh cajal 'squeue -u $USER'

3. In VS Code (with the "Remote - SSH" extension): F1 -> "Remote-SSH: Connect to Host..."
   -> pick "cajal-cpu". You land on your job's compute node. Open ~/github/<this-repo>.
   When your allocation ends, just start a new one (step 2) and reconnect — "cajal-cpu"
   follows it automatically; no config change needed.

Tip: keep the login node free — "cajal-cpu" runs your editor/terminals on the compute node.

--- Don't have a cluster login host yet? Add this one too (see README section 0 for the key):
Host cajal
  HostName $LOGIN_HOST
  User $USER
  IdentityFile ~/.ssh/id_rsa_cajal
  IdentitiesOnly yes
EOF
