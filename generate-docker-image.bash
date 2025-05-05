#!/usr/bin/env bash
set -euo pipefail

# Optional override: pass ARCH=arm64 or amd64
ARCH=${ARCH:-$(uname -m)}
case "$ARCH" in
  aarch64|arm64)   ARCH_TAG=arm64   ;;
  x86_64|amd64)    ARCH_TAG=amd64  ;;
  *) echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

# Build Debian‐arm64 image
if [[ "$ARCH_TAG" == "arm64" ]]; then
  echo "Building Debian-arm64 (eCAL from source)..."
  docker build \
    --pull \
    --platform linux/arm64 \
    -f Dockerfile.debian_arm64 \
    -t bench-debian-arm64 .

else
  echo "Building Ubuntu-x86_64 (eCAL from PPA)..."
  docker build \
    --pull \
    --platform linux/amd64 \
    -f Dockerfile.ubuntu_x86_64 \
    -t bench-ubuntu-x86_64 .
fi

echo "Done." 
