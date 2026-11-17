#!/usr/bin/env python3
"""Run the OpenFOAM Couette sweep: one simpleFoam run per shear rate.

Dry-run by default: prints the plan (gamma, Omega, torque scale) and
runs nothing. With --run it builds each run directory, runs blockMesh
+ simpleFoam, and writes torque.csv + run_info.json per point.

Each run directory is a full copy of examples/couette-tc/case/ with
__OMEGA__ substituted in 0/U. Torque comes from the forces
functionObject: postProcessing/forces/0/moment.dat (v2412 writes
force.dat and moment.dat, not forces.dat). The moment's X component
is the sector torque about the cylinder axis; the full-cylinder
torque is |M_x| * torque_scale (5400 for the 4 deg wedge, 1 mm slice).

Convergence: simpleFoam stops early via residualControl (1e-8) when
converged; a run that reaches endTime without converging is flagged
in run_info.json and in the summary — diagnose before trusting it.

Usage:
    python3 couette_sweep.py              # dry run: print the plan
    python3 couette_sweep.py --run        # run the whole sweep
    python3 couette_sweep.py --run --gamma 10   # one point only
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).parent
RUNS = HERE / "runs"


def load_case(path=HERE / "case.yaml"):
    with open(path) as fh:
        return yaml.safe_load(fh)


def omega_for_gamma(gamma, Ri, Ro):
    return gamma * (Ro * Ro - Ri * Ri) / (2.0 * Ro * Ro)


def openfoam_prefix(case):
    root = Path(case["run"].get("openfoam_root") or
                "/usr/lib/openfoam/openfoam2412")
    bashrc = root / "etc" / "bashrc"
    if not bashrc.exists():
        print(f"ERROR: OpenFOAM bashrc not found at {bashrc} — "
              "install it (scripts/install-openfoam.sh) or fix case.yaml")
        sys.exit(1)
    return f"source {bashrc} && "


def run_cmd(prefix, workdir, cmd, logfile):
    """Run `cmd` in workdir with the OpenFOAM environment sourced."""
    full = prefix + f"cd {workdir} && {cmd}"
    with open(logfile, "w") as lf:
        p = subprocess.run(["bash", "-c", full], stdout=lf,
                           stderr=subprocess.STDOUT)
    return p.returncode


def last_uz_residual(log_path):
    """Last 'Solving for Uz, Initial residual' in a simpleFoam log."""
    last = None
    pat = re.compile(r"Solving for Uz, Initial residual = ([\d.e+-]+)")
    for line in Path(log_path).read_text(errors="replace").splitlines():
        m = pat.search(line)
        if m:
            last = float(m.group(1))
    return last


def last_time(log_path):
    last = None
    pat = re.compile(r"^Time = (\d+)")
    for line in Path(log_path).read_text(errors="replace").splitlines():
        m = pat.match(line)
        if m:
            last = int(m.group(1))
    return last


def parse_moment_dat(path, torque_scale):
    """moment.dat -> list of (iteration, sector_moment, full_torque)."""
    rows = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        it = float(parts[0])
        mx = float(parts[1])  # total_x: moment about the cylinder axis
        rows.append((it, mx, abs(mx) * torque_scale))
    return rows


def run_point(case, gamma, prefix, force=False):
    g = case["geometry"]
    Ri, Ro, L = g["R_i"], g["R_o"], g["L"]
    scale = case["mesh"]["torque_scale"]
    end_time = case["solver"]["end_time_iterations"]
    omega = omega_for_gamma(gamma, Ri, Ro)
    out = RUNS / f"gamma_{gamma}"
    print(f"\ngamma={gamma} 1/s  Omega={omega:.6g} rad/s  -> {out}")

    # build
    r = subprocess.run([sys.executable, str(HERE / "couette_build.py"),
                        "--gamma", str(gamma), "--out", str(out)],
                       capture_output=True, text=True)
    print("  " + r.stdout.strip())
    if r.returncode:
        print("  BUILD FAILED:\n" + r.stderr)
        return False

    # mesh
    rc = run_cmd(prefix, out, "blockMesh", out / "blockMesh.log")
    if rc:
        print("  blockMesh FAILED — see blockMesh.log")
        return False
    rc = run_cmd(prefix, out, "checkMesh", out / "checkMesh.log")
    mesh_ok = "Mesh OK." in Path(out / "checkMesh.log").read_text(errors="replace")
    print(f"  blockMesh OK, checkMesh {'OK' if mesh_ok else 'PROBLEM — see checkMesh.log'}")
    if not mesh_ok:
        return False

    # solve
    t0 = time.time()
    rc = run_cmd(prefix, out, "simpleFoam", out / "simpleFoam.log")
    wall = time.time() - t0
    if rc:
        print("  simpleFoam FAILED — see simpleFoam.log tail:")
        print("  " + "\n  ".join(
            Path(out / "simpleFoam.log").read_text(errors="replace").splitlines()[-5:]))
        return False
    lt = last_time(out / "simpleFoam.log")
    uz_res = last_uz_residual(out / "simpleFoam.log")
    converged = uz_res is not None and uz_res < 1e-7
    print(f"  simpleFoam done in {wall:.1f} s, last iteration {lt}/{end_time}, "
          f"final Uz residual {uz_res:.2e} — "
          f"{'CONVERGED' if converged else 'NOT CONVERGED (check)'}")

    # torque
    mom = out / "postProcessing" / "forces" / "0" / "moment.dat"
    if not mom.exists():
        print(f"  MISSING {mom} — forces functionObject produced nothing")
        return False
    rows = parse_moment_dat(mom, scale)
    with open(out / "torque.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["iteration", "sector_moment_N_m", "torque_N_m"])
        w.writerows(rows)
    info = {"gamma_1_s": gamma, "omega_rad_s": omega, "L_m": L,
            "torque_scale": scale, "iterations": lt,
            "end_time_iterations": end_time, "converged": converged,
            "final_Uz_residual": uz_res, "wall_time_s": round(wall, 2),
            "n_torque_samples": len(rows),
            "torque_last_N_m": rows[-1][2] if rows else None}
    (out / "run_info.json").write_text(json.dumps(info, indent=2))
    print(f"  torque: last sample {rows[-1][2]:.6e} N.m ({len(rows)} samples)")
    return converged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--gamma", type=float, default=None)
    ap.add_argument("--case", default=str(HERE / "case.yaml"))
    args = ap.parse_args()

    case = load_case(args.case)
    g, s = case["geometry"], case["sweep"]
    gammas = [args.gamma] if args.gamma is not None else s["shear_rate_1_s"]
    print("Couette sweep — OpenFOAM simpleFoam, wedge sector, TC "
          f"sigma_y={case["fluid"]["sigma_y_Pa"]} Pa, gamma_dot_c={case["fluid"]["gamma_dot_c_1_s"]} 1/s, eta_bg={case["fluid"]["eta_bg_Pa_s"]} Pa.s, rho={case["fluid"]["rho_kg_m3"]} kg/m3")
    print(f"Ri={g['R_i']} m, Ro={g['R_o']} m, L={g['L']} m, "
          f"torque scale x{case['mesh']['torque_scale']}")
    for gamma in gammas:
        omega = omega_for_gamma(gamma, g["R_i"], g["R_o"])
        print(f"  gamma={gamma:>6} 1/s  Omega={omega:.6g} rad/s")
    if not args.run:
        print("Dry run only. Pass --run to execute the solver sweep.")
        return 0

    prefix = openfoam_prefix(case)
    RUNS.mkdir(exist_ok=True)
    ok = True
    for gamma in gammas:
        if not run_point(case, gamma, prefix):
            ok = False
    print("\nSweep " + ("complete." if ok else "finished WITH FAILURES — see above."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
