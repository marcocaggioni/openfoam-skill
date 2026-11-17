#!/usr/bin/env bash
# Couette example — dry-run by default (build mesh + checkMesh only).
#   ./run-couette.sh            dry run
#   ./run-couette.sh --run      run the sweep (needs OpenFOAM installed)
#   ./run-couette.sh --post     post-process runs/ into flow_curve.csv/png
#   ./run-couette.sh --video    render videos from runs/ (needs the sweep)
set -e
cd "$(dirname "$0")/examples/couette"
if command -v uv >/dev/null 2>&1; then PY="uv run python"; else PY="python3"; fi
if [ "$1" = "--post" ] 2>/dev/null; then $PY couette_post.py; exit 0; fi
if [ "$1" = "--video" ] 2>/dev/null; then $PY make_video.py; exit 0; fi
if [ "$1" = "--run" ] 2>/dev/null; then $PY couette_sweep.py --run; $PY couette_post.py; exit 0; fi
# dry run: build the gamma=10 case, mesh it, check it — no solver run
$PY couette_build.py --gamma 10 --out /tmp/openfoam-couette-dryrun
FOAM_BASHRC=""
for root in /usr/lib/openfoam/openfoam2412 /opt/openfoam2412 /usr/lib/openfoam/openfoam2606; do
  if [ -f "$root/etc/bashrc" ]; then FOAM_BASHRC="$root/etc/bashrc"; break; fi
done
if [ -z "$FOAM_BASHRC" ]; then
  echo "OpenFOAM not found — run bash scripts/install-openfoam.sh first."
  echo "Dry run stopped after building the case directory."
  exit 1
fi
# shellcheck disable=SC1090
# (|| true: the OpenFOAM setup script prints a harmless
# pop_var_context warning and returns non-zero when sourced in a
# non-interactive shell — must not trip `set -e`.)
source "$FOAM_BASHRC" || true
cd /tmp/openfoam-couette-dryrun && blockMesh && checkMesh
echo "Dry run only. Mesh OK. Pass --run to execute the solver sweep."
