# CLAUDE.md — Project 15

Single-cell / spatial analysis on the IFB Core Cluster, managed with pixi.

## Cluster invariants
- Shared project folder (large quota): `/shared/projects/tp_2630_ubordeaux_neuromics_184418`.
- Home (`~`) has a ~100,000-file (inode) quota — too small for a scientific env. The pixi
  environment, caches, and raw data therefore live on the **project filesystem**, not home
  (configured by `cluster_setup.sh`).
- Raw data is staged once on the project filesystem (shared, not duplicated per person);
  your own processed outputs go in the repo's `data/`.
- Run on compute nodes, never the login node — via Open OnDemand apps or Slurm (`srun`/`sbatch`).

## Environment
- pixi: deps in `pixi.toml`, pinned in `pixi.lock`. Add packages PyPI-first
  (`pixi add --pypi <pkg>`; conda only for hard-to-build compiled deps), then commit both files.

## Docs
- IFB cluster: https://doc.cluster.france-bioinformatique.fr/  ·  Project setup: README.md
