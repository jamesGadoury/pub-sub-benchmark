#!/bin/bash

# NOTE: This script uses multiples of KiB (kibibytes), MiB (mebibytes), and GiB (gibibytes) to benchmark
#       KiB = 1024 bytes
#       MiB = (1024)^2 bytes = 1048576 bytes
#       GiB = (1024)^3 bytes = 1073741824 bytes

# NOTE: This allows a user to specify a different python interpreter path to run
# Use value of first positional argument if it is set and non-empty, otherwise use python3
PYTHON_INTERPRETER="${1:-python3}"
SLEEP_TIME=1s

echo "Important: Ensure you run run-publisher-benchmark.bash before starting this script"

echo "Note that the first message in each run is ignored in saved reports due to nontrivial processing overhead that affects first message"

echo "------------------------------------------------------------------------------------------------------------------------------"
echo "Running LCM subscription benchmark"

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using lcm to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware lcm --num-msgs 6
sleep ${SLEEP_TIME}

echo "------------------------------------------------------------------------------------------------------------------------------"
echo "Running eCAL subscription benchmark"

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}

echo "Running benchmark subscriber using ecal to subscribe to 6 messages"
${PYTHON_INTERPRETER} benchmark_subscriber.py --middleware ecal --num-msgs 6
sleep ${SLEEP_TIME}
