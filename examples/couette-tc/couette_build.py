#!/usr/bin/env python3
"""Build one OpenFOAM Couette run directory from the case template.

Copies examples/couette-tc/case/ (or case-transient/ with --transient) to
the output directory and substitutes __OMEGA__ in 0/U with the angular
velocity for the requested shear rate.

    Omega = gamma * (Ro^2 - Ri^2) / (2 * Ro^2)

Usage:
    python3 couette_build.py --gamma 10 --out runs/gamma_10
    python3 couette_build.py --gamma 10 --out runs/gamma_10_spinup --transient
"""
import argparse
import math
import shutil
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent


def load_case(path=HERE / "case.yaml"):
    with open(path) as fh:
        return yaml.safe_load(fh)


def omega_for_gamma(gamma, Ri, Ro):
    return gamma * (Ro * Ro - Ri * Ri) / (2.0 * Ro * Ro)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gamma", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--transient", action="store_true",
                    help="use the pimpleFoam spin-up template (case-transient/)")
    ap.add_argument("--case", default=str(HERE / "case.yaml"))
    args = ap.parse_args()

    case = load_case(args.case)
    g = case["geometry"]
    Ri, Ro = g["R_i"], g["R_o"]
    omega = omega_for_gamma(args.gamma, Ri, Ro)

    template = HERE / ("case-transient" if args.transient else "case")
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(template, out)

    u_file = out / "0" / "U"
    text = u_file.read_text()
    if "__OMEGA__" not in text:
        print("ERROR: 0/U has no __OMEGA__ placeholder — refusing to guess")
        return 1
    u_file.write_text(text.replace("__OMEGA__", repr(omega)))

    print(f"built {out}  gamma={args.gamma} 1/s  Omega={omega:.6g} rad/s "
          f"({omega * 60 / (2 * math.pi):.3g} rpm)"
          + ("  [transient pimpleFoam]" if args.transient else "  [steady simpleFoam]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
