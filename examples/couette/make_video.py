#!/usr/bin/env python3
"""Render videos from real OpenFOAM Couette run data (ffmpeg + matplotlib).

Two videos, both revolving the 1D radial profile from the wedge-sector
mesh into a full annulus (the flow is axisymmetric, so the profile is
the same at every angle):

1. couette-gamma10.mp4 — spin-up at gamma = 10 1/s, from the transient
   pimpleFoam run (runs/gamma_10_spinup/, snapshots every 0.05 s).
   Runs the transient case first if it is not there yet.
2. couette-sweep.mp4 — steady state at each sweep point, from the
   simpleFoam runs (runs/gamma_*/ final U field).

Colour is the azimuthal velocity u_theta. Each frame is scaled to its
own maximum (the wall speed changes 1000x across the sweep, so a
single colour scale would leave the low-rate frames black); the wall
speed is printed in the title of every frame.

Usage: python3 make_video.py [--runs runs] [--gamma-spinup 10]
Writes couette-gamma10.mp4 and couette-sweep.mp4 in examples/couette/.
"""
import argparse
import math
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

HERE = Path(__file__).parent
FRAME_DIR = HERE / "frames"


def load_case(path=HERE / "case.yaml"):
    with open(path) as fh:
        return yaml.safe_load(fh)


def read_profile(u_path, Ri, Ro, n_cells):
    """Read an OpenFOAM U field -> (r_centres, u_theta, u_radial)."""
    text = Path(u_path).read_text()
    m = re.search(r"internalField\s+nonuniform List<vector>\s*\n(\d+)\n\((.*?)\)\s*;",
                  text, re.S)
    if m:
        vals = [tuple(map(float, v.split()))
                for v in re.findall(r"\(([^)]*)\)", m.group(2))]
    else:
        # initial condition: internalField uniform (0 0 0);
        mu = re.search(r"internalField\s+uniform\s+\(([^)]*)\)\s*;", text)
        if not mu:
            raise ValueError(f"no vector internalField in {u_path}")
        vals = [tuple(map(float, mu.group(1).split()))] * n_cells
    if len(vals) != n_cells:
        raise ValueError(f"{u_path}: expected {n_cells} cells, got {len(vals)}")
    dx = (Ro - Ri) / n_cells
    r = np.array([Ri + (i + 0.5) * dx for i in range(n_cells)])
    # cell centres lie in the z=0 plane: azimuthal velocity is U_z,
    # radial velocity is U_y, axial (U_x) ~ 0.
    u_theta = np.array([v[2] for v in vals])
    u_radial = np.array([v[1] for v in vals])
    return r, u_theta, u_radial


