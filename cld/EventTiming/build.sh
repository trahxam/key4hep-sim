#!/bin/bash
# Build the EventTiming Gaudi plugin.
# Source key4hep first:  source /cvmfs/sw.hsf.org/key4hep/setup.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"

mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"
cmake "${SCRIPT_DIR}"
make -j"$(nproc)"

echo ""
echo "Build successful.  Before running k4run, set:"
echo "  export LD_LIBRARY_PATH=${BUILD_DIR}:\$LD_LIBRARY_PATH"
