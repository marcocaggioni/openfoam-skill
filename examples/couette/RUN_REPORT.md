# RUN_REPORT — OpenFOAM Couette example (v0.1, run for real 2026-11-17)

## What ran

OpenFOAM **v2412** (ESI/OpenCFD, `openfoam2412` + `openfoam2412-tutorials`
Debian packages), installed on Ubuntu 24.04.5 LTS in this VM via the
official route (`https://dl.openfoam.com/add-debian-repo.sh`, then
`apt-get install openfoam2412 openfoam2412-tutorials`). Install location
`/usr/lib/openfoam/openfoam2412/`; sourced with
`. /usr/lib/openfoam/openfoam2412/etc/bashrc`. Machine: 4 CPUs,
~7.7 GB RAM, running as root.

Full sweep, Newtonian validation case, 2026-11-17 ~02:49 UTC:
7 simpleFoam runs, one per shear rate, plus one pimpleFoam spin-up
run at γ̇ = 10 for the video. Total solver wall time ~25 s (sweep)
+ ~2 s (spin-up). Everything was run through the repo's own scripts
(`./run-couette.sh --run`, `./run-couette.sh --video`).

## Case

Same geometry and fluid as the M-Star and Palabos Couette examples:
R_i = 0.020 m (rotating bob), R_o = 0.025 m (fixed cup), L = 0.060 m,
Newtonian η = 1.0 Pa·s, ρ = 1000 kg/m³, γ̇ = [0.1, 0.3, 1, 3, 10, 30,
100] s⁻¹ log-spaced.

## Mesh and boundary conditions (with references)

- **Wedge sector, not a full annulus, not a planar slice.** Cylinder
  axis = X, radial = Y, wedge opens in the Y–Z plane, total angle
  4° (half-angle 2°, OpenFOAM requires < 5°), axial extent
  x = 0..0.001 m with ONE cell, radial 40 cells across the 5 mm gap
  (dx = 0.125 mm), single hex block, `mergeType points;`.
  Rationale, verified by the numbers below: a planar slice would give
  a linear plane-Couette profile (shear 4Ω) instead of the true
  cylindrical profile (γ̇_i = 5.56Ω) — ~28% low torque; a full 3D
  annulus would develop Taylor vortices above Ta_c ≈ 41.3. The wedge
  models the ideal infinite-length Couette cell exactly.
  Pattern: the v2412 `movingCone` tutorial (wedge construction,
  `mergeType points;`, axis in-plane, `type empty;` axial faces).
- `checkMesh`: **Mesh OK.** 40 cells, wedge angle 2° per side,
  non-orthogonality max 0, max aspect ratio 8.02, max skewness 0.087,
  bounding box (0 0.02 −0.000873) – (0.001 0.025 0.000873).
- `innerWall`: `rotatingWallVelocity`, axis (1 0 0), origin (0 0 0),
  `omega constant <Ω>` in **rad/s**. Pattern: the v2412 `climbingRod`
  tutorial (`omega constant ${{ 2.1 * (2*pi()) }}`).
- `outerWall`: `noSlip`. `back`/`front`: `wedge`. `left`/`right`:
  `empty`. Pressure: `fixedFluxPressure` on both walls.
  `#includeEtc "caseDicts/setConstraintTypes"` in `0/U`.
- `constant/transportProperties`: `transportModel Newtonian;`
  `nu 1e-03;` (kinematic — see "Bugs found" below).
- `constant/turbulenceProperties`: `simulationType laminar;`.
- `system/fvSolution`: SIMPLE, GAMG (p) + smoothSolver (U),
  relaxation p 0.3 / U 0.7, `residualControl` p/U 1e-8,
  `pRefCell 0; pRefValue 0;` (required: all-wall case).
  Pattern: the v2412 `simpleFoam/pipeCyclic` tutorial.
- `system/controlDict`: `simpleFoam`, `endTime 3000` iterations,
  `writeInterval 250`, `forces` functionObject on `innerWall`
  (`rho rhoInf; rhoInf 1000; CofR (0 0 0); writeInterval 5`).
  Pattern: the v2412 `pimpleFoam/RAS/propeller` `system/forces`.
- Torque scaling: sector is a 4° slice of a 1 mm slice of the 60 mm
  cylinder, so `T_full = M_x × (360/4) × (0.060/0.001) = M_x × 5400`,
  where `M_x` is the moment about the X axis from the `forces`
  functionObject. The sign is negative (fluid drag opposes the
  rotation); the driving torque is the magnitude.

## γ̇ = 10 check (run first, before the sweep)

- Ω = 1.8 rad/s (17.2 rpm). Analytic T = 1.508e-3 N·m, τ = 10 Pa.
- Converged in ~2050 iterations (~2 s), final Uz residual 6.7e-9
  (residualControl stopped the run early).
- **Simulated T = 1.508e-3 N·m, error +0.03%.**
- Velocity profile vs analytic Couette profile (A·r + B/r):
  max error 0.47%, mean 0.04% (40 cell centres).
- Transient cross-check: `pimpleFoam` spin-up (1000 steps of
  0.001 s, Co_max ~0.03) converges to the same torque, 1.508e-3 N·m.

## Full sweep — validation

