#!/usr/bin/env bash

# Usage: ./run-benchmarks.sh [python_interpreter] [num_msgs] [transmission_rate]
#   python_interpreter: which python to use (default: python3)
#   num_msgs: how many messages to send in each run (default: 6)
#   transmission_rate: target rate in Hz (default: 1000)

PYTHON_INTERPRETER="${1:-python3}"
NUM_MSGS="${2:-6}"
TRANSMISSION_RATE="${3:-1000}"

echo "Important: Ensure you start this script before run-subscriber-benchmark.bash"
echo "First message in each run is ignored in saved reports due to setup overhead."
echo "Using interpreter: ${PYTHON_INTERPRETER}"
echo "Number of messages per run: ${NUM_MSGS}"
echo "Target transmission rate: ${TRANSMISSION_RATE} Hz"
echo "------------------------------------------------------------------------------------------------------------------------------"

echo "Running LCM publishing benchmark"
for SIZE_KIB in 1 2 4 8 16 32 64 128; do
  BYTES="$(${PYTHON_INTERPRETER} -c "print(${SIZE_KIB} * 1024)")"
  echo " • ${SIZE_KIB} KiB payload → ${NUM_MSGS} msgs @ ${TRANSMISSION_RATE} Hz"
  ${PYTHON_INTERPRETER} benchmark_publisher.py \
    --middleware lcm \
    --num-msgs "${NUM_MSGS}" \
    --num-bytes "${BYTES}" \
    --transmission-rate "${TRANSMISSION_RATE}"
done

echo "------------------------------------------------------------------------------------------------------------------------------"
echo "Running eCAL publishing benchmark"
for SIZE_KIB in 1 2 4 8 16 32 64 128; do
  BYTES="$(${PYTHON_INTERPRETER} -c "print(${SIZE_KIB} * 1024)")"
  echo " • ${SIZE_KIB} KiB payload → ${NUM_MSGS} msgs @ ${TRANSMISSION_RATE} Hz"
  ${PYTHON_INTERPRETER} benchmark_publisher.py \
    --middleware ecal \
    --num-msgs "${NUM_MSGS}" \
    --num-bytes "${BYTES}" \
    --transmission-rate "${TRANSMISSION_RATE}"
done
