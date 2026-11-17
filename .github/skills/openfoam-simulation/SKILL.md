---
name: openfoam-simulation
description: "Run an open-source OpenFOAM finite-volume simulation from an English discussion: elicit the geometry, fluid and operating conditions in plain language, turn them into a checked case file, build and run the OpenFOAM case from the command line, and turn the wall torque back into a physical result (e.g. a Couette flow curve). Use when the user wants a free, no-license CFD simulation — a Couette rheometer, a channel, a stirred tank — or asks for the open-source counterpart to an M-Star run."
---

# OpenFOAM Simulation

OpenFOAM (openfoam.com, ESI/OpenCFD) is the open-source standard
for finite-volume CFD, GPL, C++ with MPI. It is **not** a lattice
Boltzmann code like M-Star or Palabos: it solves the Navier–Stokes
equations on a mesh, with built-in viscosity models (Newtonian,
power-law, Herschel–Bulkley, Bird–Carreau, Cross, Casson), a
`rotatingWallVelocity` boundary condition, and steady
(`simpleFoam`) and transient (`pimpleFoam`) solvers. Torque comes
from the `forces` functionObject. This skill is the open-source
counterpart of the `mstar-simulation` skill in the private
`mstar-skill` repo and of `palabos-simulation`: same discussion →
case → run → report workflow, same Couette example, different
solver — no license seat, no GUI, no `.msb` file. Instead you write
dictionary files and run the solvers from the command line.

## The workflow, in order

```
1. Discuss (English)     -> what fluid, what geometry, what do you want to measure?
2. Write case.yaml       -> every number in one file, with units. Show it. Get a yes.
3. Mesh                  -> blockMeshDict: wedge sector for Couette. Check with checkMesh.
4. Build the case        -> copy the template, substitute Omega. No GUI.
5. Sweep / run           -> one simpleFoam run per shear rate, torque CSV per run.
6. Post-process          -> torque -> stress, omega -> shear rate, flow curve + validation.
7. Report                -> plot + CSV + what was assumed, checked, and unverified.
```

**Never skip step 2.** Same rule as in the M-Star and Palabos
skills: a simulation with an unconfirmed shear-rate range, fluid
model, or geometry is a wasted run. If the user has not named a
number, ask — do not invent one and bury it in a dictionary.
Defaults in the examples are labelled `default:` and must be
confirmed.

**Running is free here** (no license seat), but it is still not
free: a 3D run at fine resolution costs real CPU time. Default to
a cheap first run (coarse mesh, one shear rate) and only then sweep.

## 1. Discuss — what to elicit

Same checklist as the M-Star skill, plus OpenFOAM-specific items:

### Geometry
- Inner (rotating) radius `R_i`, outer (fixed) radius `R_o`,
  immersed length `L`. Metres.
- **First version is a wedge sector, not a full annulus.**
  OpenFOAM is 3D finite-volume, so a Couette cell is modelled as a
  thin wedge (4°, axis along X, 1 mm axial slice, 1 cell axial)
  with `wedge` patches on the two sector faces and `empty` patches
  on the two axial faces. The wedge boundary condition makes the
  solution axisymmetric: no Taylor vortices, no end effects — the
  ideal infinite-length Couette cell, exactly what the analytic
  torque assumes. Say which you are running. A full 3D annulus is
  the follow-up: it adds end effects and, above the critical Taylor
  number Ta_c ≈ 41.3, Taylor vortices that raise the torque above
  the analytic laminar value and break the validation gate. For
  this case (η = 1 Pa·s, ρ = 1000 kg/m³) Re ≤ 1.8 and Ta ≤ 0.9
  across the whole sweep, so a full annulus would stay laminar —
  but the wedge is still the cheaper, cleaner validation.

### Fluid — pick one rheology, with numbers
OpenFOAM **has** a rheology dropdown, in
`constant/transportProperties`: `transportModel Newtonian;` is the
validation case, and `HerschelBulkley`, `BirdCarreau`, `Casson`,
`powerLaw`, `CrossPowerLaw` are built-in `generalisedNewtonian`
models. Herschel–Bulkley and Bird–Carreau are the documented
follow-up, **not** the validation case. Two traps:
- The viscosity in `transportProperties` is the **kinematic**
  viscosity `nu` = η/ρ (m²/s), not the dynamic viscosity η.
  For η = 1.0 Pa·s and ρ = 1000 kg/m³, `nu = 1e-03` — not
  1e-06 (the value for water, η = 1e-3 Pa·s). An early draft of
  this repo used 1e-06 and the torque came out exactly 1000×
  too small while the velocity profile looked right — the
  Newtonian Couette profile is viscosity-independent, so the
  profile does not catch this mistake. The torque does.
- The non-Newtonian coefficients are kinematic too
  (`nu0` = η0/ρ, `k` = K/ρ); the yield stress `tau0` is in Pa.
  Verify against the model source before trusting a
  non-Newtonian run. If the user names a real material, do not
  invent its parameters: ask for a measured flow curve, a
  rheofit fit, or a literature value, or start Newtonian.

