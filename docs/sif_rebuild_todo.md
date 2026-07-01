# Pending env changes for the next SIF rebuild

Running list of changes that are committed in the repo but **not yet baked** into
the live container (`…/containers/marius/spatialbrain.sif`). The SIF is a snapshot
of the pixi env + `src/spatialbrain`, so these only take effect after a rebuild.

**To bake them in:**

```bash
# dependency change? update the pixi env first:
pixi install
# then rebuild + swap in the SIF (~10–20 min; see scripts/sif/README.md):
pixi run build-sif
```

Tick items off (or clear the list) once a rebuild lands them.

## Pending

- [ ] **`FilePaths` runtime repo-root resolution** — `src/spatialbrain/_constants.py`
  ([#9](https://github.com/quadbio/cajal-project15-spatial-brain/pull/9)). The baked
  package still uses the old `_find_root`, so `FilePaths.DATA` points inside the
  read-only container and dataset writes (e.g. `sq.datasets.merfish()`) fail. Needs
  baking before the "Spatial Brain (SIF)" kernel writes to `data/` correctly.

## Last baked

- 2026-07-01 — initial build (scanpy 1.12.1, torch 2.8.0+cpu).
