# OpenFOAM guide

Install, mesh, boundary conditions, solvers, and non-Newtonian
notes for the `openfoam-simulation` skill. Everything here was
checked against the installed OpenFOAM v2412 (Ubuntu 24.04,
2026-11-17) or against the v2412 tutorials shipped with it —
nothing is asserted from memory alone where a check was possible.

## Install

Official Debian/Ubuntu route (https://openfoam.org/download/):

```bash
bash scripts/install-openfoam.sh
source /usr/lib/openfoam/openfoam2412/etc/bashrc
```

What the script does: runs the official
`https://dl.openfoam.com/add-debian-repo.sh` (adds
`/etc/apt/sources.list.d/openfoam.list` and the GPG key), then
installs `openfoam2412` + `openfoam2412-tutorials`. Available
versions at install time went up to `openfoam2606`; v2412 was
chosen because it is a long-term release and its tutorials are
the ones this repo's dictionary patterns were copied from.

**Gotcha — keyring permissions.** The repo-setup script writes
`/etc/apt/trusted.gpg.d/openfoam.gpg` with mode 600, and apt then
ignores the key (`NO_PUBKEY 3386DD74948D208F`). The install script
fixes it with `chmod 644`. The key fingerprint is
`DC93C096174122E256DA24063386DD74948D208F`.

After sourcing the bashrc, `simpleFoam`, `pimpleFoam`,
`blockMesh`, `checkMesh` are on PATH. `foamInfo` is NOT in the
runtime package.

## Version note: turbulenceProperties vs momentumTransport

In v2412 the laminar/turbulence switch lives in
`constant/turbulenceProperties` (`simulationType laminar;`).
OpenFOAM has since renamed this file to `momentumTransport`
(the rename is in the v2506+ line). If your solver exits with
"cannot find file .../momentumTransport" (or the reverse),
rename the file **and** its internal `object` name to the one
your version expects — the content is unchanged.

## The Couette mesh (wedge sector)

OpenFOAM is 3D finite-volume, so a Couette cell is a thin wedge:

- Cylinder axis = X (the `movingCone` tutorial convention),
  radial = Y, wedge opens in the Y–Z plane.
- Total wedge angle 4° (half-angle 2°); OpenFOAM requires the
  wedge angle < 5°.
- Axial extent x = 0..0.001 m, ONE cell — no axial variation,
  so Taylor vortices cannot form and there are no end effects.
- Radial: 40 cells across the 5 mm gap (`simpleGrading (1 1 1)`).
- One hex block, `mergeType points;`, no arc edges needed.
- Patches: `innerWall`, `outerWall` (the two cylindrical faces),
  `back`/`front` (`type wedge`), `left`/`right` (`type empty`).

Why not a planar 2D slice? A slice with the azimuthal direction
thin would give a linear plane-Couette profile (shear 4Ω) instead
of the true cylindrical profile (γ̇_i = 5.56Ω at the inner wall)
— about 28% low torque, failing the validation gate. Why not a
full 3D annulus? Above the critical Taylor number Ta_c ≈ 41.3 the
flow develops Taylor vortices and the torque exceeds the analytic
laminar value. The wedge sector models the ideal infinite-length
Couette cell exactly. (For this case, with the correct viscosity,
Re ≤ 1.8 and Ta ≤ 0.9 across the sweep, so even a full annulus
would stay laminar — but the wedge is cheaper and cleaner.)

Torque scaling: the sector is a 4° slice of a 1 mm slice of the
60 mm cylinder, so `T_full = M_x × (360/4) × (0.060/0.001)
= M_x × 5400`, where `M_x` is the moment about the X axis from
the `forces` functionObject on `innerWall`.

`checkMesh` must report `Mesh OK.`, wedge angle 2° per side,
non-orthogonality 0, max aspect ratio ~8. The `empty` + `wedge`
combination in one mesh is accepted by v2412 (verified here); if
a future version rejects it, switch the axial faces to
`symmetry`.

## Boundary conditions

Verified against the v2412 tutorials (`climbingRod` for the
rotating wall, `movingCone` for the wedge, `pipeCyclic` for the
solver dictionaries):

- `innerWall`: `type rotatingWallVelocity; axis (1 0 0);
  origin (0 0 0); omega constant <Omega>;` — Omega in **rad/s**
  (the climbingRod tutorial writes omega as
  `${{ 2.1 * (2*pi()) }}` with the comment "rev/s -> rads/s").
- `outerWall`: `type noSlip;`.
- `back`/`front`: `type wedge;` in both the mesh and the field
  files. `left`/`right`: `type empty;`.
- Pressure: `fixedFluxPressure` on both walls.
- `#includeEtc "caseDicts/setConstraintTypes"` in `0/U` so the
  wedge/empty constraint types are set consistently.

All-wall case: pressure needs a reference cell, or simpleFoam
exits with "Unable to set reference cell for field p". Set
`pRefCell 0; pRefValue 0;` in the `SIMPLE` (or `PIMPLE`) subdict
of `system/fvSolution`.

## Solvers

- Steady: `simpleFoam`, `endTime 3000` iterations,
  `residualControl` p/U 1e-8. The solver stops early when
  converged (γ̇ = 10: ~2050 iterations, ~2 s). Early iterations
  overshoot the torque (γ̇ = 10 reads ~23% high at iteration 250),
  so average only the last 20% of the `moment.dat` samples.
  `consistent yes;` in SIMPLE was tried and did not accelerate
  this case.
- Transient: `pimpleFoam`, `endTime 1.0 s`, `deltaT 0.001 s`
  (Co_max ~0.03 at γ̇ = 10), `nOuterCorrectors 1`,
  `nCorrectors 2`, no relaxation. PIMPLE requires `pFinal` and
  `(U)Final` solver entries (the "Final" variants used on the
  last outer corrector). 1000 steps in ~2 s; converges to the
  same torque as the steady run. Viscous diffusion time across
  the gap is gap²/ν = 0.025 s, so 1 s is ~40 diffusion times.
- `forces` functionObject: `type forces; libs (forces);
  patches (innerWall); rho rhoInf; rhoInf 1000; CofR (0 0 0);`
  with `writeInterval 5`. **v2412 writes `force.dat` and
  `moment.dat` (separate files), not `forces.dat`.** The moment
  columns are `total_x total_y total_z pressure_x ... viscous_x
  ...`; the X component is the torque about the axis. The sign is
  negative (fluid drag opposes the rotation); the driving torque
  is the magnitude.

## Viscosity: the kinematic trap

`transportProperties` takes the **kinematic** viscosity
`nu` = η/ρ, in m²/s. For η = 1.0 Pa·s, ρ = 1000 kg/m³:
`nu = 1e-03`. The value 1e-06 is water (η = 1e-3 Pa·s).

An early draft of this repo used 1e-06 (copied from the
`pipeCyclic` tutorial, which is water) and the torque came out
exactly 1000× too small — while the velocity profile matched
the analytic Couette profile to 0.5%. The Newtonian Couette
profile is viscosity-independent, so the profile cannot catch
this mistake; only the torque can. If your torque is off by a
round factor, check `nu` first.

## Non-Newtonian models (follow-up, not validation)

OpenFOAM's `generalisedNewtonian` models live in
`transportProperties`; the patterns below come from the
`nonNewtonianIcoFoam/offsetCylinder` tutorial (CrossPowerLaw)
and the v2412 model list. **None of these has been run yet —
verify against the model source before trusting a run.**

```cpp
// Herschel-Bulkley (yield stress + power law)
transportModel  HerschelBulkley;
HerschelBulkleyCoeffs
{
    nu0     0.04;   // kinematic zero-shear viscosity (eta0/rho)
    tau0    5;      // yield stress, Pa
    k       0.002;  // kinematic consistency (K/rho)
    n       0.5;
}

// Bird-Carreau
transportModel  BirdCarreau;
BirdCarreauCoeffs
{
    nu0     0.04;   // kinematic zero-shear viscosity
    nuInf   0.001;  // kinematic infinite-shear viscosity
    k       1.0;    // time constant, s
    n       0.5;
}
```

The coefficients are kinematic (`nu0` = η0/ρ, `k` = K/ρ);
`tau0` is in Pa. The example numbers above correspond to
η0 = 40 Pa·s, K = 2 Pa·s^0.5, τ_y = 5 Pa at ρ = 1000 kg/m³ —
recompute them for the actual material; do not copy them blind.
For a real material, get the parameters from a measured flow
curve or a rheofit fit, never from this file.

## Limits

- Wedge sector only in v0.1: no end effects, no Taylor vortices,
  no 3D. A full annulus is the follow-up.
- The `forces` torque is the primary measurement. A
  profile-derived torque (near-wall velocity gradient) was not
  implemented; on 40 cells the wall gradient is first-order and
  would read a few percent high.
- `simpleFoam` convergence is slow in iteration count for this
  case (~2000 iterations for 40 cells) because the pressure–
  velocity coupling has to establish the radial pressure
  gradient (dp/dr = ρ·u_θ²/r). It is still ~2 s per point.
- OpenFOAM's `rotatingWallVelocity` takes Omega in rad/s. The
  M-Star and Palabos scripts carry an explicit "RPM vs rad/s"
  warning for the same reason — a 2π error is the classic
  failure here.
