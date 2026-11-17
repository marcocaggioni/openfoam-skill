#!/usr/bin/env python3
"""Couette post-processing (TC fluid): runs/gamma_*/torque.csv -> flow curve
+ analytic-TC validation.

Input per sweep point: runs/gamma_<value>/torque.csv with columns
    iteration, sector_moment_N_m, torque_N_m
(torque_N_m is the full-cylinder torque: sector moment x 5400.)

TC constitutive law (Marco, Nov 17):
    tau = sigma_y + sigma_y*sqrt(gamma_dot/gamma_dot_c) + eta_bg*gamma_dot
    sigma_y = 70 Pa, gamma_dot_c = 100 1/s, eta_bg = 0.05 Pa.s.

Analytic reference (copied from ~/workspace/tc-analytic.py, the shared
reference implementation — same functions, same bisection):
    tau(r) = T / (2*pi*L*r^2); invert the TC law for gamma_dot(tau)
    (quadratic in sqrt(gamma_dot); gamma_dot = 0 where tau < sigma_y);
    Omega = integral_{Ri}^{R_y} gamma_dot dr/r with
    R_y = min(Ro, sqrt(T/(2*pi*L*sigma_y))); solve for T given Omega
    by bisection. The integral machinery was verified against the known
    Newtonian analytic torque (0.0000% diff).

IMPORTANT: validation is TORQUE vs the analytic TC torque at each
Omega. It is NOT eta_app vs the TC law at the label rate: the label
gamma is the Newtonian inner-wall-rate convention
(Omega = gamma*(Ro^2-Ri^2)/(2*Ro^2)), and the true inner-wall rate
exceeds the label rate because the unyielded plug (present at
gamma <= 10, attached to the outer wall) takes up part of the gap.

Validation gate: simulated torque must match the analytic TC torque
within 10% (default). Exits non-zero on failure.

Usage: python3 couette_post.py [--runs runs] [--validation-tol 0.10]
Writes flow_curve.csv and flow_curve.png in examples/couette-tc/.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import yaml  # noqa: E402

HERE = Path(__file__).parent

# --- TC parameters (from case.yaml; duplicated here so this script is
# --- self-contained — the values are checked against case.yaml at runtime)
SIGMA_Y = 70.0       # Pa
GAMMA_DOT_C = 100.0  # 1/s
ETA_BG = 0.05        # Pa s
B = SIGMA_Y / math.sqrt(GAMMA_DOT_C)  # coefficient of sqrt(gamma_dot)


def gamma_of_tau(tau):
    """Invert TC law: shear rate for a given shear stress (0 if unyielded)."""
    if tau <= SIGMA_Y:
        return 0.0
    disc = B * B - 4.0 * ETA_BG * (SIGMA_Y - tau)
    x = (-B + math.sqrt(disc)) / (2.0 * ETA_BG)
    return x * x


def omega_of_T(T, Ri, Ro, L, n=2000):
    """Angular velocity for a given torque, by quadrature over the gap."""
    if T <= 0:
        return 0.0
    r_yield = math.sqrt(T / (2.0 * math.pi * L * SIGMA_Y))
    r_hi = min(Ro, r_yield)
    if r_hi <= Ri:
        return 0.0
    total = 0.0
    ln_lo, ln_hi = math.log(Ri), math.log(r_hi)
    dln = (ln_hi - ln_lo) / n
    for i in range(n):
        ln_r = ln_lo + (i + 0.5) * dln
        r = math.exp(ln_r)
        tau = T / (2.0 * math.pi * L * r * r)
        total += gamma_of_tau(tau) * dln  # gamma(r)/r * dr = gamma * d(ln r)
    return total


def torque_of_omega(omega, Ri, Ro, L, tol=1e-12):
    """Torque for a given angular velocity, by bisection on T."""
    T_lo = 2.0 * math.pi * L * SIGMA_Y * Ri * Ri  # tau(Ri) = sigma_y
    T_hi = T_lo * 2.0
    while omega_of_T(T_hi, Ri, Ro, L) < omega:
        T_hi *= 2.0
    for _ in range(200):
        T_mid = 0.5 * (T_lo + T_hi)
        if omega_of_T(T_mid, Ri, Ro, L) < omega:
            T_lo = T_mid
        else:
            T_hi = T_mid
        if (T_hi - T_lo) / T_mid < tol:
            break
    return 0.5 * (T_lo + T_hi)


def load_case(path=HERE / "case.yaml"):
    with open(path) as fh:
        return yaml.safe_load(fh)


def read_torque(path):
    iters, torques = [], []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            iters.append(float(row["iteration"]))
            torques.append(float(row["torque_N_m"]))
    return iters, torques


def steady_mean(torques, frac):
    n = len(torques)
    k = max(1, int(n * frac))
    window = torques[-k:]
    mean = sum(window) / len(window)
    sd = (sum((x - mean) ** 2 for x in window) / len(window)) ** 0.5
    return mean, sd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(HERE / "runs"))
    ap.add_argument("--validation-tol", type=float, default=0.10)
    args = ap.parse_args()

    case = load_case()
    g, f, s = case["geometry"], case["fluid"], case["sweep"]
    Ri, Ro, L = g["R_i"], g["R_o"], g["L"]
    # check the duplicated TC constants against case.yaml
    assert abs(f["sigma_y_Pa"] - SIGMA_Y) < 1e-12, "sigma_y mismatch vs case.yaml"
    assert abs(f["gamma_dot_c_1_s"] - GAMMA_DOT_C) < 1e-12, "gamma_dot_c mismatch"
    assert abs(f["eta_bg_Pa_s"] - ETA_BG) < 1e-12, "eta_bg mismatch"
    frac = s["steady_window_fraction"]
    rows = []
    for gamma in s["shear_rate_1_s"]:
        run_dir = Path(args.runs) / f"gamma_{gamma}"
        path = run_dir / "torque.csv"
        if not path.exists():
            print(f"missing {path} — run the sweep first")
            return 1
        iters, torques = read_torque(path)
        T, sd = steady_mean(torques, frac)
        Omega = gamma * (Ro * Ro - Ri * Ri) / (2.0 * Ro * Ro)
        tau = T / (2.0 * math.pi * Ri * Ri * L)
        T_an = torque_of_omega(Omega, Ri, Ro, L)
        err = abs(T - T_an) / T_an if T_an else float("nan")
        r_y = math.sqrt(T_an / (2.0 * math.pi * L * SIGMA_Y))
        plug = min(r_y, Ro) < Ro - 1e-12
        info = {}
        info_path = run_dir / "run_info.json"
        if info_path.exists():
            info = json.loads(info_path.read_text())
        rows.append({"gamma": gamma, "omega": Omega, "tau": tau,
                     "eta_app": tau / gamma, "T": T, "T_analytic": T_an,
                     "rel_err": err, "torque_sd": sd,
                     "R_y_mm": min(r_y, Ro) * 1000, "plug": plug,
                     "converged": info.get("converged")})
        print(f"gamma={gamma:>6} 1/s  tau={tau:9.4f} Pa  eta_app={tau/gamma:9.4f} "
              f"Pa.s  T={T:.6e} N.m  T_an={T_an:.6e} N.m  err={err*100:.2f}%  "
              f"R_y={min(r_y, Ro)*1000:.2f} mm {'PLUG' if plug else 'fully yielded'}  "
              f"converged={info.get('converged')}")

    max_err = max(r["rel_err"] for r in rows)
    passed = max_err <= args.validation_tol
    print(f"TC validation: max analytic-torque error {max_err*100:.2f}% "
          f"(tol {args.validation_tol*100:.0f}%) — {'PASSED' if passed else 'FAILED'}")

    with open(HERE / "flow_curve.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["gamma_1_s", "omega_rad_s", "tau_Pa",
                                           "eta_app_Pa_s", "torque_N_m",
                                           "torque_analytic_N_m", "rel_err",
                                           "yield_radius_mm", "plug"])
        w.writeheader()
        for r in rows:
            w.writerow({"gamma_1_s": r["gamma"], "omega_rad_s": r["omega"],
                        "tau_Pa": r["tau"], "eta_app_Pa_s": r["eta_app"],
                        "torque_N_m": r["T"], "torque_analytic_N_m": r["T_analytic"],
                        "rel_err": r["rel_err"], "yield_radius_mm": r["R_y_mm"],
                        "plug": r["plug"]})

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].loglog([r["gamma"] for r in rows], [r["tau"] for r in rows], "o-",
                 label="OpenFOAM")
    ax[0].loglog([r["gamma"] for r in rows],
                 [r["T_analytic"] / (2 * math.pi * Ri * Ri * L) for r in rows],
                 "k--", label="analytic TC")
    ax[0].set_xlabel("shear rate (1/s)"); ax[0].set_ylabel("shear stress (Pa)")
    ax[0].set_title("Couette flow curve — TC fluid (OpenFOAM)")
    ax[0].legend()
    ax[1].loglog([r["gamma"] for r in rows], [r["eta_app"] for r in rows], "o-")
    ax[1].set_xlabel("shear rate (1/s)"); ax[1].set_ylabel("apparent viscosity (Pa.s)")
    ax[1].set_title("Apparent viscosity")
    fig.tight_layout()
    fig.savefig(HERE / "flow_curve.png", dpi=150)
    print("wrote flow_curve.csv and flow_curve.png")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
