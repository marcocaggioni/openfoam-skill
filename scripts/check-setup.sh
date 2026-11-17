#!/usr/bin/env bash
# Check the machine is ready to run the OpenFOAM Couette example.
# Exits 0 when ready, 1 otherwise. No GPU, no license needed to pass
# the Copilot/skill parts — only the solver parts fail.
set -u
fail=0
say() { printf '%-28s %s\n' "$1" "$2"; }

check() {  # name, command...
  local name="$1"; shift
  if command -v "$1" >/dev/null 2>&1; then say "$name" "OK ($1)";
  elif [ -x "$HOME/.local/bin/$1" ]; then say "$name" "OK (~/.local/bin/$1)";
  else say "$name" "MISS"; fail=1; fi
}

check "copilot CLI" copilot
check "uv" uv
check "python3" python3
python3 -c "import yaml, matplotlib" 2>/dev/null && say "python yaml+matplotlib" "OK" || { say "python yaml+matplotlib" "MISS (uv sync)"; fail=1; }
check "ffmpeg" ffmpeg

# OpenFOAM: the binaries are only on PATH after sourcing the bashrc.
FOAM_BASHRC=""
for root in /usr/lib/openfoam/openfoam2412 /opt/openfoam2412 /usr/lib/openfoam/openfoam2606; do
  if [ -f "$root/etc/bashrc" ]; then FOAM_BASHRC="$root/etc/bashrc"; break; fi
done
if [ -n "$FOAM_BASHRC" ]; then
  say "OpenFOAM bashrc" "OK ($FOAM_BASHRC)"
  # shellcheck disable=SC1090
  source "$FOAM_BASHRC" >/dev/null 2>&1
  for bin in simpleFoam pimpleFoam blockMesh checkMesh; do
    if command -v "$bin" >/dev/null 2>&1; then say "  $bin" "OK"; else say "  $bin" "MISS"; fail=1; fi
  done
else
  say "OpenFOAM install" "MISS (bash scripts/install-openfoam.sh)"
  fail=1
fi

[ -f skills/openfoam-simulation/SKILL.md ] && say "skill (skills/)" "OK" || { say "skill (skills/)" "MISS"; fail=1; }
[ -f .github/skills/openfoam-simulation/SKILL.md ] && say "skill (.github/skills/)" "OK" || { say "skill (.github/skills/)" "MISS"; fail=1; }
[ -f examples/couette/case.yaml ] && say "Couette case.yaml" "OK" || { say "Couette case.yaml" "MISS"; fail=1; }

if [ "$fail" -eq 0 ]; then echo "READY"; else echo "NOT READY — fix the MISS lines above"; fi
exit "$fail"
