# openfoam-skill

Skill teaching an agent to run open-source OpenFOAM finite-volume
simulations from an English discussion — starting with a Couette
rheometer flow curve. **Public repo. No license needed.**

OpenFOAM (openfoam.com, ESI/OpenCFD) is the open-source standard
for finite-volume CFD, GPL, C++ with MPI. This is the open-source
counterpart of the private `mstar-skill` repo and of
`palabos-skill`: same workflow, same Couette example, different
solver — no license seat, no GUI, no `.msb` file. Instead you write
dictionary files and run the solvers from the command line. The
payoff over the LBM routes: built-in rheology models (Newtonian,
power-law, Herschel–Bulkley, Bird–Carreau, Cross, Casson),
a `rotatingWallVelocity` boundary condition, and a mature
steady/transient solver pair (`simpleFoam` / `pimpleFoam`).

## Quickstart

```bash
git clone https://github.com/marcocaggioni/openfoam-skill.git
cd openfoam-skill
uv sync              # Python side only (numpy, matplotlib, pyyaml)
bash scripts/install-openfoam.sh   # OpenFOAM v2412 via the official Debian repo
bash scripts/check-setup.sh
copilot
```

First prompt:

```
/openfoam-simulation run the Couette example in examples/couette/case.yaml
```

Or one go: `copilot -i "Use the /openfoam-simulation skill to run the Couette example in examples/couette/case.yaml"`. Copilot must be started from the repo root; if the skill was added mid-session, run `/skills reload`. See `QUICKSTART.md`.

## The workflow

1. **Discuss** in English — geometry, fluid + rheology, sweep, what is measured.
2. **Write `case.yaml`**, show it, get a yes. Never skip this, never invent a number.
3. **Mesh** — `blockMeshDict`: a 4° wedge sector for Couette, checked with `checkMesh`.
4. **Build** the case (copy template, substitute Omega). Dry-run by default.
5. **Sweep / run** — one `simpleFoam` run per shear rate, torque CSV per run.
6. **Post-process** torque → flow curve, with a mandatory Newtonian validation gate (analytic Couette torque, ~10%).
7. **Report** — plot + CSV + assumptions + validation + unverified items.

## The Couette example

Fluid in a Couette rheometer, inner cylinder rotating, outer fixed,
torque on the bob → flow curve. Defaults (labelled, to confirm):
R_i = 0.020 m, R_o = 0.025 m, L = 0.060 m, Newtonian η = 1.0 Pa·s,
ρ = 1000 kg/m³, γ̇ = 0.1 → 100 s⁻¹ log-spaced, 40 cells across the
5 mm gap. The mesh is a 4° wedge sector (axisymmetric: no Taylor
vortices, no end effects) with torque scaled ×5400 to the full
cylinder. Same numbers as the M-Star and Palabos examples, so the
solvers can be compared point for point.

## Results — it ran

<video src="https://raw.githubusercontent.com/marcocaggioni/openfoam-skill/main/examples/couette/couette-sweep.mp4" controls></video>

Steady state at each shear rate, γ̇ = 0.1 → 100 s⁻¹. The spin-up at γ̇ = 10 s⁻¹ is in [couette-gamma10.mp4](examples/couette/couette-gamma10.mp4).

![Flow curve](examples/couette/flow_curve.png)

Newtonian validation **PASSED**: max analytic-torque error **0.03%**, η_app = 1.0003 Pa·s (true 1.0) at all seven shear rates. Note the mesh is a 4° wedge sector, not a full 3D annulus — no end effects yet. Full numbers in [examples/couette/RUN_REPORT.md](examples/couette/RUN_REPORT.md).

## The Couette example — three-component (TC) fluid

Same geometry and sweep, but the fluid is Marco's three-component
model fluid: τ = σ_y + σ_y·√(γ̇/γ̇_c) + η_bg·γ̇, with σ_y = 70 Pa,
γ̇_c = 100 1/s, η_bg = 50 cP = 0.05 Pa·s, ρ = 1000 kg/m³. At γ̇ ≤ 10
the gap is only partly yielded — an unyielded plug sits against the
outer wall — so validation is torque vs the analytic TC torque at
each Ω, not η_app vs the TC law at the label rate.

<video src="https://raw.githubusercontent.com/marcocaggioni/openfoam-skill/main/examples/couette-tc/couette-tc-sweep.mp4" controls></video>

Steady state at each shear rate, γ̇ = 0.1 → 100 s⁻¹. The spin-up at γ̇ = 10 s⁻¹ is in [couette-tc-gamma10.mp4](examples/couette-tc/couette-tc-gamma10.mp4).

![Flow curve — TC fluid](examples/couette-tc/flow_curve.png)