### Operating conditions — the sweep
- Shear-rate range and spacing, e.g. 0.1 → 100 s⁻¹, log-spaced.
- Mesh resolution: cells across the gap (default 40, i.e.
  dx = 0.125 mm). More cells = more accurate wall shear, much
  more cost.
- Run length: `simpleFoam` runs in iterations, not seconds.
  `endTime 3000` with `residualControl` 1e-8 — the solver stops
  early when converged (γ̇ = 10 converges in ~2050 iterations,
  ~2 s). The steady window for averaging torque is the last 20%
  of the `moment.dat` samples.

### What is being measured
- Couette: torque on the rotating bob → shear stress, rotation
  rate → shear rate. The flow curve. Name the file it comes from
  (`postProcessing/forces/0/moment.dat`, written by the `forces`
  functionObject) before running.

## 2. Write case.yaml

One file per simulation, in `examples/<name>/case.yaml`. It is the
contract: the scripts read it, they do not re-derive numbers from
chat. Template: `examples/couette/case.yaml`. Show it to the user
and get a yes before building.

## 3. Mesh — the step M-Star hides

OpenFOAM needs a mesh, built here with `blockMesh` from
`system/blockMeshDict`. The Couette mesh is a single hex block:

```
axis = X (cylinder axis), radial = Y, wedge opens in the Y-Z plane
wedge angle 4 deg total (OpenFOAM requires < 5 deg), half-angle 2 deg
axial extent x = 0..0.001 m, ONE cell (no axial variation)
radial: 40 cells across the 5 mm gap, simpleGrading (1 1 1)
patches: innerWall, outerWall, back/front (type wedge),
         left/right (type empty)
```

Check it with `checkMesh` before solving: it must report
`Mesh OK.`, wedge angle 2° per side, non-orthogonality 0. The
`empty` + `wedge` combination in one mesh is accepted by v2412
(verified here); if a future version rejects it, switch the
axial faces to `symmetry`.

Torque scaling: the sector is a 4° slice of a 1 mm slice of the
60 mm cylinder, so

```
T_full = M_x(sector) * (360/4) * (0.060/0.001) = M_x * 5400
```

where `M_x` is the moment about the X axis from the `forces`
functionObject on `innerWall` (CofR at the origin, on the axis).
The sign is negative (fluid drag opposes the rotation); the
driving torque is the magnitude.

## 4. Build the case

OpenFOAM is a set of **applications**, not a library: you write
dictionary files and run them. The repo layout:

```bash
bash scripts/install-openfoam.sh   # official Debian repo, v2412
source /usr/lib/openfoam/openfoam2412/etc/bashrc
bash scripts/check-setup.sh        # simpleFoam, blockMesh, checkMesh, uv
./run-couette.sh                   # dry run: build mesh + checkMesh only
```

`couette_build.py` copies the template (`examples/couette/case/`)
to a run directory and substitutes `__OMEGA__` in `0/U` with the
angular velocity for the shear rate:

```
Omega = gamma * (Ro^2 - Ri^2) / (2 * Ro^2)
```

Boundary conditions (verified against the v2412 tutorials):
- `innerWall`: `rotatingWallVelocity`, `axis (1 0 0)`,
  `omega constant <Omega>` (rad/s), `origin (0 0 0)`.
  Pattern: the `climbingRod` tutorial's `rotatingWallVelocity`.
- `outerWall`: `noSlip`.
- `back`/`front`: `wedge`; `left`/`right`: `empty`.
- Pressure: `fixedFluxPressure` on both walls (all-wall case).
- `constant/transportProperties`: `transportModel Newtonian;`
  `nu 1e-03;` (see §1 — kinematic, not dynamic).
- `constant/turbulenceProperties`: `simulationType laminar;`.
  **v2412 reads `turbulenceProperties`;** newer versions renamed
  it `momentumTransport` — if your solver complains it cannot
  find the other name, rename the file and its internal `object`.
- `system/fvSolution`: `SIMPLE` with `pRefCell 0; pRefValue 0;`
  (required: every boundary is a wall, so pressure needs a
  reference cell — without it simpleFoam exits with
  "Unable to set reference cell for field p"), GAMG for p,
  smoothSolver for U, `residualControl` p/U 1e-8.
- `system/controlDict`: `simpleFoam`, `endTime 3000` iterations,
  `forces` functionObject (`patches (innerWall)`,
  `rho rhoInf; rhoInf 1000;`, `CofR (0 0 0)`,
  `writeInterval 5`). v2412 writes `force.dat` and `moment.dat`
  (separate files), not `forces.dat`.