def render_frame(r, u_theta, Ri, Ro, title, out_png, vmax=None):
    """Revolve a 1D profile into a full annulus and save a PNG frame."""
    n_theta = 180
    # radial edges: wall radii + cell-centre midpoints
    edges = np.empty(len(r) + 1)
    edges[0] = Ri
    edges[-1] = Ro
    edges[1:-1] = 0.5 * (r[:-1] + r[1:])
    theta = np.linspace(0, 2 * math.pi, n_theta + 1)
    # values on (r_edge, theta) grid: profile value per radial band,
    # one value per theta cell (n_theta cells between n_theta+1 edges)
    vals = np.tile(u_theta[:, None], (1, n_theta))
    R, TH = np.meshgrid(edges, theta, indexing="ij")
    X = R * np.cos(TH)
    Y = R * np.sin(TH)
    fig, ax = plt.subplots(figsize=(5, 5))
    vmax = vmax or float(np.max(np.abs(u_theta))) or 1.0
    mesh = ax.pcolormesh(X, Y, vals, shading="auto", cmap="viridis",
                         vmin=0.0, vmax=vmax)
    # bob: white disc with outline; cup: outline
    ax.add_patch(plt.Circle((0, 0), Ri, color="white", ec="black", lw=1.5, zorder=3))
    ax.add_patch(plt.Circle((0, 0), Ro, fill=False, ec="black", lw=1.5, zorder=3))
    ax.set_aspect("equal")
    ax.set_xlim(-Ro * 1.05, Ro * 1.05)
    ax.set_ylim(-Ro * 1.05, Ro * 1.05)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=11)
    cb = fig.colorbar(mesh, ax=ax, shrink=0.8)
    cb.set_label("u_theta (m/s)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=100)
    plt.close(fig)


def run_ffmpeg(frames, out_mp4, fps=4):
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i",
           str(frames / "frame_%03d.png"), "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "-vf", "scale=500:500", str(out_mp4)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        print(p.stderr[-2000:])
        raise RuntimeError(f"ffmpeg failed for {out_mp4}")
    print(f"wrote {out_mp4} ({out_mp4.stat().st_size/1e6:.2f} MB)")


def spinup_video(case, runs, gamma):
    """Transient pimpleFoam spin-up at one gamma; run it if not present."""
    g = case["geometry"]
    Ri, Ro, n_cells = g["R_i"], g["R_o"], case["mesh"]["cells_across_gap"]
    spin_dir = runs / f"gamma_{gamma:g}_spinup"
    if not (spin_dir / "1" / "U").exists():
        print(f"spin-up run not found at {spin_dir} — running pimpleFoam ...")
        r = subprocess.run([sys.executable, str(HERE / "couette_build.py"),
                            "--gamma", str(gamma), "--out", str(spin_dir),
                            "--transient"], capture_output=True, text=True)
        print("  " + r.stdout.strip())
        if r.returncode:
            print(r.stderr); raise RuntimeError("couette_build --transient failed")
        root = Path(case["run"].get("openfoam_root") or
                    "/usr/lib/openfoam/openfoam2412")
        prefix = f"source {root}/etc/bashrc && cd {spin_dir} && "
        for cmd, log in (("blockMesh", "blockMesh.log"),
                         ("pimpleFoam", "pimpleFoam.log")):
            with open(spin_dir / log, "w") as lf:
                p = subprocess.run(["bash", "-c", prefix + cmd],
                                   stdout=lf, stderr=subprocess.STDOUT)
            if p.returncode:
                raise RuntimeError(f"{cmd} failed — see {spin_dir / log}")
        print("  pimpleFoam spin-up done")
    # snapshots: time dirs 0, 0.05, ..., 1.0 (use the real dir names)
    time_dirs = sorted((d for d in spin_dir.iterdir()
                        if d.is_dir() and re.fullmatch(r"\d+(\.\d+)?", d.name)
                        and (d / "U").exists()),
                       key=lambda d: float(d.name))
    FRAME_DIR.mkdir(exist_ok=True)
    for i, d in enumerate(time_dirs):
        t = float(d.name)
        r, u_theta, _ = read_profile(d / "U", Ri, Ro, n_cells)
        u_wall = float(np.max(u_theta)) if t > 0 else 0.0
        render_frame(r, u_theta, Ri, Ro,
                     f"Couette spin-up, gamma = {gamma} 1/s, t = {t:.2f} s\n"
                     f"u_theta max = {u_wall:.4f} m/s",
                     FRAME_DIR / f"frame_{i+1:03d}.png")
    run_ffmpeg(FRAME_DIR, HERE / "couette-gamma10.mp4", fps=4)
    for f in FRAME_DIR.glob("frame_*.png"):
        f.unlink()


def sweep_video(case, runs):
    """One frame per steady sweep point, from the final U field."""
    g, s = case["geometry"], case["sweep"]
    Ri, Ro, n_cells = g["R_i"], g["R_o"], case["mesh"]["cells_across_gap"]
    FRAME_DIR.mkdir(exist_ok=True)
    i = 0
    for gamma in s["shear_rate_1_s"]:
        run_dir = runs / f"gamma_{gamma}"
        # last numeric time dir (simpleFoam writes 0, 250, 500, ...)
        times = sorted((float(d.name), d) for d in run_dir.iterdir()
                       if d.is_dir() and re.fullmatch(r"\d+", d.name)
                       and (d / "U").exists())
        if not times:
            print(f"no U field in {run_dir} — skipping gamma={gamma}")
            continue
        t, d = times[-1]
        r, u_theta, _ = read_profile(d / "U", Ri, Ro, n_cells)
        i += 1
        render_frame(r, u_theta, Ri, Ro,
                     f"Couette steady state, gamma = {gamma} 1/s\n"
                     f"u_theta max = {float(np.max(u_theta)):.4f} m/s "
                     f"(iteration {int(t)})",
                     FRAME_DIR / f"frame_{i:03d}.png")
    if i == 0:
        print("no steady profiles found — run the sweep first")
        return
    run_ffmpeg(FRAME_DIR, HERE / "couette-sweep.mp4", fps=1)
    for f in FRAME_DIR.glob("frame_*.png"):
        f.unlink()
    FRAME_DIR.rmdir()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(HERE / "runs"))
    ap.add_argument("--gamma-spinup", type=float, default=10.0)
    args = ap.parse_args()
    case = load_case()
    spinup_video(case, Path(args.runs), args.gamma_spinup)
    sweep_video(case, Path(args.runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
