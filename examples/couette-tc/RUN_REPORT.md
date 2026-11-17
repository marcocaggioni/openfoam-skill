# RUN_REPORT — OpenFOAM Couette example, three-component fluid (v0.1, run for real 2026-11-17)

## What ran

OpenFOAM **v2412** (ESI/OpenCFD, `openfoam2412` + `openfoam2412-tutorials`
+ `openfoam2412-dev` + `openfoam2412-source` Debian packages),
installed on Ubuntu 24.04.5 LTS in this VM via the official route
(`https://dl.openfoam.com/add-debian-repo.sh`, then `apt-get install
openfoam2412 openfoam2412-tutorials openfoam2412-dev openfoam2412-source`).
The `-dev`/`-source` packages were needed because the runtime package
alone ships no headers or model source, and the custom viscosity model
below is compiled against them. Install location
`/usr/lib/openfoam/openfoam2412/`; sourced with
`. /usr/lib/openfoam/openfoam2412/etc/bashrc`. Machine: 4 CPUs,
~7.7 GB RAM, running as root.

Full sweep, TC fluid, 2026-11-17 ~13:40 UTC: 7 simpleFoam runs, one
per shear rate, plus one pimpleFoam spin-up run at γ̇ = 10 for the
video. Total solver wall time 75.4 s (sweep) + 1.2 s (spin-up).
Everything was run through the repo's own scripts
(`python3 couette_sweep.py --run`, `python3 couette_post.py`,
`python3 make_video.py`).

## Case

Same geometry and sweep as the Newtonian example
(`examples/couette/`): R_i = 0.020 m (rotating bob), R_o = 0.025 m
(fixed cup), L = 0.060 m, ρ = 1000 kg/m³, γ̇ = [0.1, 0.3, 1, 3, 10,
30, 100] s⁻¹ log-spaced (Newtonian inner-wall-rate convention,
Ω = γ̇(R_o²−R_i²)/(2R_o²)). Fluid: the three-component model
(Marco, Nov 17):

    tau = sigma_y + sigma_y*sqrt(gamma_dot/gamma_dot_c) + eta_bg*gamma_dot
    sigma_y = 70 Pa, gamma_dot_c = 100 1/s, eta_bg = 0.05 Pa·s (50 cP)

## The custom viscosity model (the TC law is not built in)

OpenFOAM v2412 has no TC model (built-ins: Herschel-Bulkley,
Bird-Carreau, Casson, power-law, Cross, strainRateFunction — none has
the sqrt(γ̇) term), so TC is implemented as a custom viscosity model
in `lib/threeComponent/` (`threeComponent.H/.C`), following the
HerschelBulkley transport-model pattern (same base class, same
`calcNu()`/`correct()`/`read()` structure, same
`addToRunTimeSelectionTable` registration). No built-in model was
substituted.

- Kinematic form (all coefficients divided by ρ = 1000 kg/m³, as for
  every OpenFOAM viscosity model):
  `nu = min(nuMax, (tau0 + k*sqrt(sr) + nuBg*sr) / max(sr, VSMALL))`
  with `tau0 = 0.07 m²/s²`, `k = 0.007 m²/s` (the `k*rtone*sqrt(tone*sr)`
  dimensional trick is copied from HerschelBulkley),
  `nuBg = 5e-05 m²/s`, `sr = strainRate()` = √2·|symm(grad U)|.
- **Regularization:** `nuMax = 70.22141 m²/s` (η_max = 70221.41 Pa·s),
  the TC viscosity at γ̇_reg = 1e-3 1/s:
  η_max = 70/1e-3 + 70/√(1e-3·100) + 0.05·1e-3 = 70221.41 Pa·s.
  The cap only bites where γ̇ < 1e-3 1/s, i.e. deep inside the
  unyielded plug, where the true model has γ̇ = 0 and the exact
  viscosity is infinite. The yielded region carrying the torque is
  unaffected; the plug creeps at ~1e-3 1/s instead of sitting exactly
  still.