**Status: the steady case has been run for real in this VM
(OpenFOAM v2412, 2026-11-17) and the Newtonian validation in §6
passes (0.03% analytic torque error at γ̇ = 10 — see
`examples/couette/RUN_REPORT.md`).** The transient
`pimpleFoam` variant (`case-transient/`, for the spin-up video)
also runs: 1000 steps in ~2 s, converging to the same torque.

Non-Newtonian: change `transportModel` in
`transportProperties` (Herschel–Bulkley first, Bird–Carreau
second). Keep the Newtonian path as the default and the
validation gate — never debug a non-Newtonian model on an
unvalidated geometry.

## 5. Run

```bash
./run-couette.sh --run           # one run per shear rate, in examples/couette/runs/
# or, per point:
python3 couette_build.py --gamma 10 --out runs/gamma_10
cd runs/gamma_10 && blockMesh && simpleFoam
```

Each run writes `torque.csv` (iteration, sector moment,
full-cylinder torque) and `run_info.json` (convergence flag,
iterations, wall time). If a run is slow, refine the mesh or the
run time first — do not silently change the geometry to make it
fast. A run that reaches `endTime` without the Uz residual
falling below 1e-7 is flagged `converged: false` — diagnose
before trusting its torque (mesh, BCs, relaxation).

## 6. Post-process — torque to flow curve (Couette)

Same conversion as the M-Star and Palabos skills:

```
shear rate at the inner wall:  gamma_i = 2*Omega*Ro^2 / (Ro^2 - Ri^2)
shear stress at the inner wall: tau_i  = T / (2*pi*Ri^2*L)
apparent viscosity:             eta_app = tau_i / gamma_i
```

Average torque over the steady window named in `case.yaml`
(last 20% of samples), report its standard deviation as the
steadiness check.

**Validation gate (mandatory for the first run of a new geometry).**
Run a Newtonian fluid of known eta first and compare with the
analytic Couette torque:

```
T_analytic = 4*pi*L*eta*Omega*Ri^2*Ro^2 / (Ro^2 - Ri^2)
```

If the simulated torque differs by more than ~10%, do **not**
proceed to a non-Newtonian flow curve. Stop and diagnose: mesh
resolution across the gap, `nu` (kinematic vs dynamic — see §1),
run time / convergence, rotating-wall boundary, torque scaling.
Record the validation number in the report. `couette_post.py`
enforces this gate and exits non-zero on failure.

Then each sweep point gives one (gamma_i, tau_i) point. Plot tau vs
gamma (log-log) and eta_app vs gamma, write `flow_curve.csv`, and —
if the user wants parameters — fit the curve with rheofit
(Herschel–Bulkley, Carreau, …) in a separate step.

## 7. Report

Deliver, per run: `case.yaml` (as run), `flow_curve.csv`,
`flow_curve.png`, and a short note stating the geometry (wedge
sector, angle, cells across the gap), fluid, sweep, validation
result, steady-state criterion, and anything unverified. If a run
failed, report the solver log tail — do not silently drop the
point from the curve.

## Starting a session with GitHub Copilot CLI

Same setup as `mstar-skill` and `palabos-skill`: Copilot CLI
discovers project skills in `.github/skills/`, and this skill is
mirrored there. From the repo root:

```bash
git clone https://github.com/marcocaggioni/openfoam-skill.git
cd openfoam-skill
bash scripts/install-openfoam.sh
bash scripts/check-setup.sh
copilot
```

Then `/skills list` (you should see `openfoam-simulation`), and:

```
/openfoam-simulation run the Couette example in examples/couette/case.yaml
```

This skill deliberately has **no `allowed-tools` frontmatter**:
Copilot must ask before running shell commands, and in particular
before a long solver run. If the skill was added during a session,
run `/skills reload` first.

## What this skill does NOT do

- It does not install OpenFOAM for you beyond the scripted
  `apt` route in `scripts/install-openfoam.sh`: you need a
  Debian/Ubuntu machine and sudo.
- It does not claim a case is verified until it runs against an
  installed OpenFOAM and the Newtonian validation passes.
- It does not replace M-Star for tanks, impellers, multiphase, or
  particle-laden flows — those are out of scope for v0.1. This
  repo is the Couette flow curve, done openly, as the first proof
  that the open finite-volume route works.

## Files in this repo

- `skills/openfoam-simulation/SKILL.md` — this file. Mirrored
  byte-for-byte at `.github/skills/openfoam-simulation/SKILL.md`
  (the copy GitHub Copilot CLI discovers). **Keep the two copies
  in sync** — edit both in the same commit.
- `docs/openfoam-guide.md` — install, mesh, BCs, non-Newtonian
  notes, limits.
- `examples/couette/` — the worked Couette example: `case.yaml`,
  `case/` (steady simpleFoam template), `case-transient/`
  (pimpleFoam spin-up template), `couette_build.py`,
  `couette_sweep.py`, `couette_post.py`, `make_video.py`,
  `README.md`.
- OpenFOAM itself: https://www.openfoam.com (GPL)
