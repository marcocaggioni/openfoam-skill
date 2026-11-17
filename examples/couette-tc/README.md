# Couette example — three-component (TC) fluid — OpenFOAM

Fluid in a Couette rheometer: inner cylinder rotates, outer cylinder
fixed, torque on the bob gives the flow curve. Same geometry and sweep
as the Newtonian example (`examples/couette/`), but the fluid is
Marco's three-component model fluid:

    tau = sigma_y + sigma_y*sqrt(gamma_dot/gamma_dot_c) + eta_bg*gamma_dot

with sigma_y = 70 Pa, gamma_dot_c = 100 1/s, eta_bg = 50 cP = 0.05 Pa·s,
rho = 1000 kg/m³. At gamma <= 10 the gap is only partly yielded: an
unyielded plug sits against the outer wall (yield radius R_y < R_o),
so the inner-wall shear rate exceeds the label rate — the validation
is torque vs the analytic TC torque at each Omega, not eta_app vs the
TC law at the label rate.

## What is here

| File | What it does |
|---|---|
| `case.yaml` | The contract: geometry, TC fluid + regularization, mesh, solver, sweep. |
| `lib/` | Custom `threeComponent` viscosity model (`.C`/`.H`, `Make/`, `build.sh`). **The TC law is not a built-in OpenFOAM model** — this library is the model. |
| `case/` | Steady `simpleFoam` template (blockMeshDict, BCs, controlDict, fvSchemes, fvSolution, forces, TC transportProperties). **Run for real.** |
| `case-transient/` | Transient `pimpleFoam` template for the spin-up video. **Run for real.** |
| `couette_build.py` | Copy template → run dir, substitute Omega. |
| `couette_sweep.py` | Runs the sweep, one run per shear rate. Dry-run by default. |
| `couette_post.py` | Torque → flow curve + analytic-TC validation gate (10%). |
| `make_video.py` | Revolve the radial profiles into annulus videos (ffmpeg). |

## Defaults

R_i = 0.020 m, R_o = 0.025 m, L = 0.060 m, sigma_y = 70 Pa,
gamma_dot_c = 100 1/s, eta_bg = 0.05 Pa·s, rho = 1000 kg/m³,
gamma = 0.1 → 100 s⁻¹ log-spaced, 40 cells across the 5 mm gap,
4° wedge sector, torque scale ×5400, simpleFoam to 3000 iterations
(residualControl 1e-8), steady window = last 20% of the torque
samples.

## Regularization (required — read this first)

eta(gamma_dot) = sigma_y/gamma_dot + sigma_y/sqrt(gamma_dot*gamma_dot_c)
+ eta_bg diverges as gamma_dot -> 0, so the model caps the viscosity:
eta = min(eta(gamma_dot), eta_max) with eta_max = eta(gamma_dot_reg),
gamma_dot_reg = 1e-3 1/s, i.e. eta_max = 70221.41 Pa·s
(nu_max = 70.22141 m²/s). The cap only bites where gamma_dot < 1e-3 1/s
— deep inside the unyielded plug, where the true model has
gamma_dot = 0 and the exact viscosity is infinite. The yielded region
carrying the torque is unaffected; the plug creeps at ~1e-3 1/s instead
of sitting exactly still. See `case.yaml`, `lib/threeComponent.H`,
and `RUN_REPORT.md`.

## Run it

```bash
bash ../../scripts/check-setup.sh
bash lib/build.sh                    # compile libthreeComponent.so (once)
python3 couette_sweep.py --run       # sweep + torque CSVs in runs/
python3 couette_post.py              # flow_curve.csv + flow_curve.png, validation gate
python3 make_video.py                # couette-tc-gamma10.mp4 + couette-tc-sweep.mp4
```

## Honest status (v0.1 — run for real, 2026-11-17)

- `lib/threeComponent`: **built and run for real** against OpenFOAM
  v2412 (Ubuntu 24.04). `wmake libso` compiles clean; simpleFoam
  selects it (`Selecting incompressible transport model
  threeComponent`) via `libs` in `controlDict`. The nu field it
  writes is self-consistent: at gamma = 10 the inner-wall cell reads
  nu = 0.00401 m²/s vs 0.00389 expected from the TC law at the
  inner-wall rate, and the plug cells read nu up to ~50 m²/s (below
  the 70.22 cap — the plug creeps at ~1.4e-3 1/s).
- **TC validation PASSED on a real run**: max analytic-torque error
  **0.82%** (at gamma = 0.1), all seven points within 0.82%.
  See `flow_curve.csv`, `flow_curve.png`, `RUN_REPORT.md`.
- Transient `pimpleFoam` spin-up at gamma = 10: 1000 steps in ~1.2 s,
  converges to the same torque (1.630e-2 N·m vs steady 1.634e-2).
- Videos: `couette-tc-gamma10.mp4` (spin-up at gamma = 10),
  `couette-tc-sweep.mp4` (steady state across the sweep) — rendered
  from real run data by `make_video.py`.
- Caveat (documented in `RUN_REPORT.md`): at gamma = 30 and 100 the
  Uz residual plateaus at ~1e-6 after 3000 iterations, so the sweep
  script flags those two runs `converged: false` (its criterion is
  Uz < 1e-7). The torque is nevertheless flat (relative SD <= 7.6e-4
  in the steady window, drift <= 0.07%), and 6000-iteration check
  runs move those torques by only -0.36% / -0.17% — towards the
  analytic values. The flag is a slow solver-iteration transient in
  the viscosity field, not a torque error.
- Still unverified: mesh refinement (40 cells across the gap gives
  0.82% here; no coarser/finer comparison), a full 3D annulus
  (wedge sector here), other OpenFOAM versions.

## Analytic check

tau(r) = T/(2*pi*L*r^2); invert the TC law for gamma_dot(tau)
(quadratic in sqrt(gamma_dot); gamma_dot = 0 where tau < sigma_y);
Omega = integral_{Ri}^{R_y} gamma_dot dr/r with
R_y = min(Ro, sqrt(T/(2*pi*L*sigma_y))); solve for T given Omega by
bisection. Reference implementation: `~/workspace/tc-analytic.py`
(copied into `couette_post.py` so this repo is self-contained).
At gamma = 10 s⁻¹: Omega = 1.8 rad/s (17.2 rpm),
T_analytic = 1.628e-2 N·m, tau_i = 108.0 Pa, R_y = 24.84 mm (plug).
