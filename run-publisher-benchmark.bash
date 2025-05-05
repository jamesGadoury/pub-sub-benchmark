#!/bin/bash

# NOTE: This script uses multiples of KiB (kibibytes), MiB (mebibytes), and GiB (gibibytes) to benchmark
#       KiB = 1024 bytes
#       MiB = (1024)^2 bytes = 1048576 bytes
#       GiB = (1024)^3 bytes = 1073741824 bytes

# NOTE: This allows a user to specify a different python interpreter path to run
# Use value of first positional argument if it is set and non-empty, otherwise use python3
PYTHON_INTERPRETER="${1:-python3}"

echo "Important: Ensure you start this script before run-subscriber-benchmark.bash"

echo "Note that the first message in each run is ignored in saved reports due to nontrivial processing overhead that affects first message"

echo "------------------------------------------------------------------------------------------------------------------------------"
echo "Running LCM publishing benchmark"

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 1KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes 1024 --transmission-rate 1000

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 2KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(2 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 4KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(4 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 8KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(8 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 16KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(16 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 32KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(32 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 64KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(64 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using lcm to publish 6 messages at target transmission rate of 1kHz with data blobs of size 128KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware lcm --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(128 * 1024)") --transmission-rate 1000

echo "------------------------------------------------------------------------------------------------------------------------------"
echo "Running eCAL publishing benchmark"

${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes 1024 --transmission-rate 1000

echo "Running benchmark publisher using ecal to publish 6 messages at target transmission rate of 1kHz with data blobs of size 2KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(2 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using ecal to publish 6 messages at target transmission rate of 1kHz with data blobs of size 4KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(4 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using ecal to publish 6 messages at target transmission rate of 1kHz with data blobs of size 8KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(8 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using ecal to publish 6 messages at target transmission rate of 1kHz with data blobs of size 16KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(16 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using ecal to publish 6 messages at target transmission rate of 1kHz with data blobs of size 32KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(32 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using ecal to publish 6 messages at target transmission rate of 1kHz with data blobs of size 64KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(64 * 1024)") --transmission-rate 1000

echo "Running benchmark publisher using ecal to publish 6 messages at target transmission rate of 1kHz with data blobs of size 128KiB"
${PYTHON_INTERPRETER} benchmark_publisher.py --middleware ecal --num-msgs 6 --num-bytes $(${PYTHON_INTERPRETER} -c "print(128 * 1024)") --transmission-rate 1000