- Build: `bash lib/build.sh` (`wmake libso` → `$FOAM_USER_LIBBIN/
  libthreeComponent.so`, compiles clean, no warnings). Load:
  `libs ("libthreeComponent.so");` in `system/controlDict`
  (OpenFOAM's `Time` opens controlDict `libs` at startup); the
  transportProperties selects it with `transportModel threeComponent;`
  plus a `threeComponentCoeffs` subdict. simpleFoam confirms with
  `Selecting incompressible transport model threeComponent`.
- Field check (γ̇ = 10, final time dir, `nu` field): inner-wall cell
  ν = 0.00401 m²/s vs 0.00389 expected from inverting the TC law at
  the inner-wall stress (108.35 Pa → γ̇_i = 27.9 1/s); the difference
  is the cell-centre vs wall value across the first 0.125 mm cell.
  Outer-wall (plug) cell ν = 50.4 m²/s, below the 70.22 cap — the
  plug creeps at γ̇ ≈ 1.4e-3 1/s, self-consistent with
  ν(γ̇) = (0.07 + 0.007√γ̇ + 5e-5·γ̇)/γ̇.

## Mesh and boundary conditions

Identical to the Newtonian case (same `blockMeshDict`, same BCs):
4° wedge sector, axis = X, x = 0..0.001 m with ONE cell, radial 40
cells across the 5 mm gap (dx = 0.125 mm), `checkMesh`: **Mesh OK.**
`innerWall`: `rotatingWallVelocity`, `outerWall`: `noSlip`,
`back`/`front`: `wedge`, `left`/`right`: `empty`, pressure
`fixedFluxPressure` on both walls, `pRefCell 0; pRefValue 0;`,
`simulationType laminar`, SIMPLE with GAMG (p) + smoothSolver (U),
relaxation p 0.3 / U 0.7, `residualControl` p/U 1e-8,
`endTime 3000` iterations. Torque scaling unchanged:
`T_full = M_x × 5400`.

## γ̇ = 10 check (run first, before the sweep)

- Ω = 1.8 rad/s (17.2 rpm). Analytic TC T = 1.628e-2 N·m,
  τ_i = 108.0 Pa, R_y = 24.84 mm (plug attached to the outer wall).
- 3000 iterations (~11 s), final Uz residual 3.1e-8.
- **Simulated T = 1.634e-2 N·m, error +0.37%.**
- Transient cross-check: `pimpleFoam` spin-up (1000 steps of
  0.001 s) converges to 1.630e-2 N·m (−0.23% vs the steady run).

## Full sweep — validation vs analytic TC torque

| γ̇ (1/s) | Ω (rad/s) | iters | wall (s) | T (N·m) | T analytic (N·m) | err | τ_i (Pa) | R_y (mm) | plug? |
|---|---|---|---|---|---|---|---|---|---|
| 0.1 | 0.018 | 3000 | 8.6 | 1.17660e-02 | 1.16706e-02 | 0.82% | 78.03 | 21.03 | yes |
| 0.3 | 0.054 | 3000 | 8.9 | 1.22784e-02 | 1.21841e-02 | 0.77% | 81.42 | 21.49 | yes |
| 1 | 0.18 | 3000 | 8.0 | 1.31043e-02 | 1.30377e-02 | 0.51% | 86.90 | 22.23 | yes |
| 3 | 0.54 | 3000 | 11.3 | 1.42804e-02 | 1.42313e-02 | 0.35% | 94.70 | 23.22 | yes |
| 10 | 1.8 | 3000 | 10.8 | 1.63392e-02 | 1.62797e-02 | 0.37% | 108.35 | 24.84 | yes |
| 30 | 5.4 | 3000 | 13.0 | 1.93961e-02 | 1.93138e-02 | 0.43% | 128.62 | 25.00 | no |
| 100 | 18 | 3000 | 14.8 | 2.52870e-02 | 2.52340e-02 | 0.21% | 167.69 | 25.00 | no |

- **TC validation: PASSED. Max analytic-torque error 0.82%
  (tolerance 10%).** All errors are positive (simulated torque
  0.2–0.8% high) — a small systematic, likely the first-cell
  discretization of the steep near-wall shear-rate gradient plus the
  creeping plug contributing a little extra drag. Largest at the
  lowest rate, where the yielded layer is thinnest (R_y − R_i =
  1.03 mm at γ̇ = 0.1, ~8 cells).
- Analytic reference: `couette_post.py` copies the shared reference
  implementation (`~/workspace/tc-analytic.py`): τ(r) = T/(2πLr²),
  invert the TC law (quadratic in √γ̇, γ̇ = 0 where τ < σ_y),
  Ω = ∫γ̇ dr/r out to R_y, bisection on T. The integral machinery
  was verified against the known Newtonian analytic torque (0.0000%
  diff). Validation is torque vs torque at each Ω — **not** η_app vs
  the TC law at the label rate: the label γ̇ is the Newtonian
  inner-wall-rate convention, and the true inner-wall rate exceeds
  it (e.g. 27.9 1/s at label 10) because the plug takes up part of
  the gap.
- Steady window: torque averaged over the last 20% of the
  `moment.dat` samples (600 samples per run). Relative SD within the
  window ≤ 7.6e-4; drift between the last-10% and last-20% means
  ≤ 0.065% — the torque is flat once the viscosity field settles.
- Outputs: `flow_curve.csv`, `flow_curve.png` (τ vs γ̇ with the
  analytic TC curve overlaid; η_app panel),
  `couette-tc-gamma10.mp4` (spin-up, 21 frames, 5.25 s),
  `couette-tc-sweep.mp4` (7 steady frames, 7 s). Both videos revolve
  the real 1D radial profile into a full annulus; colour is
  u_theta, each frame scaled to its own maximum.

## The γ̇ = 30 / 100 convergence flags — diagnosed, not dropped

The sweep script flags a run `converged: false` when its final Uz
initial residual is ≥ 1e-7. At γ̇ = 30 and 100 the residuals are
6.82e-06 and 3.03e-06 after 3000 iterations — above the flag — while
the other five points are at ≤ 3.1e-8. Diagnosis (from the logs):

- The residual is not stuck: at γ̇ = 100 it rises mid-run to
  ~1e-4 around iteration 1000 (the viscosity field redistributing
  as the plug yields) and then decays steadily, roughly ×0.5 per
  500 iterations (1.92e-05 at 2000 → 7.65e-06 at 2500 → 3.03e-06
  at 3000). Same shape at γ̇ = 30. It is a slow SIMPLE-iteration
  transient in the high-viscosity-contrast field, not a limit
  cycle and not a physics problem.
- The torque does not care: relative SD ≤ 7.6e-4 in the steady
  window, and 6000-iteration check runs (same case, `endTime 6000`,
  scratch dirs `/tmp/check_30`, `/tmp/check_100`, not part of the
  sweep) move the torques by only −0.36% (γ̇ = 30: 1.9327e-02,
  error +0.07%, Uz 1.73e-07) and −0.17% (γ̇ = 100: 2.5245e-02,
  error +0.04%, Uz 1.54e-08) — *towards* the analytic values.
  The 3000-iteration torques in the table above are therefore
  conservative (biased high by ≤ 0.4%) and the gate passes with
  margin either way. The official curve keeps the uniform
  3000-iteration sweep; the check runs are the evidence the flag
  is a solver-iteration artifact.

## Still unverified

- **Mesh refinement.** 40 cells across the gap gives 0.82% max
  error here; no coarser/finer mesh comparison has been run. The
  low-rate error growing as the yielded layer thins suggests the
  first cells across the gap dominate the error — a finer mesh (or
  grading towards the inner wall) is the obvious next check.
- **Full 3D annulus.** Wedge sector only — no end effects, no
  Taylor vortices by construction.
- **Other OpenFOAM versions.** Everything above is v2412.
- **Profile-derived torque.** Not implemented (the `forces`
  functionObject moment is the primary measurement).
- **`run-couette.sh` on a fresh machine** (the sweep was run here
  via the repo scripts). Note for a fresh machine: OpenFOAM alone
  is not enough — `openfoam2412-dev` and `openfoam2412-source`
  must also be installed, and `lib/build.sh` run once, before the
  TC case will load.
