#!/usr/bin/env bash
# Build the custom threeComponent viscosity model as a user library
# (libthreeComponent.so) with wmake libso. The .so lands in
# $FOAM_USER_LIBBIN, which simpleFoam searches when the case's
# controlDict lists libs ("libthreeComponent.so").
# Requires OpenFOAM v2412: source /usr/lib/openfoam/openfoam2412/etc/bashrc
# (or run bash scripts/check-setup.sh first).
set -e
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2412/etc/bashrc 2>/dev/null || true
wmake libso .
ls -l "$FOAM_USER_LIBBIN/libthreeComponent.so"
