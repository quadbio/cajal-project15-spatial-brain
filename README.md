# Project 15 — Mapping the Spatial Cellular Architecture of the Brain

**CAJAL Neuromics 2026 (Bordeaux).** Reconstruct the spatial cellular architecture of the
brain from high-plex, image-based spatial transcriptomics: QC → cell segmentation →
cell-type annotation by label transfer from a scRNA-seq reference atlas → spatial niches →
region-specific cell–cell communication. Notebook-first and CPU-only, run from a single
shared container on the IFB Core Cluster.

**Links:** [IFB docs](https://doc.cluster.france-bioinformatique.fr/) ·
[OnDemand (run notebooks)](https://ondemand.cluster.france-bioinformatique.fr) ·
[scanpy](https://scanpy.readthedocs.io) ·
[squidpy](https://squidpy.readthedocs.io) · [spatialdata](https://spatialdata.scverse.org)

## 0. One-time access

- **Cluster SSH key** — generate your own on the
  [cluster manager portal](https://my.cluster.france-bioinformatique.fr/manager2/project):
  create a key, download the **private rsa key**, and save it to `~/.ssh/` (`chmod 600`).
  You'll need it for `ssh`, Claude Code, and VS Code Remote-SSH from your laptop.
- **GitHub CLI**, then log in:
  ```bash
  curl -sS https://webi.sh/gh | sh      # installs gh, no sudo
  gh auth login                          # GitHub.com -> HTTPS -> web browser
  ```
- **Fork this repo** to your own GitHub account (top-right on GitHub) — you'll push your
  own analysis there.

## 1. Get the code (in your cluster home)

```bash
mkdir -p ~/github && cd ~/github
gh repo clone <your-username>/cajal-project15-spatial-brain
cd cajal-project15-spatial-brain
```

## 2. Set up — one fast command (nothing to build)

```bash
bash scripts/cluster_setup.sh
```

This registers the **`Spatial Brain (SIF)`** Jupyter kernel and links the shared Baysor binary —
that's it, it takes **seconds**. There's no environment to build: the whole scientific stack
(scanpy, squidpy, spatialdata, sopa, cellpose, proseg, cellmapper, …) is pre-packed into **one
shared container file** on the project filesystem, and this kernel just points at it. Every
notebook (Levels 0–3) runs on it. See [`scripts/sif/README.md`](scripts/sif/README.md) for how the
container is built.

### Need an extra Python package?

The container is read-only and shared, so don't try to rebuild it — add packages **just for
yourself**:

```bash
bash scripts/sif_pip.sh <package> [<package> ...]     # e.g. harmonypy pertpy
```

This installs into your personal user-site (`~/.local`), which the `Spatial Brain (SIF)` kernel
**already sees** — so your packages show up in notebooks with no kernel or config changes (restart
the kernel afterwards to pick them up). It builds nothing and never touches the project filesystem.
The container is already very complete, so most packages just reuse what's there; steer clear of
ones that re-pull a whole compiled stack (`jax`, `tensorflow`), which are large and rarely needed.
`bash scripts/sif_pip.sh list` shows what you've added.

## 3. Run your analysis — Open OnDemand (recommended)

Everything runs in your browser, on a compute node — no SSH key or tunnel needed.
[OnDemand](https://ondemand.cluster.france-bioinformatique.fr) → **Interactive Apps**:

- **JupyterLab** — for notebooks; once the session starts, select the
  **`Spatial Brain (SIF)`** kernel. It loads the environment from a single shared
  container file, so it starts in seconds.
- **Visual Studio Code** — a full IDE in the browser.

Request resources (account `tp_2630_ubordeaux_neuromics_184418`, partition `fast`, a few
CPUs / 16 GB) and launch.

> Don't run heavy work on the login node.

### Local VS Code (Remote-SSH) — optional

Prefer your own editor? You can drive the cluster from a local **VS Code** so that editing,
terminals, and the Jupyter/Claude Code extensions all run on a **compute node** (never the
login node). One command on the cluster sets it up:

```bash
bash scripts/setup_vscode_remote.sh
```

It installs two small helpers into `~/bin` and prints a ready-to-paste block for your
laptop's `~/.ssh/config`. Assuming you already `ssh` to the cluster (§0 key + a login host),
the only new laptop change is one host, **`cajal-cpu`** — your **compute node**, resolved
dynamically to whatever Slurm job you have running (it prefers a job named `vscode*`). No
hardcoded node names. (If your existing login host isn't named `cajal`, change the one
`ssh cajal` in its `ProxyCommand` to match — the script's output explains this.) You'll also
install the VS Code **Remote - SSH** extension.

Then, each session: start an allocation and point VS Code at `cajal-cpu`:

```bash
# start a compute allocation (8h, adjust as needed)
ssh cajal "sbatch -J vscode -p fast -A tp_2630_ubordeaux_neuromics_184418 \
  -c 4 --mem=16G -t 08:00:00 --wrap='sleep infinity'"
```

In VS Code (with the **Remote - SSH** extension): `F1` → **Remote-SSH: Connect to Host…** →
**`cajal-cpu`**. You land on your job's node; open your repo and work as usual. When the
allocation ends, start a new one and reconnect — `cajal-cpu` follows it automatically.
The script prints the full step-by-step; see [`scripts/setup_vscode_remote.sh`](scripts/setup_vscode_remote.sh).

**Kernel won't start** (`OSError: [Errno 30] Read-only file system: '/run/user'`)? Over
Remote-SSH, VS Code hands the kernel a connection-file path under `/run/user`, which isn't
visible inside the shared container. The `Spatial Brain (SIF)` kernelspec installed by
[`scripts/cluster_setup.sh`](scripts/cluster_setup.sh) handles this (it binds that directory
into the container). If you hit the error, (re-)run `bash scripts/cluster_setup.sh` to refresh
the kernelspec, then restart the kernel.

**Just need SSH for editing and git?** Connect to `cajal` with your key from §0, and run
notebooks / heavy compute via OnDemand or Slurm.

## 4. Daily workflow

- Course notebooks live in `analysis/levelN/`, paired as `NN_slug_student.ipynb` (your working
  copy to fill in) and `NN_slug_solution.ipynb` (the executed reference). Add any notebooks of
  your own alongside them with a short, descriptive name.
- Notebooks are committed **with** their outputs — so executed solution notebooks stay readable.
- Commit & push to **your fork**:
  ```bash
  git add -A && git commit -m "..." && git push
  ```
- Need a package the container doesn't have? Add it just for yourself with
  `bash scripts/sif_pip.sh <pkg>` — it installs into your `~/.local`, which the SIF kernel
  already sees (restart the kernel afterwards). See [§2](#need-an-extra-python-package).

## 5. Data

**Staged once, read-only, shared.** The large inputs are staged for the whole course under

```
/shared/projects/tp_2630_ubordeaux_neuromics_184418/projects/C15/data/
```

Read from there, but **never write to it and never copy it into your repo** — several people run in
parallel off the same files. The notebooks already point at this location in their setup cells; the
main inputs are:

| Path (under the data root above) | Level | What it is |
|---|---|---|
| `wang2025_merfish/processed/UCSF2018-003-MFG_baseline.zarr` | L1 | one imaged tissue section (stains + transcripts + vendor cells) to segment |
| `wang2025_merfish/processed/wang2025_merfish_cells_student.h5ad` | L2 | the spatial cell cohort (reference labels stripped — you rebuild them) |
| `wang2025_multiome/processed/wang2025_multiome_rna.h5ad` | L2/L3 | the single-cell RNA reference atlas |
| `wang2025_multiome/processed/wang2025_multiome_atac.h5ad` | L3 | the matched ATAC modality (16 GB — open `backed="r"` and subset before loading) |

*(A couple more files unlock at the Level 2 reveal; the notebooks introduce them where relevant.)*

**Your outputs go in your repo.** Anything you create — processed objects, figures — goes in the
repo's git-ignored `data/` and `figures/`, addressed through the path helper so you never hard-code
paths:

```python
from spatialbrain import FilePaths

FilePaths.DATA                                     # -> <repo>/data
FilePaths.FIGURES                                  # -> <repo>/figures
FilePaths.dataset("wang2025_merfish").processed    # your per-dataset output folder (created on demand)
```

`FilePaths` resolves the repo root at runtime from your working directory, so it works whether you
run under the SIF kernel or a local checkout. To point outputs elsewhere, set the
`SPATIALBRAIN_ROOT` environment variable.

## 6. Compute

This is a **CPU-only** course — there is no GPU partition. Everything is designed to run on CPU:
segmentation parallelises across cores via Sopa, and label transfer uses CPU k-NN. Request a few
CPUs and ~16–32 GB via OnDemand or Slurm; no `gpu` environment is needed or provided.

## Reference

- **Helper package:** `src/spatialbrain/` — `FilePaths` for project data paths.
- **Container:** the whole stack is pre-packed into one shared Apptainer image; see
  [`scripts/sif/README.md`](scripts/sif/README.md) for how it's built. You don't need
  [pixi](https://pixi.sh) to run the course — the `Spatial Brain (SIF)` kernel is self-contained.
- **Repo contributors** (not needed to run the course): `scripts/build_pixi_env.sh` builds the
  [pixi](https://pixi.sh) dev environment (`pixi.toml` + `pixi.lock`) and installs the
  [pre-commit](https://pre-commit.com/) / [ruff](https://docs.astral.sh/ruff/) git hooks.
- **Science:** [scanpy](https://scanpy.readthedocs.io) · [squidpy](https://squidpy.readthedocs.io) ·
  [spatialdata](https://spatialdata.scverse.org) · [single-cell best practices](https://www.sc-best-practices.org/).
