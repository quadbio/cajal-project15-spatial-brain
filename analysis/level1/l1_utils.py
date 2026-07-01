"""Level-1 helpers: CPU-parallel Sopa segmentation + the label-free purity metric.

The course has no GPU, and CellPose's per-patch work is largely single-threaded, so
the fast way to segment on CPU is Sopa's own pattern: split the image into patches and
run one **process per patch** in parallel (this is what Sopa's Snakemake pipeline does
across cluster jobs). Here we do the same inside a notebook with a thread pool that
launches ``sopa segmentation ... --patch-index`` subprocesses (``OMP_NUM_THREADS=1``
each), so the single-threaded work runs truly in parallel across the session's cores.

Students call :func:`run_cellpose`, :func:`run_baysor`, :func:`run_proseg`; the
segmentation is written into the (writable, home-local) crop's ``.zarr`` store.
"""

from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import spatialdata as sd

__all__ = [
    "run_cellpose",
    "run_baysor",
    "run_proseg",
    "default_n_workers",
    "gene_on_calls",
    "negative_marker_purity",
    "proportion_assigned_reads",
    "shapes_area_um2",
    "mutually_exclusive_markers_from_reference",
]


def _sopa() -> str:
    """Absolute path to the ``sopa`` CLI in the active env.

    Jupyter kernels don't always put the env's ``bin`` on ``PATH``.
    """
    exe = Path(sys.executable).parent / "sopa"
    return str(exe) if exe.exists() else "sopa"


def default_n_workers() -> int:
    """Cores to parallelise over — the Slurm/OnDemand allocation if known, else 8."""
    return int(os.environ.get("SLURM_CPUS_PER_TASK", 8))


def _run(cmd: list[str], single_threaded: bool = False) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if single_threaded:
        env.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    return subprocess.run([_sopa(), *cmd], env=env, capture_output=True, text=True)


def _n_patches(zarr_path: str, key: str) -> int:
    return len(sd.read_zarr(zarr_path)[key])


