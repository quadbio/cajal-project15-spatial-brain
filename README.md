# Project 15 — Mapping the Spatial Cellular Architecture of the Brain

**CAJAL Neuromics 2026 (Bordeaux).** Reconstruct the spatial cellular architecture of the
brain from high-plex, image-based spatial transcriptomics: QC → cell segmentation →
cell-type annotation by label transfer from a scRNA-seq reference atlas → spatial niches →
region-specific cell–cell communication. Notebook-first, [pixi](https://pixi.sh)-managed,
runs on the IFB Core Cluster.

**Links:** [IFB docs](https://doc.cluster.france-bioinformatique.fr/) ·
[OnDemand (run notebooks)](https://ondemand.cluster.france-bioinformatique.fr) ·
[pixi](https://pixi.sh) · [scanpy](https://scanpy.readthedocs.io) ·
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

## 2. Set up the environment — one command

```bash
bash cluster_setup.sh
```

Installs pixi (if needed) and builds the project environment. **Why a script?** The cluster
home directory has a 100,000-*file* quota that a scientific environment would blow, so the
script puts the environment and caches on the large **project filesystem**, then registers a
Jupyter kernel and the git hooks. A few minutes the first time.

> **Env model:** each student gets their **own** environment (so you can `pixi add` and
> experiment freely), but the package **cache is shared** on the project filesystem — packages
> download once and each env hardlinks them, so an env costs only ~17k files instead of ~100k.
> This only works because the cache stays on the project filesystem, which `cluster_setup.sh`
> handles — don't override it to point at home.

## 3. Run your analysis — Open OnDemand (recommended)

Everything runs in your browser, on a compute node — no SSH key or tunnel needed.
[OnDemand](https://ondemand.cluster.france-bioinformatique.fr) → **Interactive Apps**:

- **JupyterLab** — for notebooks; select the project's kernel once the session starts.
- **Visual Studio Code** — a full IDE in the browser.

Request resources (account `tp_2630_ubordeaux_neuromics_184418`, partition `fast`, a few
CPUs / 16 GB) and launch.

> Don't run heavy work on the login node.

**Using Claude Code or a desktop editor?** Connect to the cluster over SSH (with your key
from §0) for editing and git, and run notebooks / heavy compute via OnDemand or Slurm.

## 4. Daily workflow

- Notebooks live in `analysis/`, named `INITIALS-YYYY-MM-DD_description.ipynb`.
- Notebooks are committed **with** their outputs — so executed solution notebooks stay readable.
- Commit & push to **your fork**:
  ```bash
  git add -A && git commit -m "..." && git push
  ```
- Add a package **PyPI-first**: `pixi add --pypi <pkg>` (use conda only for hard-to-build
  compiled deps), then commit `pixi.toml` + `pixi.lock` so everyone stays in sync.

## 5. Data

Raw data is staged once in a shared location (not copied per student); your repo's `data/`
holds smaller processed outputs. Paths are exposed via `from spatialbrain import FilePaths`.
*(Specifics to be added.)*

## 6. Compute

This is a **CPU-only** course — there is no GPU partition. Everything is designed to run on CPU:
segmentation parallelises across cores via Sopa, and label transfer uses CPU k-NN. Request a few
CPUs and ~16–32 GB via OnDemand or Slurm; no `gpu` environment is needed or provided.

## Reference

- **Environment:** `pixi.toml` (+ `pixi.lock` for exact, reproducible versions) —
  [pixi docs](https://pixi.sh/latest/).
- **Helper package:** `src/spatialbrain/` — `FilePaths` for project data paths.
- **Code quality:** [pre-commit](https://pre-commit.com/) hooks (set up by `cluster_setup.sh`) —
  [ruff](https://docs.astral.sh/ruff/) lint/format.
- **Science:** [scanpy](https://scanpy.readthedocs.io) · [squidpy](https://squidpy.readthedocs.io) ·
  [spatialdata](https://spatialdata.scverse.org) · [single-cell best practices](https://www.sc-best-practices.org/).
