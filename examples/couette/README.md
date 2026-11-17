# Couette example — OpenFOAM

Fluid in a Couette rheometer: inner cylinder rotates, outer cylinder
fixed, torque on the bob gives the flow curve. Same geometry and
fluid as the M-Star and Palabos examples, so the solvers can be
compared point for point.

## What is here

| File | What it does |
|---|---|
| `case.yaml` | The contract: geometry, fluid, mesh, solver, sweep. Confirm before running. |
| `case/` | Steady `simpleFoam` template (blockMeshDict, BCs, controlDict, fvSchemes, fvSolution, forces). **Run for real.** |
| `case-transient/` | Transient `pimpleFoam` template for the spin-up video. **Run for real.** |
| `couette_build.py` | Copy template → run dir, substitute Omega. |
| `couette_sweep.py` | Runs the sweep, one run per shear rate. Dry-run by default. |
| `couette_post.py` | Torque → flow curve + Newtonian validation gate. |
| `make_video.py` | Revolve the radial profiles into annulus videos (ffmpeg). |

## Defaults

R_i = 0.020 m, R_o = 0.025 m, L = 0.060 m, Newtonian η = 1.0 Pa·s,
ρ = 1000 kg/m³, γ̇ = 0.1 → 100 s⁻¹ log-spaced, 40 cells across the
5 mm gap, 4° wedge sector, torque scale ×5400, simpleFoam to
3000 iterations (residualControl 1e-8 stops it early), steady
window = last 20% of the torque samples.

## Run it

```bash
bash ../../scripts/check-setup.sh
./../../run-couette.sh            # dry run: build mesh + checkMesh
./../../run-couette.sh --run      # sweep + post-process
./../../run-couette.sh --video    # videos from runs/
python3 couette_post.py           # flow_curve.csv + flow_curve.png, validation gate
```

## Honest status (v0.1 — run for real, 2026-11-17)

- `couette_build.py` / `couette_sweep.py` / `couette_post.py`:
  **run for real** against OpenFOAM v2412 (Ubuntu 24.04).
  `blockMesh` + `checkMesh` report Mesh OK (40 cells, wedge 2°+2°,
  non-orthogonality 0). γ̇ = 10 converges in ~2050 iterations
  (~2 s) with final Uz residual 6.7e-9.
- **Newtonian validation PASSED on a real run**: γ̇ = 10,
  T = 1.508e-3 N·m vs analytic 1.508e-3 N·m, error **0.03%**;
  velocity profile matches the analytic Couette profile to
  0.47% max / 0.04% mean. See `flow_curve.csv`,
  `flow_curve.png`, `RUN_REPORT.md`.
- Transient `pimpleFoam` spin-up at γ̇ = 10: 1000 steps in ~2 s,
  converges to the same torque (1.508e-3 N·m).
- Videos: `couette-gamma10.mp4` (spin-up at γ̇ = 10),
  `couette-sweep.mp4` (steady state across the sweep) — rendered
  from real run data by `make_video.py`.
- Two bugs found and fixed on the way (see `RUN_REPORT.md`):
  `nu` was 1e-06 (water) instead of 1e-03 — torque 1000× small
  while the profile looked right; and v2412 reads
  `constant/turbulenceProperties`, not `momentumTransport`.
- Still unverified: non-Newtonian fluids (no model run yet —
  Herschel–Bulkley / Bird–Carreau coefficients are documented in
  `docs/openfoam-guide.md` but not run) and a full 3D annulus
  (wedge sector here).

## Analytic check

γ̇_i = 2·Ω·R_o²/(R_o²−R_i²), τ_i = T/(2π·R_i²·L),
T_analytic = 4π·L·η·Ω·R_i²·R_o²/(R_o²−R_i²).
At γ̇ = 10 s⁻¹: Ω = 1.8 rad/s (17.2 rpm), T = 1.508e-3 N·m, τ = 10 Pa.
