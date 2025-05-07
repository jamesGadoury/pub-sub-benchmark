#!/usr/bin/env bash

# Usage: ./run-subscriber-benchmark.sh [python_interpreter] [num_msgs]
#   results_dir: output dir to save results (default: /tmp/subscriber-benchmark-results/)
#   python_interpreter: which python to use (default: python3)
#   sleep_time: how long to sleep after each subscriber process finishes (default: 2s)

RESULTS_DIR="${1:-/tmp/subscriber-benchmark-results/}"
PYTHON_INTERPRETER="${2:-python3}"
SLEEP_TIME="${3:-2s}"

echo "Important: Make sure you run run-publisher-benchmark.bash first."
echo "First message in each run is ignored in saved reports due to setup overhead."
echo "Using results dir: ${RESULTS_DIR}"
echo "Interpreter: ${PYTHON_INTERPRETER}"
echo "Sleep time: ${SLEEP_TIME}"
echo

for MIDDLEWARE in lcm ecal; do
  echo "------------------------------------------------------------------------------------------------------------------------------"
  echo "Running ${MIDDLEWARE^^} subscription benchmark"
  for i in {1..8}; do
    echo " • [${i}/8] subscribe to ${NUM_MSGS} messages via ${MIDDLEWARE}"
    "${PYTHON_INTERPRETER}" benchmark_subscriber.py \
      --middleware "${MIDDLEWARE}" \
      --results-dir "${RESULTS_DIR}" \
      --ecal-ini-file ./ecal.ini
    sleep "${SLEEP_TIME}"
  done
  echo
done
