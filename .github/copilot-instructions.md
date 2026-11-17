# Copilot instructions — openfoam-skill

This repo teaches an agent to run open-source OpenFOAM finite-volume
simulations from an English discussion. The skill is
`skills/openfoam-simulation/SKILL.md`, mirrored at
`.github/skills/openfoam-simulation/SKILL.md`.

Rules for every simulation in this repo:

1. Discuss in English first, then write `case.yaml`, show it, and
   get a yes before building. Never invent a number.
2. The Couette mesh is a 4° wedge sector (axisymmetric), not a full
   annulus. Torque scale is 5400 (sector → full cylinder).
3. `nu` in transportProperties is KINEMATIC viscosity (eta/rho).
   For eta = 1 Pa·s, rho = 1000 kg/m³, nu = 1e-03 — not 1e-06.
4. Default to a dry run (build mesh + checkMesh only). Never run
   the solver without saying so first.
5. Validate a Newtonian case against the analytic Couette torque
   (within ~10%) before any non-Newtonian flow curve.
6. OpenFOAM has built-in rheology models (HerschelBulkley,
   BirdCarreau, Casson, powerLaw) in transportProperties — but the
   coefficients are kinematic too (nu0 = eta0/rho, k = K/rho).
7. v2412 reads `constant/turbulenceProperties`; newer versions
   renamed it `momentumTransport` — rename the file and its
   internal `object` if the solver asks for the other name.
