# AGENTS.md — openfoam-skill

Open-source counterpart of the private `mstar-skill` repo and of
`palabos-skill`: same discussion → case → run → report workflow,
same Couette example, OpenFOAM finite-volume solver instead of
licensed M-Star or LBM Palabos. No license, no GUI.

- Skill: `skills/openfoam-simulation/SKILL.md`, mirrored byte-for-byte
  at `.github/skills/openfoam-simulation/SKILL.md` (the copy Copilot
  CLI discovers). Keep the two copies in sync; edit both per commit.
- No `allowed-tools` in the skill frontmatter, deliberately — Copilot
  must ask before shell/solver runs.
- `case.yaml` is the contract. Defaults are labelled; confirm before
  running. Never invent a number.
- The mesh is a 4° wedge sector (axisymmetric), NOT a full annulus.
  Torque scale is 5400 (sector → full cylinder). Never change the
  scale without re-deriving it from the wedge angle and axial slice.
- `nu` in transportProperties is KINEMATIC viscosity (eta/rho).
  An early draft used 1e-06 (water) for eta = 1 Pa·s and the torque
  came out 1000× small while the profile looked right — the profile
  does not catch this; the torque does.
- Validation gate: Newtonian torque vs analytic Couette torque within
  ~10% before any non-Newtonian curve. `couette_post.py` enforces it.
- v0.1 status: the steady case and the transient spin-up have both
  been run for real (OpenFOAM v2412, 2026-11-17); validation PASSES
  (0.03% at gamma = 10) — see `examples/couette/RUN_REPORT.md`.
- OpenFOAM itself is GPL; this repo's own code is MIT.
