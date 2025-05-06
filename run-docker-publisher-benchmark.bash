#!/usr/bin/env bash
set -euo pipefail

# Optional override: pass ARCH=arm64 or amd64
ARCH=${ARCH:-$(uname -m)}
case "$ARCH" in
  aarch64|arm64)   ARCH_TAG=arm64   ;;
  x86_64|amd64)    ARCH_TAG=amd64  ;;
  *) echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

if [[ "$ARCH_TAG" == "arm64" ]]; then
    docker run --rm -it --privileged --network=host --ipc=host \
    -e LCM_DEFAULT_URL=udpm://239.255.76.67:7667?ttl=1 \
    -v /tmp/publisher-benchmark-results/:/tmp/publisher-benchmark-results/ \
    bench-debian-arm64 \
    bash -lc "cd /workspace && ./run-publisher-benchmark.bash"
else
    docker run --rm -it --privileged --network=host --ipc=host \
    -e LCM_DEFAULT_URL=udpm://239.255.76.67:7667?ttl=1 \
    -v /tmp/publisher-benchmark-results/:/tmp/publisher-benchmark-results/ \
    bench-ubuntu-x86_64 \
    bash -lc "cd /workspace && ./run-publisher-benchmark.bash"
fi

echo "Done." 
