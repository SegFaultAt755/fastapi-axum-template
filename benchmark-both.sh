#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
RESULTS_ROOT="${RESULTS_ROOT:-benchmark/results}"

BASE_URL=http://127.0.0.1:8000 RESULTS_DIR="$RESULTS_ROOT/fastapi" \
    "$SCRIPT_DIR/benchmark.sh"
BASE_URL=http://127.0.0.1:8001 RESULTS_DIR="$RESULTS_ROOT/axum" \
    "$SCRIPT_DIR/benchmark.sh"