| γ̇ (1/s) | Ω (rad/s) | iters | wall (s) | T (N·m) | T analytic (N·m) | err | η_app (Pa·s) |
|---|---|---|---|---|---|---|---|
| 0.1 | 0.018 | 2920 | 3.2 | 1.50844e-05 | 1.50796e-05 | 0.03% | 1.0003 |
| 0.3 | 0.054 | 3000 | 3.6 | 4.52533e-05 | 4.52389e-05 | 0.03% | 1.0003 |
| 1 | 0.18 | 2004 | 3.2 | 1.50845e-04 | 1.50796e-04 | 0.03% | 1.0003 |
| 3 | 0.54 | 2018 | 2.6 | 4.52535e-04 | 4.52389e-04 | 0.03% | 1.0003 |
| 10 | 1.8 | 3000 | 5.0 | 1.50844e-03 | 1.50796e-03 | 0.03% | 1.0003 |
| 30 | 5.4 | 1920 | 2.9 | 4.52537e-03 | 4.52389e-03 | 0.03% | 1.0003 |
| 100 | 18 | 1945 | 4.4 | 1.50846e-02 | 1.50796e-02 | 0.03% | 1.0003 |

- **Newtonian validation: PASSED. Max analytic error 0.03%
  (tolerance 10%), η_app = 1.0003 Pa·s at every point (true 1.0).**
- Every run reported `converged: true` (final Uz initial residual
  ≤ 8.9e-9). Two runs (γ̇ = 0.3, 10) used the full 3000 iterations
  without the residualControl stopping them early, but their final
  residuals were 8.5e-10 and their torques match the others to 4
  digits — converged, just not early-stopped.
- Steady window: torque averaged over the last 20% of the
  `moment.dat` samples (384–600 samples per run). Relative SD
  within the window ≤ 6e-6 — the torque is flat once converged.
  (Early iterations overshoot: at γ̇ = 10 the torque reads ~23%
  high at iteration 250. Averaging the whole run would be wrong.)
- Flow regime: Re = U·d/ν ≤ 1.8, Ta = √(d/R_i)·Re ≤ 0.9 across the
  sweep — far below Ta_c ≈ 41.3, so no Taylor vortices even in a
  full annulus.
- Outputs: `flow_curve.csv`, `flow_curve.png` (τ vs γ̇ is a straight
  line of slope 1; the η_app panel is autoscaled to a ±5e-6 band
  around 1.0003, which exaggerates the point-to-point scatter —
  the numbers are in the CSV), `couette-gamma10.mp4` (spin-up,
  21 frames, 5.25 s), `couette-sweep.mp4` (7 steady frames, 7 s).
  Both videos revolve the real 1D radial profile into a full
  annulus; colour is u_theta, each frame scaled to its own maximum
  (wall speed spans 0.00036–0.36 m/s across the sweep).

## Bugs found on the way (all fixed in the repo)

1. **Kinematic viscosity trap (the big one).** The first draft used
   `nu = 1e-06` (copied from the `pipeCyclic` tutorial, which is
   water) for η = 1.0 Pa·s. That is η = 1e-3 Pa·s, and the torque
   came out exactly 1000× too small (1.51e-6 N·m) **while the
   velocity profile matched the analytic Couette profile to 0.5%**
   — the Newtonian profile is viscosity-independent, so the profile
   cannot catch this. Only the torque can. Fixed: `nu = 1e-03`
   (= η/ρ). The wrong value also made the SIMPLE convergence slow
   (the 3000-iteration run with ν = 1e-6 still had a 14% profile
   error at iteration 500 — the profile was still developing).
2. **`turbulenceProperties` vs `momentumTransport`.** v2412's
   simpleFoam requires `constant/turbulenceProperties`; the file
   was first written as `momentumTransport` (the newer name) and
   the solver exited "cannot find file .../turbulenceProperties".
   Renamed. The guide notes the rename for newer versions.
3. **Pressure reference cell.** All-wall case: simpleFoam exits
   "Unable to set reference cell for field p" without `pRefCell 0;
   pRefValue 0;` in the SIMPLE subdict. Added.
4. **`forces` output files.** v2412 writes `force.dat` and
   `moment.dat` (separate files), not `forces.dat`. The sweep
   script parses `moment.dat` (column `total_x` = moment about
   the X axis).
5. **PIMPLE needs `pFinal` / `(U)Final` solver entries.** Added
   (copies of `p` / `U` with `relTol 0`).
6. **`consistent yes;` in SIMPLE did not accelerate this case**
   (500 iterations still unconverged). Not used; the fix was
   `endTime 3000` + residualControl.
7. **Sourcing the OpenFOAM bashrc under `set -e`.** The setup
   script prints a harmless `pop_var_context` warning and returns
   non-zero in a non-interactive shell, which killed
   `run-couette.sh`. Fixed with `|| true` (documented in the script).

## Still unverified

- **Non-Newtonian fluids.** Herschel–Bulkley and Bird–Carreau are
  documented in `docs/openfoam-guide.md` (with the kinematic
  coefficient conversions) but no non-Newtonian run has been made.
  The coefficients must be verified against the model source before
  trusting a run.
- **Full 3D annulus.** Wedge sector only — no end effects, no
  Taylor vortices by construction. A full annulus is the follow-up.
- **Mesh refinement.** 40 cells across the gap gives 0.03% torque
  error here; no coarser/finer mesh comparison has been run.
- **Profile-derived torque.** Not implemented (the `forces`
  functionObject moment is the primary measurement).
- **Other OpenFOAM versions.** Everything above is v2412. The
  `momentumTransport` rename (v2506+) is noted but not tested.
- **`run-couette.sh --run` on a fresh machine** (the sweep was run
  here via the repo scripts, but the parent's push/CI has not
  re-run it). `scripts/check-setup.sh` reports MISS for the
  Copilot CLI in this VM (not installed here) — expected.
