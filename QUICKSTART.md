# Quickstart — openfoam-skill

```bash
git clone https://github.com/marcocaggioni/openfoam-skill.git
cd openfoam-skill
uv sync            # Python side: numpy, matplotlib, pyyaml (see note below)
bash scripts/install-openfoam.sh   # OpenFOAM v2412 via the official Debian repo
bash scripts/check-setup.sh
```

OpenFOAM itself is C++, not Python — there is no PyPI package for
it, so `uv sync` cannot install it. The install script adds the
official OpenFOAM Debian repository and installs `openfoam2412`
(and the tutorials). It needs sudo and a Debian/Ubuntu machine.

Then build the Couette mesh and run it:

```bash
./run-couette.sh            # dry run: build mesh + checkMesh only
./run-couette.sh --run      # run the sweep, then post-process
```

Then start Copilot CLI in the repo root and invoke the skill:

```bash
copilot
```

```
/openfoam-simulation run the Couette example in examples/couette/case.yaml
```

Or in one go:

```bash
copilot -i "Use the /openfoam-simulation skill to run the Couette example in examples/couette/case.yaml"
```

Copilot must be started from the repo root for skill discovery.
If the skill was added during a session, run `/skills reload` first.
The skill has no `allowed-tools` frontmatter on purpose — Copilot
must ask before running shell commands or a solver run.