def _parallel_over_patches(zarr_path: str, seg_cmd, n: int, n_workers: int) -> list[int]:
    """Run ``seg_cmd(i)`` (a subprocess) for patch ``i`` across ``n_workers`` cores."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as ex:
        return list(ex.map(seg_cmd, range(n)))


def run_cellpose(
    zarr_path: str,
    *,
    diameter: int = 110,
    channels: tuple[str, ...] = ("PolyT", "DAPI"),
    patch_width: int = 1500,
    patch_overlap: int = 120,
    flow_threshold: float = 2,
    cellprob_threshold: float = -6,
    min_area: int = 2000,
    n_workers: int | None = None,
) -> int:
    """CellPose (v3) on the image, process-parallel across patches. Returns #cells.

    Segments **whole cells** using two channels — cytoplasm (poly(T)) then nucleus (DAPI).
    ``diameter`` is in **pixels**; at 0.108 µm/px, ``diameter=110`` ≈ 12 µm, matching real
    cell size and Baysor's ``scale`` (6.25 µm radius = 12.5 µm diameter). Patch width is
    1500 px (not Sopa's cluster-oriented 6000) so there are enough patches to fill the cores.
    """
    n_workers = n_workers or default_n_workers()
    _run(
        [
            "patchify",
            "image",
            zarr_path,
            "--patch-width-pixel",
            str(patch_width),
            "--patch-overlap-pixel",
            str(patch_overlap),
        ]
    ).check_returncode()
    n = _n_patches(zarr_path, "image_patches")

    chan_args: list[str] = []
    for c in channels:
        chan_args += ["--channels", c]

    def seg(i: int) -> int:
        return _run(
            [
                "segmentation",
                "cellpose",
                zarr_path,
                "--patch-index",
                str(i),
                "--diameter",
                str(diameter),
                *chan_args,
                "--flow-threshold",
                str(flow_threshold),
                "--cellprob-threshold",
                str(cellprob_threshold),
                "--min-area",
                str(min_area),
            ],
            single_threaded=True,
        ).returncode

    fails = [i for i, rc in enumerate(_parallel_over_patches(zarr_path, seg, n, n_workers)) if rc]
    if fails:
        raise RuntimeError(f"cellpose failed on {len(fails)} patches: {fails[:5]}")
    _run(["resolve", "cellpose", zarr_path]).check_returncode()
    return len(sd.read_zarr(zarr_path)["cellpose_boundaries"])


# Baysor config from Sopa's workflow/config/merscope/baysor_cellpose.yaml
BAYSOR_CONFIG = {
    "data": {
        "force_2d": True,
        "min_molecules_per_cell": 10,
        "x": "x",
        "y": "y",
        "z": "z",
        "min_molecules_per_gene": 0,
        "min_molecules_per_segment": 3,
        "confidence_nn_id": 6,
    },
    "segmentation": {
        "scale": 6.25,
        "scale_std": "25%",
        "prior_segmentation_confidence": 0.5,
        "estimate_scale_from_centers": False,
        "n_clusters": 4,
        "iters": 500,
        "n_cells_init": 0,
        "nuclei_genes": "",
        "cyto_genes": "",
    },
}


def run_baysor(
    zarr_path: str,
    *,
    prior_shapes_key: str = "cellpose_boundaries",
    patch_width_microns: float = 1000,
    min_area: float = 20,
    config: dict | None = None,
) -> int:
    """Baysor refining the CellPose prior. Returns #cells.

    (Baysor is internally multithreaded, so a single transcript patch already uses the cores.)
    """
    import sopa

    s = sd.read_zarr(zarr_path)
    sopa.make_transcript_patches(s, patch_width=patch_width_microns, prior_shapes_key=prior_shapes_key)
    sopa.segmentation.baysor(s, min_area=min_area, config=config or BAYSOR_CONFIG)
    return len(sd.read_zarr(zarr_path)["baysor_boundaries"])


def run_proseg(zarr_path: str, *, prior_shapes_key: str = "cellpose_boundaries") -> int:
    """Proseg refining the same CellPose prior, on the whole crop (one patch). Returns #cells."""
    import sopa

    s = sd.read_zarr(zarr_path)
    sopa.make_transcript_patches(s, patch_width=None, prior_shapes_key=prior_shapes_key)
    sopa.segmentation.proseg(s)
    return len(sd.read_zarr(zarr_path)["proseg_boundaries"])


def shapes_area_um2(sdata, shapes_key: str, points_key: str | None = None) -> np.ndarray:
    """Cell areas in **micron^2** for one segmentation, comparable across methods.

    Different methods store polygons in different intrinsic units — CellPose in image
    **pixels**, transcript-based methods in **microns** — so a raw ``.area`` is not
    comparable. We rescale each element's area by its intrinsic->pixel scale relative to
    the microns->pixel scale of the transcripts.
    """
    from spatialdata.transformations import get_transformation

    if points_key is None:
        points_key = next(k for k in sdata.points if "patch" not in k.lower())
    px_per_um = abs(
        float(
            get_transformation(sdata[points_key], "global").to_affine_matrix(
                input_axes=("x", "y"), output_axes=("x", "y")
            )[0, 0]
        )
    )
    intrinsic_to_px = abs(
        float(
            get_transformation(sdata[shapes_key], "global").to_affine_matrix(
                input_axes=("x", "y"), output_axes=("x", "y")
            )[0, 0]
        )
    )
    micron_per_intrinsic = intrinsic_to_px / px_per_um
    return sdata[shapes_key].geometry.area.to_numpy() * micron_per_intrinsic**2


# --------------------------------------------------------------------------------------
# Label-free segmentation quality: negative-marker purity
#
# Idea (Salas et al.; ResolVI): take pairs of marker genes from *mutually exclusive* cell
# lineages (e.g. a neuron marker and a glia marker). A correctly segmented cell should
# almost never be "on" for both — co-expression means transcripts leaked across a cell
# boundary (over-merging / mis-assignment). Purity = 1 - mean cross-lineage double-positive
# rate. It needs no cell-type labels on the spatial side, so it works pre-annotation.
# --------------------------------------------------------------------------------------


def gene_on_calls(counts: np.ndarray, min_positive: int = 20) -> np.ndarray:
    """Boolean "gene is ON" per cell, via a per-gene 2-component Gaussian mixture.

    Fits on ``log1p`` counts (signal vs background) instead of the naive ``count > 0``;
    falls back to ``count > 0`` for genes with too few positive cells to fit a mixture.
    """
    from sklearn.mixture import GaussianMixture

    counts = np.asarray(counts, dtype=float).ravel()
    if (counts > 0).sum() < min_positive or counts.max() == 0:
        return counts > 0
    x = np.log1p(counts).reshape(-1, 1)
    gm = GaussianMixture(n_components=2, covariance_type="full", random_state=0, n_init=1).fit(x)
    on_component = int(np.argmax(gm.means_.ravel()))  # higher-mean component = signal
    return gm.predict(x) == on_component


def negative_marker_purity(adata, pairs, layer: str | None = "counts"):
    """Negative-marker purity for one segmentation's cell x gene table.

    Parameters
    ----------
    adata
        Cells x genes AnnData for a single segmentation method.
    pairs
        List of ``(gene_a, gene_b)`` marker pairs from *mutually exclusive* lineages
        (e.g. from :func:`mutually_exclusive_markers_from_reference`). A correctly
        segmented cell should almost never be "on" for both; co-expression = transcript
        leakage. Pairs with a gene absent from ``adata`` are skipped.
    layer
        Layer holding raw counts (default ``"counts"``); ``None`` uses ``adata.X``.

    Returns
    -------
    purity : float
        ``1 - mean(double_positive_rate)`` over the pairs (higher = better).
    per_pair : dict
        ``{(gene_a, gene_b): double_positive_rate}`` for inspection.
    """
    X = adata.X if layer is None else adata.layers[layer]
    X = np.asarray(X.todense()) if hasattr(X, "todense") else np.asarray(X)

    genes = {g for pair in pairs for g in pair if g in adata.var_names}
    on = {g: gene_on_calls(X[:, adata.var_names.get_loc(g)]) for g in genes}

    per_pair: dict[tuple[str, str], float] = {}
    for ga, gb in pairs:
        if ga not in on or gb not in on:
            continue
        either = on[ga] | on[gb]
        if either.sum() == 0:
            continue
        per_pair[(ga, gb)] = float((on[ga] & on[gb]).sum() / either.sum())

    purity = 1.0 - float(np.mean(list(per_pair.values()))) if per_pair else float("nan")
    return purity, per_pair


def proportion_assigned_reads(assigned_total: float, n_transcripts_total: int) -> float:
    """Benchmark x-axis: fraction of all decoded transcripts assigned to a cell."""
    return float(assigned_total) / float(n_transcripts_total)


# --------------------------------------------------------------------------------------
# Deriving mutually-exclusive marker pairs from the (annotated) reference
#
# Reproducible replacement for hand-picked markers. Uses ONLY the reference's cell-type
# labels (never spatial labels): per lineage, pick genes that are specifically expressed
# there (high in-lineage fraction, low elsewhere), then keep only cross-lineage pairs that
# are ~never co-expressed in the reference single cells (Salas/ResolVI "negative marker"
# logic). The resulting pairs feed `negative_marker_purity` on the label-free spatial data.
# --------------------------------------------------------------------------------------


def mutually_exclusive_markers_from_reference(
    ref_adata,
    class_key: str = "class",
    lineages=("Neuron", "Glia", "Vascular", "Immune"),
    n_per_lineage: int = 8,
    min_frac_in: float = 0.25,
    max_frac_out: float = 0.05,
    max_ref_coexpr: float = 0.02,
):
    """Derive mutually-exclusive lineage markers + verified cross-lineage pairs.

    Parameters
    ----------
    ref_adata
        Reference cells x panel-genes AnnData with lineage labels in ``obs[class_key]``.
        ``X`` may be counts or log-normalised (only ``X > 0`` is used).
    lineages
        Which ``class_key`` values to use (others, e.g. progenitors/unknown, are skipped).
    n_per_lineage
        Max specific markers kept per lineage.
    min_frac_in / max_frac_out
        A gene marks a lineage if expressed in >= ``min_frac_in`` of its cells and
        <= ``max_frac_out`` of all other lineages' cells.
    max_ref_coexpr
        Keep a cross-lineage pair only if its reference co-detection
        ``P(both>0)/P(either>0)`` is <= this (i.e. genuinely mutually exclusive).

    Returns
    -------
    lineage_markers : dict[str, list[str]]
    pairs : list[tuple[str, str]]   # reference-verified mutually-exclusive pairs
    """
    X = ref_adata.X
    expressed = (X.toarray() if hasattr(X, "toarray") else np.asarray(X)) > 0
    labels = ref_adata.obs[class_key].to_numpy().astype(str)
    genes = list(ref_adata.var_names)
    gidx = {g: i for i, g in enumerate(genes)}

    lineage_markers: dict[str, list[str]] = {}
    for lin in lineages:
        in_mask = labels == lin
        if in_mask.sum() == 0:
            continue
        frac_in = expressed[in_mask].mean(0)
        frac_out = expressed[~in_mask].mean(0)
        spec = frac_in - frac_out
        ok = (frac_in >= min_frac_in) & (frac_out <= max_frac_out)
        order = np.argsort(spec)[::-1]
        lineage_markers[lin] = [genes[i] for i in order if ok[i]][:n_per_lineage]

    pairs: list[tuple[str, str]] = []
    lins = list(lineage_markers)
    for i, la in enumerate(lins):
        for lb in lins[i + 1 :]:
            for ga in lineage_markers[la]:
                for gb in lineage_markers[lb]:
                    ea, eb = expressed[:, gidx[ga]], expressed[:, gidx[gb]]
                    either = (ea | eb).sum()
                    coexpr = (ea & eb).sum() / either if either else 0.0
                    if coexpr <= max_ref_coexpr:
                        pairs.append((ga, gb))
    return lineage_markers, pairs
