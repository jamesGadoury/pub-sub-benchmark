#!/usr/bin/env bash

# Usage: ./run-subscriber-benchmark.sh [python_interpreter] [num_msgs]
#   python_interpreter: which python to use (default: python3)
#   num_msgs: how many messages each subscriber run should consume (default: 6)

PYTHON_INTERPRETER="${1:-python3}"
NUM_MSGS="${2:-6}"
SLEEP_TIME="1s"

echo "Important: Make sure you run run-publisher-benchmark.bash first."
echo "First message in each run is ignored in saved reports due to setup overhead."
echo "Interpreter: ${PYTHON_INTERPRETER}"
echo "Messages per run: ${NUM_MSGS} (NOTE THAT THIS MUST BE THE SAME VALUE AS run-publisher-benchmark.bash)"
echo

for MIDDLEWARE in lcm ecal; do
  echo "------------------------------------------------------------------------------------------------------------------------------"
  echo "Running ${MIDDLEWARE^^} subscription benchmark"
  for i in {1..8}; do
    echo " • [${i}/8] subscribe to ${NUM_MSGS} messages via ${MIDDLEWARE}"
    "${PYTHON_INTERPRETER}" benchmark_subscriber.py \
      --middleware "${MIDDLEWARE}" \
      --num-msgs "${NUM_MSGS}" \
      --ecal-ini-file ./ecal.ini
    sleep "${SLEEP_TIME}"
  done
  echo
done
