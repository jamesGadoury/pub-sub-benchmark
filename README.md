# General Pub-Sub Benchmark Docker Containers

This repository provides two Docker images for running your LCM and eCAL Python-based benchmarking scripts:

1. **debian-arm64**

   * Base: Debian (arm64)
   * Builds eCAL from source
   * Python + LCM installed via pip

2. **ubuntu-x86\_64**

   * Base: Ubuntu (x86\_64)
   * Installs eCAL from PPA
   * Python + LCM installed via pip

Each image bundles your benchmarking scripts and allows you to run:

* `run-publisher-benchmark.bash`
* `run-subscriber-benchmark.bash`

## Prerequisites

* Docker (>= 20.10)
* Git (to clone this repo)

## Build Images

Make the generator script executable and run it from the project root:

```bash
chmod +x generate-docker-image.bash
./generate-docker-image.bash
```

This will detect your host architecture and build both images:

* `bench-debian-arm64`
* `bench-ubuntu-x86_64`

You can also force a specific architecture:

```bash
ARCH=arm64 ./generate-docker-image.bash   # only build Debian-arm64
ARCH=amd64 ./generate-docker-image.bash   # only build Ubuntu-x86_64
```

## Running the Benchmarks

Mount your workspace into the container and execute the scripts:

### Publisher

```bash
docker run --rm -it --network=host \
  -v "$(pwd)":/workspace \
  bench-ubuntu-x86_64 \
  bash -lc "cd /workspace && ./run-publisher-benchmark.bash"
```

*In a separate terminal, start the subscriber:*

### Subscriber

```bash
docker run --rm -it --network=host \
  -v "$(pwd)":/workspace \
  bench-ubuntu-x86_64 \
  bash -lc "cd /workspace && ./run-subscriber-benchmark.bash"
```

Replace `bench-debian-arm64` with `bench-ubuntu-x86_64` if desired.

Both scripts will write their YAML reports into the `results/` directory on your host.

## File Overview

* `Dockerfile.debian_arm64`            – builds eCAL from source on Debian/arm64
* `Dockerfile.ubuntu_x86_64`           – installs eCAL from PPA on Ubuntu/amd64
* `generate-docker-image.bash`         – builds images based on host arch
* `run-publisher-benchmark.bash`       – executes publisher script across message sizes
* `run-subscriber-benchmark.bash`      – executes subscriber script
* `benchmark_publisher.py`             – Python publisher benchmark
* `benchmark_subscriber.py`            – Python subscriber benchmark
* `benchmark.py`                       – common utilities (serialization, stats)
* `bench_pb2.py`                       – Protobuf definitions
* `lcmtypes/bench_t.lcm`               – LCM type definitions

## Notes

* The first message in each run is ignored in saved reports to avoid skew from startup overhead.
* Scripts use KiB (1024 bytes) units for message sizes.
* Ensure clocks are synchronized (NTP/PTP) if comparing one-way latencies across machines.
