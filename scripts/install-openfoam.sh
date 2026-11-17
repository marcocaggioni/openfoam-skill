#!/usr/bin/env bash
# Install OpenFOAM v2412 on Debian/Ubuntu via the official repository.
# Route: https://openfoam.org/download/ (Debian/Ubuntu packages).
# Needs sudo. Tested on Ubuntu 24.04, 2026-11-17.
#
# Gotcha found on the way: the repo-setup script writes the GPG key
# to /etc/apt/trusted.gpg.d/openfoam.gpg with mode 600, and apt
# then ignores it (NO_PUBKEY 3386DD74948D208F). The chmod 644 below
# fixes that. If apt still complains about the key, check the
# fingerprint: DC93C096174122E256DA24063386DD74948D208F.
set -e
echo "==> Adding the OpenFOAM Debian repository (official script)..."
curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
echo "==> Fixing keyring permissions (apt ignores mode-600 keys)..."
sudo chmod 644 /etc/apt/trusted.gpg.d/openfoam.gpg
echo "==> Installing openfoam2412 + tutorials..."
sudo apt-get update
sudo apt-get install -y openfoam2412 openfoam2412-tutorials
echo "==> Verifying..."
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2412/etc/bashrc
simpleFoam -help | head -2
blockMesh -help | head -2
echo "OpenFOAM v2412 installed. Source it with:"
echo "  source /usr/lib/openfoam/openfoam2412/etc/bashrc"