**TC validation PASSED**: max analytic-torque error **0.82%**
(at γ̇ = 0.1), all seven points within 0.82% of the analytic TC
torque. Two notes, both documented in
[examples/couette-tc/RUN_REPORT.md](examples/couette-tc/RUN_REPORT.md):

- **There is no built-in TC model in OpenFOAM**, so TC is a custom
  viscosity model in `examples/couette-tc/lib/threeComponent/`,
  following the Herschel–Bulkley pattern (`wmake libso`, loaded via
  `libs` in `controlDict`). No built-in model was substituted.
- **Regularization:** η(γ̇) diverges as γ̇ → 0, so the model caps
  it at η_max = 70221.41 Pa·s, the TC viscosity at γ̇_reg = 1e-3 1/s.
  The cap only bites inside the unyielded plug; the yielded region
  carrying the torque is unaffected (the plug creeps at ~1e-3 1/s).
- At γ̇ = 30 and 100 the Uz residual plateaus at ~1e-6 after 3000
  iterations, so the sweep flags those runs `converged: false` — but
  the torque is flat (relative SD ≤ 7.6e-4) and 6000-iteration check
  runs move those torques by only −0.36% / −0.17%, towards the
  analytic values. A slow solver-iteration transient, not a torque
  error.

## How this compares

Same Couette case, same validation, five solvers. Full write-up: [docs/comparison.md](docs/comparison.md).

| Solver | Method | Repo | Validation (max error) | η_app | Sweep video |
|---|---|---|---|---|---|
| M-Star | LBM, GPU, licensed | [mstar-skill](https://github.com/marcocaggioni/mstar-skill) (private) | not yet run | — | — |
| Palabos | LBM, C++/MPI, AGPLv3 | [palabos-skill](https://github.com/marcocaggioni/palabos-skill) | 1.43% | 1.0143 | [video](https://github.com/marcocaggioni/palabos-skill/blob/main/examples/couette/couette-sweep.mp4) |
| XLB | LBM, Python/JAX | [xlb-skill](https://github.com/marcocaggioni/xlb-skill) | 1.16% | 0.988–1.000 | [video](https://github.com/marcocaggioni/xlb-skill/blob/main/examples/couette/couette-sweep.mp4) |
| OpenFOAM | Finite-volume, GPL | [openfoam-skill](https://github.com/marcocaggioni/openfoam-skill) | 0.03% | 1.0003 | [video](https://github.com/marcocaggioni/openfoam-skill/blob/main/examples/couette/couette-sweep.mp4) |
| OpenLB | LBM, C++/CUDA, GPLv2 | [openlb-skill](https://github.com/marcocaggioni/openlb-skill) | 0.94% | 1.0093 | [video](https://github.com/marcocaggioni/openlb-skill/blob/main/examples/couette/couette-sweep.mp4) |

## Status — v0.1

- `couette_build.py`, `couette_sweep.py`, `couette_post.py`:
  **tested in this VM** (OpenFOAM v2412, Ubuntu 24.04, 2026-11-17).
- **Newtonian validation PASSED on a real run**: full sweep
  γ̇ = 0.1 → 100 s⁻¹, η_app = 1.0003 Pa·s at γ̇ = 10
  (true 1.0), analytic torque error 0.03% — see
  `examples/couette/RUN_REPORT.md`, `flow_curve.csv/png`, and the
  videos `couette-gamma10.mp4` / `couette-sweep.mp4`.
- The transient `pimpleFoam` spin-up also runs (1000 steps, ~2 s)
  and converges to the same torque.
- **TC fluid (new, 2026-11-17):** the three-component model runs
  in `examples/couette-tc/` as a custom viscosity model
  (`libthreeComponent.so`); TC validation **PASSED**, max
  analytic-torque error **0.82%** — see
  `examples/couette-tc/RUN_REPORT.md`, `flow_curve.csv/png`, and the
  videos `couette-tc-gamma10.mp4` / `couette-tc-sweep.mp4`. Fresh
  machines also need `openfoam2412-dev` + `openfoam2412-source`
  installed and `lib/build.sh` run once.
- Still open: a full 3D annulus (wedge sector here) and mesh
  refinement for the TC case (the low-rate error grows as the
  yielded layer thins).

## Files

- `skills/openfoam-simulation/SKILL.md` — the skill, mirrored at `.github/skills/openfoam-simulation/SKILL.md`
- `docs/openfoam-guide.md` — install, mesh, BCs, non-Newtonian notes, limits
- `examples/couette/` — the worked Newtonian example
- `examples/couette-tc/` — the three-component fluid example: custom
  `threeComponent` viscosity model in `lib/`, steady + transient
  templates, sweep/post/video scripts, `RUN_REPORT.md`
- `scripts/check-setup.sh` — readiness check (copilot, uv, simpleFoam, blockMesh, checkMesh)

OpenFOAM: https://www.openfoam.com (GPL).
This repo's own code: MIT.
